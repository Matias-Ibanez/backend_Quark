import io
import asyncio
import json
import os
import subprocess
import tempfile

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="quark-music-test-")

from fastapi.testclient import TestClient
from backend.app import app
from backend import agent, store
from backend import music

client = TestClient(app)


def test_video_music_offer_and_chat_acceptance(monkeypatch):
    project = client.post("/api/projects", json={"name": "Video con música"}).json()
    project_id = project["id"]
    payload = {"document": project["document"], "revision": 1, "kind": "mp4", "quality": "final"}
    with store.connection() as db:
        db.execute("INSERT INTO jobs (id,project_id,kind,status,progress,payload,result,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
                   (store.uid(), project_id, "render", "done", 1, json.dumps(payload), json.dumps({"url": "/media/exports/example.mp4"}), store.now(), store.now()))
    offer = music.offer_after_video(project_id, "Tu video está listo.")
    assert offer.endswith(music.MUSIC_OFFER)
    store.add_message(project_id, "assistant", offer, media=["/media/exports/example.mp4"])
    reply = asyncio.run(agent.chat(project_id, "Sí"))
    assert reply["message"] == music.MUSIC_UPLOAD_PROMPT
    assert len(store.messages(project_id)) == 3
    assert asyncio.run(agent.chat(project_id, "agregar música"))["message"] == music.MUSIC_UPLOAD_PROMPT


def test_music_selection_and_mix_preserve_video_duration_and_audio():
    project = client.post("/api/projects", json={"name": "Música"}).json()
    audio = store.DATA / "test-tone.wav"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                    "sine=frequency=440:duration=4", "-y", str(audio)], check=True)
    uploaded = client.post("/api/assets", files={"file": ("música.wav", audio.read_bytes(), "audio/wav")})
    assert uploaded.status_code == 201
    asset = uploaded.json()
    invalid = client.put(f"/api/projects/{project['id']}/music", json={"assetId": asset["id"], "sourceStart": 1, "sourceEnd": 3})
    assert invalid.status_code == 422  # An unattached asset cannot be selected.
    assert client.post(f"/api/projects/{project['id']}/assets", json={"assetId": asset["id"]}).status_code == 200
    invalid = client.put(f"/api/projects/{project['id']}/music", json={"assetId": asset["id"], "sourceStart": 1, "sourceEnd": 8})
    assert invalid.status_code == 422
    chosen = client.put(f"/api/projects/{project['id']}/music", json={"assetId": asset["id"], "sourceStart": 1,
                         "sourceEnd": 3, "videoStart": 0.5, "volume": 0.25})
    assert chosen.status_code == 200
    assert chosen.json()["assetId"] == asset["id"]
    source = store.DATA / "exports" / "source-test.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                    "color=c=black:s=320x568:r=24:d=3", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-y", str(source)], check=True)
    mixed, selection = __import__("backend.music", fromlist=["mix_export"]).mix_export(project["id"], source, 3)
    assert selection is not None
    assert 2.9 <= agent.video_duration(mixed) <= 3.1
    assert agent.video_has_audio(mixed)
