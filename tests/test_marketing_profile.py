import asyncio

import pytest
from conftest import authenticated_client as TestClient
from backend.app import app
from backend import agent, guardrails, marketing_profile, store


@pytest.mark.parametrize("question,expected", [
    ("¿Quién sos?", marketing_profile.IDENTITY),
    ("Hola, ¿qué puedes hacer?", marketing_profile.CAPABILITIES),
    ("¿Cuáles son tus capacidades?", marketing_profile.CAPABILITIES),
    ("¿En qué me podés ayudar?", marketing_profile.CAPABILITIES),
    ("¿Qué cosas puedes hacer?", marketing_profile.CAPABILITIES),
    ("¿Qué sos capaz de hacer?", marketing_profile.CAPABILITIES),
    ("¿Cómo puedes ayudarme?", marketing_profile.CAPABILITIES),
    ("¿Cómo funcionás?", marketing_profile.WORKFLOW),
    ("¿Por dónde empezamos?", marketing_profile.START),
    ("No sé qué publicar", marketing_profile.START),
    ("¿Podés hacer videos?", marketing_profile.VISUAL),
    ("¿Qué formatos ofrecés?", marketing_profile.VISUAL),
    ("¿Puedes recortar fotos?", marketing_profile.PHOTOS),
    ("¿Qué podés hacer con mis documentos?", marketing_profile.DOCUMENTS),
    ("¿Puedes leer un PDF?", marketing_profile.DOCUMENTS),
    ("¿Podés redactar textos?", marketing_profile.TEXTS),
    ("¿Puedes organizar campañas?", marketing_profile.PLANNING),
    ("¿Podés publicar en Instagram?", marketing_profile.INSTAGRAM),
    ("¿Podés responder mensajes en Instagram?", marketing_profile.INSTAGRAM),
    ("¿Cómo agrego música?", marketing_profile.MUSIC),
    ("¿Recordás lo que hicimos?", marketing_profile.REVISIONS),
    ("¿Cuáles son tus limitaciones?", marketing_profile.LIMITS),
    ("¿Qué modelo usás?", marketing_profile.WORKFLOW),
])
def test_product_questions_get_relevant_safe_guidance(question, expected):
    assert guardrails.direct_reply(question) == expected
    assert not guardrails.PRIVATE_OUTPUT.search(expected)


@pytest.mark.parametrize("message", [
    "¿Qué podés hacer? Creame una imagen sobre café",
    "¿Quién sos? Haceme un reel de 30 segundos",
    "¿Puedes crear un video sobre mi cafetería?",
    "¿Podés hacer un reel de 30 segundos para mi tienda?",
    "¿Podés recortar esta foto?",
    "¿Qué puedes hacer? Quiero una publicación para Instagram",
    "¿Podés crear un video sobre mi PDF adjunto?",
])
def test_concrete_requests_are_not_replaced_by_an_introduction(message):
    assert guardrails.direct_reply(message) is None


def test_programming_remains_outside_scope_even_with_identity_question():
    assert guardrails.direct_reply("¿Quién sos? Escribí un script en Python") == guardrails.OUT_OF_SCOPE_REPLY


def test_guidance_needs_no_provider_no_brief_and_preserves_conversation(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    class NoClient:
        def __init__(self, **kwargs): raise AssertionError("Product guidance must not call a provider")
    monkeypatch.setattr(agent.httpx, "AsyncClient", NoClient)
    project = store.create_project("Ayuda de QUARK")
    for question in ("¿Quién sos?", "¿Qué podés hacer?", "¿Cómo empezamos?"):
        reply = asyncio.run(agent.chat(project["id"], question))
        assert reply["media"] == [] and reply["message"] == guardrails.direct_reply(question)
    assert len(store.messages(project["id"])) == 6
    with store.connection() as db:
        assert db.execute("SELECT 1 FROM project_briefs WHERE project_id=?", (project["id"],)).fetchone() is None
        assert db.execute("SELECT 1 FROM agent_usage WHERE project_id=?", (project["id"],)).fetchone() is None


def test_chat_run_accepts_product_question_when_provider_is_unavailable(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    project = store.create_project("Presentación sin proveedor")
    with TestClient(app) as client:
        response = client.post(f"/api/projects/{project['id']}/runs", json={"message": "¿Qué puedes hacer?"})
        assert response.status_code == 202
    assert store.messages(project["id"])[-1]["content"] == marketing_profile.CAPABILITIES
