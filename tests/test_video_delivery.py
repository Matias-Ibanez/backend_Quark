"""Delivery accepts a complete narrated ending, while keeping artifact guards."""
import shutil
import subprocess

import pytest

from backend import agent, store


@pytest.mark.parametrize("duration,expected", [(24.333333, True), (25, True), (25.5, False), (5, False), (10, False), (0, False)])
def test_twenty_second_video_has_bounded_flexible_duration(duration, expected):
    assert agent.video_duration_matches(duration, 20) is expected


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="FFmpeg runtime required")
def test_complete_narrated_video_is_delivered_without_retiming(tmp_path):
    store.init_db()
    project = store.create_project("Video de prueba")
    source = tmp_path / "final.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=64x96:r=30:d=24.333333",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=24.333333", "-c:v", "libx264",
                    "-preset", "ultrafast", "-c:a", "aac", "-shortest", "-y", str(source)],
                   capture_output=True, check=True, timeout=30)
    before = {"final.mp4": (source.stat().st_mtime_ns, source.stat().st_size)}
    params = dict(target_seconds=20, require_audio=True, preferred_kind="mp4", dimensions=[64, 96], apply_music=False)
    silent = tmp_path / "silent"
    silent.mkdir()
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(source), "-an", "-c:v", "copy", "-y", str(silent / "final.mp4")],
                   capture_output=True, check=True, timeout=30)
    assert agent.import_hermes_media(project["id"], silent, {}, **params) == []
    assert agent.import_hermes_media(project["id"], tmp_path, before, **params) == []
    assert agent.import_hermes_media(project["id"], tmp_path, {}, **{**params, "dimensions": [1080, 1920]}) == []
    urls = agent.import_hermes_media(project["id"], tmp_path, {}, **params)
    assert len(urls) == 1
    delivered = store.DATA / "exports" / urls[0].rsplit("/", 1)[1]
    assert delivered.read_bytes() == source.read_bytes()
    assert agent.video_has_audio(delivered)
    with store.connection() as db:
        assert db.execute("SELECT COUNT(*) FROM jobs WHERE project_id=? AND status='done'", (project["id"],)).fetchone()[0] == 1
