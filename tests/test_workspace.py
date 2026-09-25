"""Chat-first flow: real persistence, immutable approvals, resumable exports."""
import asyncio
import json
from datetime import datetime, timedelta, timezone
from test_studio import client, project, upload_image
from backend import store, agent, workspace, instagram


def completed_job(p, quality="final"):
    job_id = store.uid()
    payload = {"document": p["document"], "revision": p["revision"], "kind": "png", "quality": quality, "scene": 0, "hermes": True}
    with store.connection() as db:
        db.execute("INSERT INTO jobs (id,project_id,kind,status,progress,payload,result,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)", (job_id, p["id"], "render", "done", 1, json.dumps(payload), json.dumps({"url": "/media/exports/test.png", "filename": "test.png"}), store.now(), store.now()))
    return store.get_job(job_id)


def test_assets_are_scoped_and_no_key_does_not_invent_turn():
    p, other, asset = project(), project(), upload_image()
    response = client.post(f"/api/projects/{p['id']}/runs", json={"message": "Usá mi producto", "assetIds": [asset["id"]]})
    assert response.status_code == 503
    assert client.get(f"/api/projects/{p['id']}/messages").json() == []
    assert [a["id"] for a in store.project_assets(p["id"])] == [asset["id"]]
    assert store.project_assets(other["id"]) == []
    assert client.post(f"/api/projects/{p['id']}/runs", json={"message": "Foto", "assetIds": ["missing"]}).status_code == 404


def test_calendar_requires_final_approval_and_connection(monkeypatch):
    p = project()
    job = completed_job(p)
    date = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    body = {"project_id": p["id"], "job_id": job["id"], "title": "Promo", "scheduled_at": date}
    response = client.post("/api/calendar", json=body)
    assert response.status_code == 201
    event = response.json()
    url = f"/api/calendar/{event['id']}"
    assert client.post("/api/calendar", json=body).status_code == 409
    assert client.patch(url, json={"action": "schedule"}).status_code == 409
    assert client.patch(url, json={"action": "approve"}).json()["status"] == "approved"
    monkeypatch.delenv("INSTAGRAM_ACCESS_TOKEN", raising=False)
    assert client.patch(url, json={"action": "schedule"}).status_code == 503
    p["document"]["caption"] = "No reemplazar la pieza aprobada"
    store.update_project(p["id"], p["document"], 1)
    assert store.get_job(job["id"])["payload"]["document"]["caption"] == ""
    assert client.patch(url, json={"action": "reschedule", "scheduled_at": date}).json()["status"] == "draft"
    preview = completed_job(p, "preview")
    event = client.post("/api/calendar", json={**body, "job_id": preview["id"]}).json()
    assert client.patch(f"/api/calendar/{event['id']}", json={"action": "approve"}).status_code == 422
    assert client.post("/api/calendar", json={**body, "scheduled_at": "2026-12-10T12:00:00"}).status_code == 422


def test_calendar_scheduler_claims_once_and_does_not_retry_uncertain(monkeypatch):
    p = project()
    job = completed_job(p)
    event = workspace.create_draft(workspace.CalendarDraft(project_id=p["id"], job_id=job["id"], title="Post", scheduled_at=datetime.now(timezone.utc) - timedelta(minutes=1)))
    with store.connection() as db:
        db.execute("UPDATE calendar SET status='scheduled' WHERE id=?", (event["id"],))
    calls = []
    async def uncertain(job_id):
        calls.append(job_id)
        raise RuntimeError("ambiguous timeout")
    monkeypatch.setattr(instagram, "publish", uncertain)
    asyncio.run(workspace.publish_due())
    asyncio.run(workspace.publish_due())
    assert calls == [job["id"]]
    assert workspace.get_event(event["id"])["status"] == "needs_review"


def test_run_persists_failure_and_context(monkeypatch):
    p = project()
    seen = []
    async def fake_chat(project_id, message, function, assets, run_id=None):
        seen.append((project_id, message, function, assets, run_id))
        raise ValueError("private implementation detail")
    monkeypatch.setattr(agent, "chat", fake_chat)
    run_id = store.uid()
    with store.connection() as db:
        db.execute("INSERT INTO runs VALUES (?,?,'running',NULL,?)", (run_id, p["id"], store.now()))
    asyncio.run(workspace.execute_run(run_id, p["id"], workspace.Chat(message="Planificá", function="calendar")))
    result = client.get(f"/api/projects/{p['id']}/runs").json()[0]
    assert result["status"] == "failed"
    assert "private" not in result["error"]
    assert seen == [(p["id"], "Planificá", "calendar", [], run_id)]


def test_proxy_preserves_origin_protection():
    assert client.get("/api/settings", headers={"Host": "studio:8000", "Origin": "http://localhost:8010"}).status_code == 200
    assert client.get("/api/settings", headers={"Host": "localhost:8011", "Origin": "http://localhost:3000"}).status_code == 200
    assert client.get("/api/settings", headers={"Host": "studio:8000", "Origin": "https://evil.example"}).status_code == 403
