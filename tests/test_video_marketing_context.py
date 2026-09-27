import asyncio
import pytest
from fastapi.testclient import TestClient
from backend import agent, brief, store, workspace
from backend.app import app

REQUEST = "Creá un reel de 10 segundos con Manim sobre café, 9:16, sin voz"
KNOWN = "Mi marca es Pausa, una cafetería para vecinos. Busco vender café."
EVIDENCE = {"brand": "Pausa", "audience": "vecinos", "objective": "vender café"}


def prepare(monkeypatch, *, history=None, role="user", evidence=None, message=REQUEST):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test")
    pid = store.create_project("Contexto de marketing")["id"]
    if history:
        store.add_message(pid, role, history)
    async def plan(*args):
        # Even complete-looking guesses must not bypass the context questions.
        return brief.Intake(answers=brief.Answers(brand="Pausa, cafetería", audience="vecinos", objective="sell",
            subject="Café", medium="video", video_mode="animation", seconds=10, aspect="story"),
            missing=[], evidence=evidence or {})
    monkeypatch.setattr(brief, "assess", plan)
    return pid, asyncio.run(agent.chat(pid, message))


def test_renderer_and_format_are_not_a_marketing_context(monkeypatch):
    pid, result = prepare(monkeypatch)
    state = brief.read_brief(pid)
    assert not result["media"] and brief.production_context(pid) is None
    assert [f["key"] for f in state["fields"]] == ["brand", "audience", "objective"]
    assert state["question"] == "brand"
    assert state["brief"]["answers"]["brand"] == ""
    assert state["brief"]["answers"]["audience"] == ""
    with store.connection() as db:
        assert db.execute("SELECT COUNT(*) FROM agent_usage WHERE project_id=?", (pid,)).fetchone()[0] == 0


def test_inline_context_is_persistent_and_required_before_render(monkeypatch):
    pid, _ = prepare(monkeypatch)
    async def start_run(project_id, body):
        answers = brief.get(project_id)["answers"]
        assert answers["brand"] == "Pausa, una cafetería"
        assert answers["audience"] == "Vecinos del barrio" and answers["objective"] == "sell"
        return {"id":"confirmed", "status":"running"}
    monkeypatch.setattr(workspace, "start_run", start_run)
    with TestClient(app) as client:
        for key, answer in [("brand", "Pausa, una cafetería"), ("audience", "Vecinos del barrio"), ("objective", "Vender")]:
            state = brief.read_brief(pid); saved = state["brief"]
            assert state["question"] == key
            early = client.put(f"/api/projects/{pid}/brief", json={"id":saved["id"], "version":saved["version"], "action":"confirm", "answers":saved["answers"]})
            assert early.status_code == 422
            response = client.post(f"/api/projects/{pid}/brief/reply", json={"id":saved["id"], "version":saved["version"], "message":answer})
            assert response.status_code == 200
            store.init_db()
        saved = brief.get(pid)
        assert brief.read_brief(pid)["question"] is None
        assert client.post(f"/api/projects/{pid}/brief/reply", json={"id":saved["id"], "version":saved["version"], "message":"Crear"}).status_code == 200


@pytest.mark.parametrize("role,history,evidence", [
    ("assistant", KNOWN, EVIDENCE),
    ("user", "Hola", EVIDENCE),
    ("user", KNOWN, {}),
])
def test_only_evidenced_user_data_satisfies_context(monkeypatch, role, history, evidence):
    pid, _ = prepare(monkeypatch, role=role, history=history, evidence=evidence)
    assert {f["key"] for f in brief.read_brief(pid)["fields"]} == {"brand", "audience", "objective"}


def test_known_context_is_not_reasked_and_reaches_production(monkeypatch):
    async def render(pid, *args, **kwargs):
        context = brief.production_context(pid)
        assert context["brand"] == "Pausa, cafetería" and context["objective"] == "sell"
        return {"media":["/media/exports/demo.mp4"]}
    monkeypatch.setattr(agent, "_hermes_chat", render)
    pid, result = prepare(monkeypatch, history=KNOWN, evidence=EVIDENCE)
    assert result["media"] and brief.get(pid)["status"] == "done"
    assert {"brand", "audience", "objective"} <= set(brief.read_brief(pid)["answered"])


def test_confirmed_brand_and_audience_survive_a_new_piece_in_same_chat(monkeypatch):
    pid, _ = prepare(monkeypatch, history=KNOWN, evidence=EVIDENCE, message=REQUEST.replace("sin voz", ""))
    brief.finish(pid, "done")
    # Later planning must not forget data just because no quote was returned this time.
    async def plan(*args):
        return brief.Intake(answers=brief.Answers(subject="Café", medium="video", video_mode="animation"), missing=[])
    monkeypatch.setattr(brief, "assess", plan)
    asyncio.run(agent.chat(pid, "Creá un nuevo reel de 10 segundos con Manim sobre café sin voz"))
    state = brief.read_brief(pid)
    assert state["brief"]["answers"]["brand"] == "Pausa, cafetería"
    assert state["brief"]["answers"]["audience"] == "vecinos"
    assert [f["key"] for f in state["fields"]] == ["objective"]


def test_context_does_not_leak_between_conversations(monkeypatch):
    pid, _ = prepare(monkeypatch, history=KNOWN, evidence=EVIDENCE, message=REQUEST.replace("sin voz", ""))
    other, _ = prepare(monkeypatch)
    assert pid != other
    assert brief.read_brief(other)["question"] == "brand"


def test_unbranded_content_is_a_valid_context(monkeypatch):
    async def plan(*args):
        return brief.Intake(answers=brief.Answers(brand="Sin marca, curso de marketing", audience="estudiantes", objective="educate",
            subject="Embudo de ventas", medium="video", video_mode="animation", seconds=10), missing=[],
            evidence={"brand":"Sin marca", "audience":"estudiantes", "objective":"explicar"})
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test")
    monkeypatch.setattr(brief, "assess", plan)
    async def render(*args, **kwargs): return {"media":["/media/exports/demo.mp4"]}
    monkeypatch.setattr(agent, "_hermes_chat", render)
    pid = store.create_project("Sin marca")["id"]
    result = asyncio.run(agent.chat(pid, "Sin marca: creá un reel de 10 segundos con gráficos para explicar el embudo de ventas a estudiantes, sin voz"))
    assert result["media"] and brief.get(pid)["status"] == "done"
