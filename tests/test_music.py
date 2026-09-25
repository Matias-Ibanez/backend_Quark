import io
import os
import subprocess
import tempfile

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="quark-music-test-")

from fastapi.testclient import TestClient
from backend.app import app
from backend import agent, store

client = TestClient(app)


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
