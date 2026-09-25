import asyncio
import subprocess
from decimal import Decimal

import httpx
import pytest
from fastapi import HTTPException

from backend import agent, shorts, store


def test_topic_only_short_uses_mpt_and_imports_single_valid_mp4(monkeypatch, tmp_path):
    project = store.create_project("Short sobre café")
    source = tmp_path / "result.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                    "color=c=black:s=320x568:r=24:d=6", "-f", "lavfi", "-i",
                    "sine=frequency=440:duration=6", "-c:v", "libx264", "-c:a", "aac",
                    "-shortest", "-y", str(source)], check=True)
    submitted = []

    def respond(request):
        if request.method == "POST" and request.url.path == "/api/v1/videos":
            submitted.append(__import__("json").loads(request.content))
            return httpx.Response(200, json={"data": {"task_id": "test-task"}})
        if request.url.path == "/api/v1/tasks/test-task":
            return httpx.Response(200, json={"data": {"state": 1, "videos": ["/tasks/test-task/result.mp4"], "combined_videos": ["/tasks/test-task/silent.mp4"]}})
        if request.url.path == "/tasks/test-task/result.mp4":
            return httpx.Response(200, content=source.read_bytes())
        return httpx.Response(404)

    real_client = httpx.AsyncClient
    monkeypatch.setattr(shorts.httpx, "AsyncClient", lambda **kwargs: real_client(transport=httpx.MockTransport(respond), **kwargs))
    async def no_wait(seconds): return None
    balances = iter([Decimal("2.000"), Decimal("1.997")])
    async def test_balance(): return next(balances)
    monkeypatch.setattr(shorts.asyncio, "sleep", no_wait)
    monkeypatch.setattr(shorts, "deepseek_usd_balance", test_balance)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-only")
    monkeypatch.setenv("PEXELS_API_KEY", "test-only")
    result = asyncio.run(agent.chat(project["id"], "Café de especialidad", function="shorts"))
    assert submitted[0]["video_subject"] == "Café de especialidad"
    assert submitted[0]["video_aspect"] == "9:16"
    assert submitted[0]["video_count"] == 1
    assert submitted[0]["n_threads"] == 4
    assert len(result["media"]) == 1
    assert (store.DATA / "exports" / result["media"][0].rsplit("/", 1)[-1]).is_file()
    assert len([m for m in store.messages(project["id"]) if m["media"]]) == 1
    with store.connection() as db:
        usage = db.execute("SELECT cost_usd,media_count FROM agent_usage WHERE project_id=? ORDER BY created_at DESC LIMIT 1", (project["id"],)).fetchone()
    assert usage["cost_usd"] == pytest.approx(0.003)
    assert usage["media_count"] == 1


def test_short_without_stock_key_fails_before_charging_or_creating_turn(monkeypatch):
    project = store.create_project("Sin biblioteca")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-only")
    monkeypatch.delenv("PEXELS_API_KEY", raising=False)
    with pytest.raises(HTTPException) as error:
        asyncio.run(agent.chat(project["id"], "Café", function="shorts"))
    assert error.value.status_code == 503
    assert store.messages(project["id"]) == []
