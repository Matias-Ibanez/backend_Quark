import asyncio
import pytest
from conftest import authenticated_client as TestClient
from backend.app import app
from backend import agent, brief, store, workspace


@pytest.fixture
def conversation(monkeypatch):
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test')
    async def plan(*args):
        return brief.Intake(answers=brief.Answers(subject='', aspect='square'), missing=['subject', 'aspect'])
    monkeypatch.setattr(brief, 'assess', plan)
    with TestClient(app) as client:
        pid = store.create_project('Preguntas en conversación')['id']
        asyncio.run(agent.chat(pid, 'Creame una imagen'))
        yield client, pid


def reply(client, pid, message, **override):
    current = client.get(f'/api/projects/{pid}/brief').json()['brief']
    return client.post(f'/api/projects/{pid}/brief/reply', json={'id': current['id'], 'version': current['version'], 'message': message, **override})


def test_inline_text_choice_and_reload_preserve_question_progress(conversation, monkeypatch):
    client, pid = conversation
    url = f'/api/projects/{pid}/brief'
    assert client.get(url).json()['question'] == 'subject'
    assert reply(client, pid, 'Café de especialidad').status_code == 200
    current = client.get(url).json()
    assert current['question'] == 'aspect' and current['answered'] == ['subject']
    history = store.messages(pid)
    assert history[-2]['role'] == 'assistant' and 'comunicar' in history[-2]['content']
    assert history[-1]['role'] == 'user' and history[-1]['content'] == 'Café de especialidad'
    assert reply(client, pid, 'una opción inválida').status_code == 422
    assert reply(client, pid, '1:1').status_code == 200
    store.init_db()
    assert client.get(url).json()['question'] is None
    history = store.messages(pid)
    assert any('Café de especialidad' in turn['content'] for turn in history if turn['role'] == 'user')
    assert any('Cuadrado' in turn['content'] for turn in history if turn['role'] == 'user')
    assert reply(client, pid, 'Café de especialidad', version=1).status_code == 409
    calls = []
    async def start(pid, body):
        calls.append(body)
        return {'id': 'run', 'status': 'running'}
    monkeypatch.setattr(workspace, 'start_run', start)
    assert reply(client, pid, 'Crear').status_code == 200
    assert reply(client, pid, 'Crear').status_code == 409
    assert len(calls) == 1
    assert store.messages(pid)[-1]['content'] == 'Crear la pieza con mis respuestas.'


def test_faq_and_scope_guard_do_not_advance_the_question(conversation):
    client, pid = conversation
    for message in ('Quien sos?', 'Escribime un programa Python para ordenar una lista'):
        assert reply(client, pid, message).status_code == 200
        state = client.get(f'/api/projects/{pid}/brief').json()
        assert state['question'] == 'subject' and not state['answered']
    assert reply(client, pid, 'cancelar').status_code == 200
    assert brief.get(pid)['status'] == 'cancelled'


def test_exact_text_is_not_accepted_when_empty(conversation):
    client, pid = conversation
    assert reply(client, pid, 'Café').status_code == 200
    assert reply(client, pid, 'Cuadrado').status_code == 200
    saved = brief.get(pid)
    with store.connection() as db:
        db.execute('UPDATE brief_questions SET fields=? WHERE brief_id=?', ('["copy_text"]', saved['id']))
    assert client.get(f'/api/projects/{pid}/brief').json()['question'] == 'copy_text'
    assert reply(client, pid, '   ').status_code == 422
    assert reply(client, pid, 'Mi promoción').status_code == 200
    assert brief.get(pid)['answers']['copy_text'] == 'Mi promoción'
