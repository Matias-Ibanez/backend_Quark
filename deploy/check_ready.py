"""Run inside studio: bounded readiness checks, without LLM calls or tokens in logs."""
import os
import time

import httpx


def check():
    with httpx.Client(timeout=5, trust_env=False) as client:
        api = client.get('http://localhost:8000/api/health')
        assert api.status_code == 200 and api.json().get('status') == 'ok'
        session = client.get('http://localhost:8000/api/auth/session')
        assert session.status_code == 200 and session.json().get('configured') is True
        assert client.get('http://localhost:8000/api/projects').status_code == 401
        hermes = os.environ['HERMES_BASE_URL'].rstrip('/').removesuffix('/v1')
        assert client.get(hermes+'/health', headers={
            'Authorization': 'Bearer '+os.environ['HERMES_API_KEY']}).status_code == 200
        shorts = os.environ['SHORTS_BASE_URL'].rstrip('/')
        assert client.get(shorts+'/api/v1/tasks', headers={
            'x-api-key': os.environ['SHORTS_API_KEY']}).status_code == 200


if __name__ == '__main__':
    deadline, attempt = time.monotonic()+300, 0
    while time.monotonic() < deadline:
        attempt += 1
        try:
            check()
        except (httpx.HTTPError, AssertionError, ValueError):
            print(f'Esperando API, autenticación y motores multimedia (intento {attempt}).', flush=True)
            time.sleep(3)
        else:
            print('Backend listo: admin configurado, acceso privado y motores disponibles.')
            break
    else:
        raise SystemExit('El backend no superó las comprobaciones de arranque.')
