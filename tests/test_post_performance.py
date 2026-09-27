import asyncio
import pytest
from backend import agent, brief, store


@pytest.mark.parametrize("medium,setting,fast", [
    ("image", "off", True), ("carousel", "off", True),
    ("image", "on", False), ("image", "invalid", False),
    ("video", "off", False), ("chat", "off", False),
])
def test_fast_thinking_only_affects_static_production_and_can_be_disabled(monkeypatch, medium, setting, fast):
    store.init_db()
    pid = store.create_project("Performance")["id"]
    monkeypatch.setenv("QUARK_POST_REASONING", setting)
    if medium != "chat":
        brief.maybe_start(pid, "Creá una imagen de café", "content", [], quiet=True)
        answers = brief.Answers(subject="Café", medium=medium, video_mode="animation", copy_mode="exact", copy_text="Tu pausa, tu café.")
        with store.connection() as db:
            db.execute("UPDATE project_briefs SET answers=?,status='generating' WHERE project_id=?", (answers.model_dump_json(), pid))
    sent = []
    class Response:
        status_code = 200
        def json(self): return {"choices":[{"message":{"content":"Listo, preparé el contenido."}}], "usage":{}}
    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, **kwargs):
            sent.append(kwargs["json"])
            return Response()
    monkeypatch.setattr(agent.httpx, "AsyncClient", Client)
    monkeypatch.setattr(agent, "import_hermes_media", lambda *a, **k: [] if medium == "chat" else ["/media/exports/test.mp4" if medium == "video" else "/media/exports/test.svg"])
    monkeypatch.setattr(agent, "assemble_rendered_scenes", lambda *args: False)
    asyncio.run(agent._hermes_chat(pid, "Creá mi pieza" if medium != "chat" else "Ideas de campañas", "strategy" if medium == "chat" else "content", [], {}))
    assert ("model_options" in sent[0]) == fast
    if fast:
        assert sent[0]["model_options"] == {"reasoning":{"enabled":False}}
    prompt = sent[0]["messages"][0]["content"]
    assert ("# Flujo eficiente para publicaciones" in prompt) == (medium in ("image", "carousel"))
    if medium in ("image", "carousel"):
        assert "inspeccioná ese PNG" in prompt and "entrega SVG+PNG" in prompt
        assert "--batch" in prompt
        assert "no agregues eslóganes, texto de apoyo" in prompt
