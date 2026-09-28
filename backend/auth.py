"""One local admin account; opaque, revocable sessions in private storage."""
import getpass
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse

import anyio
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

ROOT = Path(os.getenv('QUARK_AUTH_DIR', Path(__file__).resolve().parent.parent / '.auth'))
HASHER = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=1)
SESSION_SECONDS, IDLE_SECONDS, PRE_SECONDS = 8 * 3600, 30 * 60, 600
TOKEN = re.compile(r'^[A-Za-z0-9_-]{43}$')
LOGIN_LIMITER = anyio.CapacityLimiter(2)
router = APIRouter(prefix='/api/auth')


@contextmanager
def database():
    db = sqlite3.connect(ROOT / 'auth.sqlite', timeout=10)
    db.row_factory = sqlite3.Row
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    for setting in ('PUBLIC_APP_ORIGIN', 'PUBLIC_API_ORIGIN'):
        public = os.getenv(setting, '').rstrip('/')
        try:
            parsed = urlparse(public)
            _ = parsed.port  # Validate malformed port strings too.
            invalid = public and (parsed.scheme != 'https' or not parsed.hostname or parsed.path or parsed.query or parsed.fragment or parsed.username)
        except ValueError:
            invalid = True
        if invalid:
            raise RuntimeError(f'{setting} debe ser un origen HTTPS, sin ruta ni credenciales.')
    ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    ROOT.chmod(0o700)
    with database() as db:
        db.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS admin(id INTEGER PRIMARY KEY CHECK(id=1), password_hash TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY, csrf TEXT NOT NULL, kind TEXT NOT NULL,
          created REAL NOT NULL, expires REAL NOT NULL, seen REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS attempts(bucket TEXT PRIMARY KEY, started REAL NOT NULL, count INTEGER NOT NULL);
        ''')
    (ROOT / 'auth.sqlite').chmod(0o600)


def configure_password(password):
    if not 12 <= len(password) <= 128:
        raise ValueError('Usá una contraseña de entre 12 y 128 caracteres.')
    encoded = HASHER.hash(password)
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('INSERT OR REPLACE INTO admin VALUES (1,?)', (encoded,))
        db.execute('DELETE FROM sessions')
        db.execute('DELETE FROM attempts')


def configured():
    with database() as db:
        return db.execute('SELECT 1 FROM admin WHERE id=1').fetchone() is not None


def cookie_name(kind='session'):
    return ('__Host-' if os.getenv('PUBLIC_APP_ORIGIN') else '') + 'quark-' + kind


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def find_session(token, kind='session', touch=True):
    if not token or not TOKEN.fullmatch(token):
        return None
    now = time.time()
    with database() as db:
        row = db.execute('SELECT * FROM sessions WHERE token_hash=? AND kind=?', (digest(token), kind)).fetchone()
        if not row or row['expires'] <= now or (kind == 'session' and row['seen'] + IDLE_SECONDS <= now):
            if row:
                db.execute('DELETE FROM sessions WHERE token_hash=?', (row['token_hash'],))
            return None
        if touch and kind == 'session':
            db.execute('UPDATE sessions SET seen=? WHERE token_hash=?', (now, row['token_hash']))
        return dict(row)


def issue(db, kind):
    now, token, csrf = time.time(), secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    db.execute('DELETE FROM sessions WHERE expires<=? OR (kind=? AND seen<=?)', (now, 'session', now-IDLE_SECONDS))
    limit = 32 if kind == 'session' else 256
    # Bound persistent storage under anonymous traffic; newest sessions remain usable.
    db.execute('DELETE FROM sessions WHERE token_hash IN (SELECT token_hash FROM sessions WHERE kind=? ORDER BY created DESC LIMIT -1 OFFSET ?)', (kind, limit-1))
    lifetime = SESSION_SECONDS if kind == 'session' else PRE_SECONDS
    db.execute('INSERT INTO sessions VALUES (?,?,?,?,?,?)', (digest(token), csrf, kind, now, now+lifetime, now))
    return token, csrf


def set_cookie(response, token, kind='session'):
    response.set_cookie(cookie_name(kind), token, max_age=SESSION_SECONDS if kind == 'session' else PRE_SECONDS,
                        secure=bool(os.getenv('PUBLIC_APP_ORIGIN')), httponly=True, samesite='strict', path='/')


def allowed_request(request):
    public = os.getenv('PUBLIC_APP_ORIGIN', '').rstrip('/')
    try:
        host = urlparse('//' + request.headers.get('host', '')).hostname
    except ValueError:
        return False
    hosts = {'localhost', '127.0.0.1', 'testserver', 'studio'}
    if public:
        hosts.add(urlparse(public).hostname)
    api_origin = os.getenv('PUBLIC_API_ORIGIN', '')
    if api_origin:
        hosts.add(urlparse(api_origin).hostname)
    if host not in hosts or request.headers.get('sec-fetch-site') == 'cross-site':
        return False
    origins = {public} if public else {f'http://{host}:{port}' for host in ('localhost','127.0.0.1') for port in (os.getenv('WEB_PORT','8010'),'3000')}
    origin = request.headers.get('origin')
    return origin is None or origin in origins


def csrf_valid(session, request):
    supplied = request.headers.get('x-quark-csrf','')
    return bool(session and TOKEN.fullmatch(supplied) and hmac.compare_digest(session['csrf'], supplied))


class AccessControl:
    """Protect every route and mounted file, without per-endpoint opt-in."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] not in ('http', 'websocket'):
            return await self.app(scope, receive, send)
        if scope['type'] == 'websocket':
            return await send({'type':'websocket.close', 'code':4401})  # No websocket endpoint is currently used.
        request = Request(scope, receive)
        path = scope['path']
        public = path in ('/api/health', '/api/auth/session', '/api/auth/login', '/webhooks/instagram')
        error = None
        if path != '/api/health' and not allowed_request(request):
            error = (403, 'Origen no permitido')
        elif not public:
            session = find_session(request.cookies.get(cookie_name()))
            if not session:
                error = (401, 'Iniciá sesión para continuar')
            elif request.method not in ('GET','HEAD','OPTIONS') and not csrf_valid(session, request):
                error = (403, 'La sesión cambió. Recargá la página e intentá de nuevo.')
            else:
                scope.setdefault('state', {})['auth_session'] = session
        async def secured_send(message):
            if message['type'] == 'http.response.start':
                headers = [(k,v) for k,v in message.get('headers',[]) if k.lower() not in (b'cache-control',b'x-frame-options',b'referrer-policy')]
                headers.extend([(b'cache-control', b'private, no-store'), (b'x-frame-options',b'DENY'),
                                (b'referrer-policy',b'no-referrer'), (b'x-content-type-options',b'nosniff')])
                message = {**message, 'headers':headers}
            await send(message)
        if error:
            return await JSONResponse({'detail':error[1]}, status_code=error[0])(scope, receive, secured_send)
        await self.app(scope, receive, secured_send)


@router.get('/session')
def session_status(request: Request):
    active = find_session(request.cookies.get(cookie_name()))
    if active:
        return {'authenticated':True, 'username':'admin', 'csrfToken':active['csrf'], 'expiresAt':active['expires']}
    if not configured():
        return {'authenticated':False, 'configured':False}
    pre = find_session(request.cookies.get(cookie_name('pre')), 'pre', touch=False)
    response = JSONResponse({'authenticated':False, 'configured':True, 'csrfToken':pre['csrf'] if pre else None})
    if not pre:
        with database() as db:
            token, csrf = issue(db, 'pre')
        response = JSONResponse({'authenticated':False, 'configured':True, 'csrfToken':csrf})
        set_cookie(response, token, 'pre')
    return response


def login_sync(request, username, password):
    now = time.time()
    peer = digest(request.client.host if request.client else 'unknown')
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('DELETE FROM attempts WHERE started<=?', (now-900,))
        for bucket, limit in [('account',40), ('peer:'+peer,10)]:
            row = db.execute('SELECT count FROM attempts WHERE bucket=?', (bucket,)).fetchone()
            if row and row['count'] >= limit:
                raise HTTPException(429, 'Demasiados intentos. Esperá 15 minutos antes de volver a probar.', headers={'Retry-After':'900'})
        # Bound unique peer buckets too. Forwarded IP headers are deliberately ignored.
        if db.execute('SELECT count(*) FROM attempts').fetchone()[0] >= 128:
            raise HTTPException(429, 'Demasiados intentos. Probá más tarde.', headers={'Retry-After':'900'})
        for bucket in ('account','peer:'+peer):
            db.execute('INSERT INTO attempts VALUES (?,?,1) ON CONFLICT(bucket) DO UPDATE SET count=count+1', (bucket,now))
        row = db.execute('SELECT password_hash FROM admin WHERE id=1').fetchone()
    if not row:
        raise HTTPException(503, 'El acceso todavía no está configurado.')
    try:
        valid = HASHER.verify(row['password_hash'], password)
    except VerificationError:
        valid = False
    if not valid or not hmac.compare_digest(username.encode(), b'admin'):
        raise HTTPException(401, 'Usuario o contraseña incorrectos')
    pre = find_session(request.cookies.get(cookie_name('pre')), 'pre', touch=False)
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        current = db.execute('SELECT password_hash FROM admin WHERE id=1').fetchone()
        # Check again after hashing: password changes and parallel logins revoke the pre-session.
        if not pre or current['password_hash'] != row['password_hash'] or not db.execute('DELETE FROM sessions WHERE token_hash=?', (pre['token_hash'],)).rowcount:
            raise HTTPException(401, 'Volvé a cargar el formulario de acceso.')
        old = request.cookies.get(cookie_name())
        if old and TOKEN.fullmatch(old):
            db.execute('DELETE FROM sessions WHERE token_hash=?', (digest(old),))
        token, csrf = issue(db, 'session')
    response = JSONResponse({'authenticated':True, 'username':'admin', 'csrfToken':csrf})
    set_cookie(response, token)
    response.delete_cookie(cookie_name('pre'), path='/', secure=bool(os.getenv('PUBLIC_APP_ORIGIN')), httponly=True, samesite='strict')
    return response


@router.post('/login')
async def login(request: Request):
    pre = find_session(request.cookies.get(cookie_name('pre')), 'pre', touch=False)
    if not csrf_valid(pre, request):
        raise HTTPException(403, 'Volvé a cargar el formulario de acceso.')
    if request.headers.get('content-type','').split(';')[0] != 'application/json':
        raise HTTPException(415, 'Formato de acceso inválido')
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > 4096:
            raise HTTPException(413, 'Datos de acceso demasiado largos')
    try:
        data = json.loads(raw)
        if not isinstance(data, dict) or set(data) != {'username','password'} or any(not isinstance(data[k],str) for k in data) or not 1 <= len(data['username']) <= 100 or not 1 <= len(data['password']) <= 128:
            raise ValueError()
    except (ValueError, TypeError, UnicodeError):
        raise HTTPException(400, 'Datos de acceso inválidos')
    return await anyio.to_thread.run_sync(login_sync, request, data['username'], data['password'], limiter=LOGIN_LIMITER)


@router.get('/check')
def check():
    return {'authenticated':True, 'username':'admin'}


@router.post('/logout')
def logout(request: Request):
    with database() as db:
        db.execute('DELETE FROM sessions WHERE token_hash=?', (request.state.auth_session['token_hash'],))
    response = JSONResponse({'authenticated':False})
    response.delete_cookie(cookie_name(), path='/', secure=bool(os.getenv('PUBLIC_APP_ORIGIN')), httponly=True, samesite='strict')
    return response


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Gestionar la única cuenta admin de QUARK.')
    parser.add_argument('action', choices=['configure','initialize','revoke'])
    args = parser.parse_args()
    init_db()
    if args.action == 'initialize':
        # CI receives the bootstrap password over stdin, never argv or .env.
        import sys
        password = sys.stdin.read()
        with database() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT 1 FROM admin WHERE id=1').fetchone():
                print('Cuenta admin existente conservada.')
            else:
                if not 12 <= len(password) <= 128:
                    raise SystemExit('La contraseña inicial requiere 12–128 caracteres.')
                db.execute('INSERT INTO admin VALUES (1,?)', (HASHER.hash(password),))
                print('Cuenta admin inicializada.')
    elif args.action == 'configure':
        password = getpass.getpass('Nueva contraseña de admin (12–128 caracteres): ')
        if password != getpass.getpass('Repetí la contraseña: '):
            raise SystemExit('Las contraseñas no coinciden.')
        configure_password(password)
        print('Cuenta admin configurada. Las sesiones anteriores fueron revocadas.')
    else:
        with database() as db:
            db.execute('DELETE FROM sessions')
        print('Todas las sesiones fueron revocadas.')


if __name__ == '__main__':
    main()
