import json
import time

import pytest
from fastapi.testclient import TestClient
from backend import auth, store
from backend.app import app

PASSWORD = 'An-isolated-test-password-2026!'


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, 'ROOT', tmp_path/'private-auth')
    auth.init_db()
    auth.configure_password(PASSWORD)
    with TestClient(app) as client:
        yield client


def sign_in(client, password=PASSWORD, username='admin'):
    nonce = client.get('/api/auth/session').json()['csrfToken']
    return client.post('/api/auth/login', json={'username':username,'password':password}, headers={'X-Quark-CSRF':nonce})


@pytest.mark.parametrize('path',['/api/projects','/api/settings','/api/costs','/api/deepseek/balance','/media/assets/missing.png','/media/exports/missing.mp4','/docs','/openapi.json'])
def test_every_private_route_is_closed_before_login(client, path):
    response = client.get(path)
    assert response.status_code == 401
    assert response.headers['cache-control'] == 'private, no-store'


def test_missing_configuration_does_not_open_access(client):
    with auth.database() as db:
        db.execute('DELETE FROM admin')
    assert client.get('/api/auth/session').json() == {'authenticated':False,'configured':False}
    assert client.get('/api/projects').status_code == 401
    assert client.get('/api/health').json() == {'status':'ok'}


def test_success_has_opaque_cookie_hashed_storage_csrf_and_logout(client):
    response = sign_in(client)
    assert response.status_code == 200
    cookie = response.headers.get_list('set-cookie')[0]
    assert 'HttpOnly' in cookie and 'SameSite=strict' in cookie and 'Path=/' in cookie
    token = client.cookies.get(auth.cookie_name())
    with auth.database() as db:
        row = db.execute("SELECT * FROM sessions WHERE kind='session'").fetchone()
        assert row['token_hash'] == auth.digest(token) and token not in json.dumps(dict(row))
        assert db.execute('SELECT password_hash FROM admin').fetchone()[0].startswith('$argon2id$')
    assert client.get('/api/projects').status_code == 200
    assert client.post('/api/projects',json={'name':'Blocked without CSRF'}).status_code == 403
    client.headers['X-Quark-CSRF'] = response.json()['csrfToken']
    assert client.post('/api/projects',json={'name':'Authorized with CSRF'}).status_code == 201
    assert client.post('/api/auth/logout').status_code == 200
    client.cookies.set(auth.cookie_name(), token)
    assert client.get('/api/projects').status_code == 401


def test_two_teachers_keep_independent_sessions(client):
    first = sign_in(client)
    token = client.cookies.get(auth.cookie_name())
    with TestClient(app) as second:
        assert sign_in(second).status_code == 200
        assert second.cookies.get(auth.cookie_name()) != token
        assert client.get('/api/projects').status_code == second.get('/api/projects').status_code == 200
        second.headers['X-Quark-CSRF'] = second.get('/api/auth/session').json()['csrfToken']
        second.post('/api/auth/logout')
        assert client.get('/api/projects').status_code == 200


@pytest.mark.parametrize('field',['expires','seen'])
def test_session_expiry_enforced_server_side(client, field):
    sign_in(client)
    with auth.database() as db:
        db.execute(f"UPDATE sessions SET {field}=? WHERE kind='session'", (time.time()-auth.SESSION_SECONDS-1,))
    assert client.get('/api/projects').status_code == 401


def test_password_change_revokes_existing_sessions(client):
    sign_in(client)
    auth.configure_password('Another-test-password-2026!')
    assert client.get('/api/projects').status_code == 401
    assert sign_in(client).status_code == 401
    assert sign_in(client,'Another-test-password-2026!').status_code == 200


def test_wrong_username_and_password_have_same_error(client):
    a = sign_in(client,'wrong-password')
    b = sign_in(client,username='other')
    assert a.status_code == b.status_code == 401 and a.json() == b.json()
    assert not client.cookies.get(auth.cookie_name())


def test_brute_force_limit_persists_and_ignores_forwarded_ip(client):
    for i in range(10):
        nonce = client.get('/api/auth/session').json()['csrfToken']
        response = client.post('/api/auth/login',json={'username':'admin','password':'bad'},headers={'X-Quark-CSRF':nonce,'X-Forwarded-For':f'192.0.2.{i}'})
        assert response.status_code == 401
    auth.init_db()
    response = sign_in(client)
    assert response.status_code == 429 and response.headers['Retry-After'] == '900'


@pytest.mark.parametrize('headers',[{'Origin':'https://evil.test'},{'Origin':'null'},{'Sec-Fetch-Site':'cross-site'},{'Host':'evil.test'},{'Host':'[invalid'}])
def test_foreign_origin_and_host_rejected_even_with_session(client,headers):
    response = sign_in(client)
    response = client.post('/api/projects',json={'name':'Rejected'},headers={'X-Quark-CSRF':response.json()['csrfToken'],**headers})
    assert response.status_code == 403


def test_login_needs_pre_session_csrf_and_rotates_it(client):
    assert client.post('/api/auth/login',json={'username':'admin','password':PASSWORD}).status_code == 403
    nonce = client.get('/api/auth/session').json()['csrfToken']
    old = client.cookies.get(auth.cookie_name('pre'))
    response = client.post('/api/auth/login',json={'username':'admin','password':PASSWORD},headers={'X-Quark-CSRF':nonce})
    assert response.status_code == 200 and nonce != response.json()['csrfToken']
    client.cookies.set(auth.cookie_name('pre'), old)
    assert client.post('/api/auth/login',json={'username':'admin','password':PASSWORD},headers={'X-Quark-CSRF':nonce}).status_code == 403


def test_public_origin_requires_https_and_secure_host_cookie(client, monkeypatch):
    monkeypatch.setenv('PUBLIC_APP_ORIGIN','http://quark.test')
    with pytest.raises(RuntimeError): auth.init_db()
    monkeypatch.setenv('PUBLIC_APP_ORIGIN','https://quark.test')
    auth.init_db()
    with TestClient(app,base_url='https://quark.test') as public_client:
        response = sign_in(public_client)
        assert response.status_code == 200
        cookie = response.headers.get_list('set-cookie')[0]
        assert cookie.startswith('__Host-quark-session=') and 'Secure' in cookie and 'Domain=' not in cookie
        assert public_client.get('/api/projects').status_code == 200


def test_bad_input_does_not_echo_password(client):
    nonce = client.get('/api/auth/session').json()['csrfToken']
    response = client.post('/api/auth/login',json={'password':PASSWORD},headers={'X-Quark-CSRF':nonce})
    assert response.status_code == 400 and PASSWORD not in response.text
    response = client.post('/api/auth/login',content=b'x'*4097,headers={'X-Quark-CSRF':nonce,'Content-Type':'application/json'})
    assert response.status_code == 413


def test_media_range_and_vector_download_require_cookie(client):
    name = 'auth-test.svg'
    file = store.DATA/'exports'/name
    file.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
    try:
        assert client.get('/media/exports/'+name).status_code == 401
        sign_in(client)
        response = client.get('/media/exports/'+name)
        assert response.status_code == 200 and 'sandbox' in response.headers['content-security-policy']
        assert client.get('/media/exports/'+name,headers={'Range':'bytes=0-9'}).status_code == 206
    finally:
        file.unlink(missing_ok=True)


def test_anonymous_nonce_storage_is_bounded(client):
    with auth.database() as db:
        for _ in range(270): auth.issue(db,'pre')
        assert db.execute("SELECT count(*) FROM sessions WHERE kind='pre'").fetchone()[0] == 256


def test_signed_webhook_keeps_its_own_authentication(client):
    assert client.post('/webhooks/instagram',json={}).status_code == 403


def test_restart_keeps_live_sessions_and_never_accepts_url_tokens(client):
    sign_in(client)
    token = client.cookies.get(auth.cookie_name())
    auth.init_db()
    assert client.get('/api/projects').status_code == 200
    with TestClient(app) as anonymous:
        assert anonymous.get('/api/projects',params={'token':token}).status_code == 401
        assert anonymous.get('/api/projects',headers={'Authorization':'Bearer '+token}).status_code == 401


def test_nonce_from_another_browser_does_not_authorize_login(client):
    nonce = client.get('/api/auth/session').json()['csrfToken']
    with TestClient(app) as second:
        second.get('/api/auth/session')
        assert second.post('/api/auth/login',json={'username':'admin','password':PASSWORD},headers={'X-Quark-CSRF':nonce}).status_code == 403


def test_weak_password_is_not_configured(client):
    with pytest.raises(ValueError): auth.configure_password('admin')
    assert sign_in(client).status_code == 200
