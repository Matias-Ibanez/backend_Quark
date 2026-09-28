import asyncio
import pytest
from conftest import authenticated_client as TestClient
from backend import agent, brief, shorts, store, workspace
from backend.app import app

CUES = {"animation":"con diagramas", "motion":"con diseño animado", "clips":"con clips reales", "assets":"con mis fotos"}


def setup(monkeypatch, client, mode, suffix="", guessed_voice="voice"):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test")
    async def plan(*args):
        store.add_message(args[0], "user", "Mi marca es Pausa, una cafetería para vecinos. Busco vender café.")
        return brief.Intake(evidence={"brand":"Pausa", "audience":"vecinos", "objective":"vender café"}, answers=brief.Answers(brand="Pausa, cafetería", audience="vecinos", objective="sell", subject="Café", medium="video", video_mode=mode,
            seconds=10, aspect="story", narration=guessed_voice), missing=[])
    monkeypatch.setattr(brief, "assess", plan)
    pid = store.create_project("Elegir voz")["id"]
    assets = [store.add_asset("foto.png", "foto.png", "image", 1, 1)["id"]] if mode == "assets" else []
    request = f"Creá un reel de 10 segundos sobre café {CUES[mode]} {suffix}"
    return pid, asyncio.run(agent.chat(pid, request, "shorts", assets))


@pytest.mark.parametrize("mode", CUES)
@pytest.mark.parametrize("answer,expected", [("Sí", "voice"), ("Sin voz", "none")])
def test_all_video_styles_wait_for_voice_choice_and_persist_it(monkeypatch, mode, answer, expected):
    with TestClient(app) as client:
        pid, result = setup(monkeypatch, client, mode)
        state = brief.read_brief(pid)
        assert not result.get("media") and brief.production_context(pid) is None
        assert state["question"] == "narration"
        assert {key for key, _ in state["fields"][0]["choices"]} == {"voice", "none"}
        saved = state["brief"]
        # A technical default or guessed voice value is not a user decision.
        early = client.put(f"/api/projects/{pid}/brief", json={"id":saved["id"], "version":saved["version"], "action":"confirm", "answers":saved["answers"]})
        assert early.status_code == 422
        selected = client.post(f"/api/projects/{pid}/brief/reply", json={"id":saved["id"], "version":saved["version"], "message":answer})
        assert selected.status_code == 200
        store.init_db()
        assert brief.get(pid)["answers"]["narration"] == expected
        assert brief.get(pid)["answers"]["video_mode"] == mode
        assert brief.read_brief(pid)["question"] is None
        async def start_run(project_id, body):
            context = brief.get(project_id)["answers"]
            assert context["narration"] == expected and context["video_mode"] == mode
            return {"id":"test", "status":"running"}
        monkeypatch.setattr(workspace, "start_run", start_run)
        saved = brief.get(pid)
        confirmed = client.post(f"/api/projects/{pid}/brief/reply", json={"id":saved["id"], "version":saved["version"], "message":"Crear"})
        assert confirmed.status_code == 200
        brief.finish(pid, "done")
        assert brief.production_context(pid, "Cambiá el título")["narration"] == expected
        changed = "sin voz" if expected == "voice" else "con voz"
        assert brief.production_context(pid, f"Rehacé el video {changed}")["narration"] != expected


@pytest.mark.parametrize("mode", CUES)
@pytest.mark.parametrize("voice_request,expected", [("con voz", "voice"), ("sin voz en off", "none")])
def test_explicit_voice_request_does_not_ask_again(monkeypatch, mode, voice_request, expected):
    async def produce(pid, *args, **kwargs):
        context = brief.production_context(pid)
        assert context["narration"] == expected
        return {"media":["/media/exports/test.mp4"]}
    monkeypatch.setattr(agent, "_hermes_chat", produce)
    monkeypatch.setattr(shorts, "create_short", produce)
    with TestClient(app) as client:
        pid, result = setup(monkeypatch, client, mode, voice_request, "none" if expected == "voice" else "voice")
        assert result["media"]
        assert brief.get(pid)["status"] == "done"


@pytest.mark.parametrize("message,expected", [
    ("Con voz en off", "voice"), ("Sin voz en off", "none"),
    ("Video narrado", "voice"), ("No quiero narración", "none"),
    ("Sin voz, mejor con voz", "voice"), ("Con voz, mejor sin voz", "none"),
    ("¿Con voz o sin voz?", None), ("Con música", None),
])
def test_voice_cues_do_not_confuse_music_or_negation(message, expected):
    assert brief.narration_direction(message) == expected
