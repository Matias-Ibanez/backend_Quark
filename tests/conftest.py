import os
import tempfile

# All modules share an isolated database and never inherit paid provider credentials.
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="quark-test-")
os.environ["QUARK_AUTH_DIR"] = tempfile.mkdtemp(prefix="quark-auth-test-")
os.environ.pop("PUBLIC_APP_ORIGIN", None)
os.environ.pop("PUBLIC_API_ORIGIN", None)
os.environ.pop("DEEPSEEK_API_KEY", None)


_test_session = None


def authenticated_client(app, **kwargs):
    """Existing product tests use a real session; auth tests start anonymously."""
    from fastapi.testclient import TestClient
    from backend import auth
    global _test_session
    if not auth.configured():
        auth.configure_password('Only-for-isolated-tests-2026!')
    client = TestClient(app, **kwargs)
    if not _test_session or not auth.find_session(_test_session[0]):
        with auth.database() as db:
            _test_session = auth.issue(db, 'session')
    token, csrf = _test_session
    client.cookies.set(auth.cookie_name(), token)
    client.headers['X-Quark-CSRF'] = csrf
    return client
