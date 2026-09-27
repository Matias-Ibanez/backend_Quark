import asyncio

import pytest

from backend import agent, brief, narration, store


@pytest.mark.parametrize("seconds", [None, 5, 30, 180])
def test_shared_guide_fits_moneyprinter_prompt_limit(seconds):
    prompt = narration.clip_script_prompt(seconds)
    assert len(prompt) <= 2000
    assert narration.SPOKEN_GUIDE in prompt
    assert "## Producción y revisión" not in prompt and "narration.txt" not in prompt
    assert (f"{seconds * 2} palabras" if seconds else "50 a 80 palabras") in prompt


@pytest.mark.parametrize("medium,voice", [("image", "none"), ("video", "none"), ("video", "voice")])
def test_hermes_receives_narration_skill_only_for_spoken_video(monkeypatch, medium, voice):
    store.init_db()
    project = store.create_project("Guion de café")
    pid = project["id"]
    brief.maybe_start(pid, "Un video de café" if medium == "video" else "Una imagen de café", "content", [], quiet=True)
    answers = brief.Answers(subject="Café molido al pedir", medium=medium, narration=voice, video_mode="animation",
                            seconds=20, facts="Molemos al pedir", copy_mode="exact", copy_text="Tu pausa, tu café.")
    with store.connection() as db:
        db.execute("UPDATE project_briefs SET answers=?,status='generating' WHERE project_id=?", (answers.model_dump_json(), pid))
    submitted = []

    class Response:
        status_code = 200
        def json(self):
            return {"choices": [{"message": {"content": "Listo, preparé tu contenido."}}], "usage": {}}

    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, **kwargs):
            submitted.append(kwargs["json"]["messages"][0]["content"])
            return Response()

    def import_media(*args, **kwargs):
        assert args[4] == (voice == "voice")
        return ["/media/exports/test.mp4" if medium == "video" else "/media/exports/test.svg"]

    monkeypatch.setattr(agent.httpx, "AsyncClient", Client)
    monkeypatch.setattr(agent, "import_hermes_media", import_media)
    monkeypatch.setattr(agent, "assemble_rendered_scenes", lambda *args: False)
    asyncio.run(agent._hermes_chat(pid, "Creá mi pieza", "content", [], {}))
    assert (narration.SKILL in submitted[0]) == (medium == "video" and voice == "voice")
    assert '"copy_text": "Tu pausa, tu café."' in submitted[0] and '"facts": "Molemos al pedir"' in submitted[0]
