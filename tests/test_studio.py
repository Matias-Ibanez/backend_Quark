import asyncio
import hashlib
import hmac
import io
import json
import os
import subprocess
import tempfile
import time

import pytest

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="quark-test-")
os.environ.pop("DEEPSEEK_API_KEY", None)

from fastapi.testclient import TestClient
from PIL import Image
from backend.app import app
from backend import agent, costs, guardrails, store, instagram

client = TestClient(app)


def project():
    response = client.post("/api/projects", json={"name": "Campaña de prueba"})
    assert response.status_code == 201
    return response.json()


def upload_image():
    data = io.BytesIO()
    Image.new("RGB", (200, 100), "#aabbcc").save(data, "PNG")
    response = client.post("/api/assets", files={"file": ("producto.png", data.getvalue(), "image/png")})
    assert response.status_code == 201
    return response.json()


def test_no_key_blocks_paid_agent_without_creating_a_turn():
    p = project()
    assert client.get("/api/settings").json()["provider"] == "hermes_deepseek"
    assert client.get("/api/deepseek/balance").json()["configured"] is False
    assert client.post(f"/api/projects/{p['id']}/runs", json={"message": "Un post"}).status_code == 503
    assert store.messages(p["id"]) == []


def test_uploaded_image_can_be_cropped_without_changing_original():
    asset = upload_image()
    cropped = client.post(f"/api/assets/{asset['id']}/crop", json={"left": .25, "top": 0, "right": .75, "bottom": 1}).json()
    assert (cropped["width"], cropped["height"]) == (100, 100)
    with Image.open(store.DATA / "assets" / asset["filename"]) as image:
        assert image.size == (200, 100)


def test_hermes_creates_image_and_records_deepseek_cost(monkeypatch):
    p = project()
    store.add_message(p["id"], "user", "Mi marca vende cursos de canto")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr(costs, "rate_period", lambda timestamp=None: "peak")
    async def allow(message, recent): return None
    monkeypatch.setattr(guardrails, "route_request", allow)
    calls = []

    class Response:
        status_code = 200
        def json(self):
            return {"choices": [{"message": {"content": "Imagen lista."}}],
                    "runtime": {"provider": "deepseek", "model": "deepseek-flash"},
                    "usage": {"prompt_tokens": 50000, "completion_tokens": 10000, "cache_read_tokens": 10000}}

    class FakeClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, **kwargs):
            calls.append(kwargs)
            folder = store.DATA / "hermes" / p["id"]
            Image.new("RGB", (100, 100), "#553388").save(folder / "final.png")
            return Response()

    monkeypatch.setattr(agent.httpx, "AsyncClient", FakeClient)
    result = asyncio.run(agent.chat(p["id"], "Creá un post. No hagas video.", run_id="test-run"))
    assert "Archivo generado:" not in result["message"]
    assert len(result["media"]) == 1 and result["media"][0].endswith(".png")
    assert store.messages(p["id"])[-1]["media"] == result["media"]
    assert "Mi marca vende cursos de canto" in calls[0]["json"]["messages"][0]["content"]
    assert "QUARK marketing production" in calls[0]["json"]["messages"][0]["content"]
    assert calls[0]["json"]["provider"] == "deepseek"
    assert calls[0]["headers"]["X-Hermes-Session-Id"] == "quark-" + p["id"]
    assert "tools" not in calls[0]["json"]
    with store.connection() as db:
        row = db.execute("SELECT * FROM agent_usage WHERE run_id='test-run'").fetchone()
    assert row["media_kind"] == "image" and row["media_count"] == 1
    assert row["cost_usd"] == pytest.approx((40000 * .30 + 10000 * .006 + 10000 * 1.20) / 1_000_000)
    assert client.get("/api/costs").json()["images"]["pieces"] >= 1


def test_video_without_mp4_is_failure_but_usage_is_counted(monkeypatch):
    p = project()
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    async def allow(message, recent): return None
    monkeypatch.setattr(guardrails, "route_request", allow)

    class Response:
        status_code = 200
        def json(self):
            return {"choices": [{"message": {"content": "Video terminado."}}],
                    "usage": {"prompt_tokens": 1000, "completion_tokens": 500}}

    class FakeClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, **kwargs): return Response()

    monkeypatch.setattr(agent.httpx, "AsyncClient", FakeClient)
    with pytest.raises(Exception, match="No pude terminar el video"):
        asyncio.run(agent.chat(p["id"], "Creá un video", run_id="failed-video"))
    with store.connection() as db:
        row = db.execute("SELECT status,cost_usd FROM agent_usage WHERE run_id='failed-video'").fetchone()
    assert row["status"] == "failed" and row["cost_usd"] is not None


def test_partial_manim_scene_is_not_delivered_as_final_video(tmp_path, monkeypatch):
    folder = tmp_path / "project"
    rendered = folder / "media" / "videos" / "scene" / "1080p30" / "Story.mp4"
    rendered.parent.mkdir(parents=True)
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=orange:s=64x64:d=0.2",
                    "-c:v", "mpeg4", "-y", str(rendered)], check=True, capture_output=True)
    partial = rendered.parent / "partial_movie_files" / "bad.mp4"
    partial.parent.mkdir()
    partial.write_bytes(b"not a video")
    assert not (folder / "final.mp4").exists()
    assert partial not in agent.rendered_video_candidates(folder)
    assert agent.requested_video_seconds([
        {"role": "user", "content": "Video de 30 segundos más o menos"},
        {"role": "user", "content": "Agregá una locución"},
    ]) == 30
    p = project()
    (folder / "final.mp4").write_bytes(rendered.read_bytes())
    assert agent.import_hermes_media(p["id"], folder, {}, target_seconds=30) == []
    assert agent.import_hermes_media(p["id"], folder, {}, require_audio=True) == []
    monkeypatch.setattr(agent, "video_duration", lambda path: 40)
    assert agent.import_hermes_media(p["id"], folder, {}, target_seconds=30) == []


def test_teacher_can_revise_an_exported_educational_reel(monkeypatch):
    class NoClient:
        def __init__(self, **kwargs):
            raise AssertionError("An existing reel revision should not be classified as homework")
    monkeypatch.setattr(guardrails.httpx, "AsyncClient", NoClient)
    previous = [
        {"role": "user", "content": "Soy profesor de matemáticas. Creá un video de integrales dobles"},
        {"role": "assistant", "content": "Pieza lista", "media": ["/media/exports/reel.mp4"]},
    ]
    assert asyncio.run(guardrails.route_request("Rehacé el video de integrales con locución", previous)) is None


def test_banner_request_does_not_ask_for_the_same_brief_again(monkeypatch):
    class NoClient:
        def __init__(self, **kwargs):
            raise AssertionError("A clear banner brief needs no scope classifier")
    monkeypatch.setattr(guardrails.httpx, "AsyncClient", NoClient)
    assert asyncio.run(guardrails.route_request(
        "Me haces un banner para vender este terreno en Taco Pozo?", [])) is None


def test_inline_image_and_unverified_paths_are_removed_from_public_reply():
    embedded = "![image](data:image/png;base64," + "a" * 100_000 + ")"
    reply = guardrails.public_reply(
        "Listo, te dejo el banner.\n\n" + embedded +
        "\n\nTexto reescrito: Campo en Chaco.\nArchivo generado: /media/exports/old.png", ["/media/exports/new.png"])
    assert reply == "Listo, te dejo el banner.\n\nTexto reescrito: Campo en Chaco."


def test_image_request_imports_only_the_verified_image(tmp_path):
    p = project()
    folder = tmp_path / "project"
    folder.mkdir()
    Image.new("RGB", (32, 32), "#335577").save(folder / "final.png")
    (folder / "final.mp4").write_bytes(b"an unrelated stale video")
    media = agent.import_hermes_media(p["id"], folder, {}, preferred_kind="png")
    assert len(media) == 1 and media[0].endswith(".png")


def test_old_inline_media_is_migrated_out_of_message_text():
    p = project()
    filename = "hermes-" + p["id"] + "-old.png"
    Image.new("RGB", (16, 16), "#335577").save(store.DATA / "exports" / filename)
    original = "Banner listo.\n\n![image](data:image/png;base64," + "a" * 50_000 + ")"
    original += "\nArchivo generado: /media/exports/" + filename
    store.add_message(p["id"], "assistant", original)
    store.init_db()
    migrated = store.messages(p["id"])[-1]
    assert migrated["content"] == "Banner listo."
    assert migrated["media"] == ["/media/exports/" + filename]


def test_identity_is_quark_and_skips_paid_calls(monkeypatch):
    p = project()
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    class NoClient:
        def __init__(self, **kwargs): raise AssertionError("identity must not call a model")
    monkeypatch.setattr(guardrails.httpx, "AsyncClient", NoClient)
    result = asyncio.run(agent.chat(p["id"], "¿Quién sos y sobre qué corrés?"))
    assert result["message"] == guardrails.IDENTITY_REPLY
    assert store.messages(p["id"])[-1]["content"] == guardrails.IDENTITY_REPLY


def test_unrelated_request_is_stopped_before_hermes(monkeypatch):
    p = project()
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    calls = []
    class Response:
        def raise_for_status(self): pass
        def json(self):
            return {"choices": [{"message": {"content": "DECLINE"}}],
                    "usage": {"prompt_tokens": 200, "completion_tokens": 2}}
    class FakeClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, **kwargs):
            calls.append((url, kwargs["json"]["thinking"]))
            return Response()
    monkeypatch.setattr(guardrails.httpx, "AsyncClient", FakeClient)
    result = asyncio.run(agent.chat(p["id"], "Resolvé mi tarea de física"))
    assert result["message"] == guardrails.OUT_OF_SCOPE_REPLY
    assert calls == [("https://api.deepseek.com/v1/chat/completions", {"type": "disabled"})]
    with store.connection() as db:
        assert db.execute("SELECT source FROM aux_usage ORDER BY created_at DESC LIMIT 1").fetchone()["source"] == "scope_guard"


def test_scope_check_failure_does_not_open_hermes(monkeypatch):
    p = project()
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    class OfflineClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, **kwargs):
            raise guardrails.httpx.ConnectError("offline")
    monkeypatch.setattr(guardrails.httpx, "AsyncClient", OfflineClient)
    result = asyncio.run(agent.chat(p["id"], "Necesito hacer algo"))
    assert result["message"] == guardrails.CLARIFY_REPLY


def test_private_or_code_output_is_not_shown_to_customer():
    assert guardrails.public_reply("Soy QUARK y corro sobre Hermes", []) == guardrails.OUT_OF_SCOPE_REPLY
    assert guardrails.public_reply("```python\nprint('hola')\n```", []) == guardrails.OUT_OF_SCOPE_REPLY
    assert guardrails.public_reply("Generé /workspace/hermes/final.mp4", ["/media/exports/pieza.mp4"]) == guardrails.MEDIA_REPLY
    assert guardrails.public_reply("Preparé un reel para tu marca.", []) == "Preparé un reel para tu marca."


def test_instagram_stays_separate_from_paid_agent(monkeypatch):
    settings = {"mode": "review", "rules": [{"id": "price", "name": "Precios", "keywords": ["precio"], "reply": "Consultá el precio vigente."}]}
    assert client.put("/api/instagram/automation", json=settings).status_code == 200
    with store.connection() as db:
        db.execute("INSERT INTO inbox(id,sender,text,timestamp) VALUES (?,?,?,?)", ("faq-test", "u1", "precio", time.time()))
        db.execute("INSERT INTO inbox(id,sender,text,timestamp) VALUES (?,?,?,?)", ("nonfaq-test", "u2", "otro tema", time.time()))
    assert client.post("/api/inbox/faq-test/suggest").json()["source"] == "faq"
    assert client.post("/api/inbox/nonfaq-test/suggest").status_code == 422
    store.set_setting("instagram_automation", {"mode": "off", "rules": []})


def test_signed_instagram_webhook_is_deduplicated(monkeypatch):
    monkeypatch.setenv("INSTAGRAM_APP_SECRET", "test-signing-secret")
    monkeypatch.setenv("INSTAGRAM_ACCOUNT_ID", "account-1")
    body = json.dumps({"entry": [{"id": "account-1", "messaging": [{"sender": {"id": "customer-1"}, "timestamp": int(time.time() * 1000), "message": {"mid": "message-unique", "text": "¿Hay talle M?"}}]}]}).encode()
    assert client.post("/webhooks/instagram", content=body).status_code == 403
    signature = "sha256=" + hmac.new(b"test-signing-secret", body, hashlib.sha256).hexdigest()
    for _ in range(2):
        assert client.post("/webhooks/instagram", content=body, headers={"x-hub-signature-256": signature}).status_code == 200
    assert len([m for m in client.get("/api/inbox").json() if m["id"] == "message-unique"]) == 1
