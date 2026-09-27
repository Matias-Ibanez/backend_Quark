import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from backend import agent, brief, shorts, store
from backend.app import app


def prepare(monkeypatch, message, *, guessed_mode="clips"):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test")
    async def plan(pid, request, function, seeded):
        return brief.Intake(answers=brief.Answers(subject="Café de especialidad", medium="video", aspect="story", seconds=20, video_mode=guessed_mode), missing=[])
    monkeypatch.setattr(brief, "assess", plan)
    pid = store.create_project("Dirección de video")["id"]
    return pid, asyncio.run(agent.chat(pid, message))


def test_ambiguous_cafe_short_asks_visual_direction_even_if_model_guesses_clips(monkeypatch):
    pid, result = prepare(monkeypatch, "Haceme un short de 20 segundos sobre por qué somos una buena cafetería")
    state = brief.read_brief(pid)
    assert state["question"] == "video_mode"
    assert {key for key, _ in state["fields"][0]["choices"]} == {"clips", "animation"}
    assert "moneyprinter" not in json.dumps(state).lower() and "manim" not in json.dumps(state).lower()
    assert not result["media"] and not brief.production_context(pid)
    with store.connection() as db:
        assert db.execute("SELECT COUNT(*) FROM agent_usage WHERE project_id=?", (pid,)).fetchone()[0] == 0


@pytest.mark.parametrize("answer, mode, engine", [("clips", "clips", "clips"), ("animaciones", "animation", "hermes")])
def test_inline_choice_persists_and_controls_renderer_on_confirmation(monkeypatch, answer, mode, engine):
    pid, _ = prepare(monkeypatch, "Haceme un short de 20 segundos sobre café")
    saved = brief.get(pid)
    with TestClient(app) as client:
        response = client.post(f"/api/projects/{pid}/brief/reply", json={"id": saved["id"], "version": saved["version"], "message": answer})
    assert response.status_code == 200
    saved = brief.get(pid)
    assert saved["answers"]["video_mode"] == mode
    assert brief.read_brief(pid)["question"] is None
    store.init_db()
    assert brief.get(pid)["answers"]["video_mode"] == mode
    called = []
    async def render_clips(*args, **kwargs):
        called.append("clips")
        assert kwargs["record_user"] is False
        return {"media": ["/media/exports/final.mp4"]}
    async def render_animation(*args, **kwargs):
        called.append("hermes")
        assert kwargs["record_user"] is False
        return {"media": ["/media/exports/final.mp4"]}
    monkeypatch.setattr(shorts, "create_short", render_clips)
    monkeypatch.setattr(agent, "_hermes_chat", render_animation)
    brief.finish(pid, "confirmed")
    asyncio.run(agent.chat(pid, saved["request"], brief_id=saved["id"]))
    assert called == [engine]
    assert brief.get(pid)["status"] == "done"


def test_explicit_animated_short_produces_without_style_question(monkeypatch):
    called = []
    async def render(*args, **kwargs):
        called.append("hermes")
        return {"media": ["/media/exports/final.mp4"]}
    async def no_stock(*args, **kwargs):
        raise AssertionError("An animated explanation must not become a stock montage")
    monkeypatch.setattr(agent, "_hermes_chat", render)
    monkeypatch.setattr(shorts, "create_short", no_stock)
    pid, result = prepare(monkeypatch, "Creá un short animado de 20 segundos sobre una ecuación", guessed_mode="clips")
    assert called == ["hermes"] and result["media"]
    assert brief.get(pid)["answers"]["video_mode"] == "animation"


def test_revision_can_change_visual_direction_and_keeps_it_for_next_turn(monkeypatch):
    pid, _ = prepare(monkeypatch, "Haceme un short de 20 segundos sobre café")
    with store.connection() as db:
        db.execute("UPDATE project_briefs SET status='done' WHERE project_id=?", (pid,))
    assert brief.production_context(pid, "Rehacelo con animaciones y gráficos")["video_mode"] == "animation"
    assert not shorts.should_use_clips(brief.production_context(pid), "Ahora cambiá el título", "shorts")
    assert brief.production_context(pid, "Usá clips reales en su lugar")["video_mode"] == "clips"


def test_user_assets_are_offered_only_when_attached_and_cannot_be_faked(monkeypatch):
    pid, _ = prepare(monkeypatch, "Haceme un short con mis fotos de 20 segundos")
    saved = brief.get(pid)
    assert saved["answers"]["video_mode"] == "auto"
    with TestClient(app) as client:
        response = client.put(f"/api/projects/{pid}/brief", json={"id": saved["id"], "version": saved["version"], "field": "video_mode", "answers": {**saved["answers"], "video_mode": "assets"}})
    assert response.status_code == 422
    # An existing original photo makes the owned-material direction available.
    photo = store.add_asset("photo.png", "photo.png", "image", 1, 1)
    store.attach_assets(pid, [photo["id"]])
    choices = next(f for f in brief.read_brief(pid)["fields"] if f["key"] == "video_mode")["choices"]
    assert "assets" in {key for key, _ in choices}


def test_negative_clips_request_does_not_infer_stock():
    assert brief.video_direction("Un short sin clips") is None
    assert brief.video_direction("Un short con los clips de stock") == "clips"


@pytest.mark.parametrize("message,aspect", [("Haceme un short de 20 segundos sobre café", "story"), ("Haceme un short cuadrado de 20 segundos sobre café", "square"), ("Haceme un short 4:5 de 20 segundos sobre café", "portrait")])
def test_short_defaults_to_vertical_and_preserves_explicit_ratio(monkeypatch, message, aspect):
    # An incorrect generic post default from the model must not override a short's format.
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test")
    async def plan(*args):
        return brief.Intake(answers=brief.Answers(subject="Café", medium="video", aspect="landscape"), missing=["aspect"])
    monkeypatch.setattr(brief, "assess", plan)
    pid = store.create_project("Formato de short")["id"]
    asyncio.run(agent.chat(pid, message))
    assert brief.get(pid)["answers"]["aspect"] == aspect
    assert "aspect" not in {f["key"] for f in brief.read_brief(pid)["fields"]}
