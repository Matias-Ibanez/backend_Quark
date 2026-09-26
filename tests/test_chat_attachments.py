import asyncio
import io

from PIL import Image
from fastapi.testclient import TestClient
from backend.app import app
from backend import agent, brief, store


def uploaded(client):
    image = io.BytesIO()
    Image.new("RGB", (24, 48), "red").save(image, "PNG")
    response = client.post("/api/assets", files={"file": ("producto.png", image.getvalue(), "image/png")})
    assert response.status_code == 201
    return response.json()


def test_uploaded_image_is_persisted_on_its_turn_and_returned_in_history(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with TestClient(app) as client:
        project = store.create_project("Adjuntos del chat")
        asset = uploaded(client)
        response = client.post(f"/api/projects/{project['id']}/chat", json={"message": "¿Qué puedes hacer?", "assetIds": [asset["id"]]})
        assert response.status_code == 200
        history = client.get(f"/api/projects/{project['id']}/messages").json()
        assert history[0]["role"] == "user" and history[0]["media"] == ["/media/assets/" + asset["filename"]]
        assert client.get(history[0]["media"][0]).status_code == 200
        assert history[1]["media"] == []


def test_intake_keeps_uploaded_image_on_the_request(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test")
    async def plan(pid, message, function, seeded):
        return brief.Intake(answers=brief.Answers.model_validate(seeded), missing=["subject", "aspect"])
    monkeypatch.setattr(brief, "assess", plan)
    with TestClient(app) as client:
        asset = uploaded(client)
        project = store.create_project("Brief con foto")
        asyncio.run(agent.chat(project["id"], "Creame una imagen", asset_ids=[asset["id"]]))
        assert store.messages(project["id"])[0]["media"] == ["/media/assets/" + asset["filename"]]
        store.init_db()
        assert store.messages(project["id"])[0]["media"] == ["/media/assets/" + asset["filename"]]
