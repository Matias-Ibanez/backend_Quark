import asyncio
import json
import pytest
from fastapi import HTTPException
from backend import agent, brief, store
from hermes.renderer.svg_artifact import finalize_svg, unexpected_copy


def svg(text):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="320" height="320">{text}</svg>'.encode()


@pytest.mark.parametrize("markup", [
    "<text>Tu pausa, tu café.</text><text>Conocé Pausa</text>",
    "<text>Tu pausa,</text><text>tu café.</text><text>Conocé Pausa</text>",
    "<text><tspan>Tu pausa,</tspan><tspan>tu café.</tspan></text>",
    "<text>PAUSA</text><text>CAFETERÍA</text>",
])
def test_exact_copy_allows_layout_breaks_and_explicit_short_brand_labels(markup):
    assert unexpected_copy(finalize_svg(svg(markup)), '«Tu pausa, tu café.» y «Conocé Pausa»', 'Marca Pausa, una cafetería') == []


@pytest.mark.parametrize("added", ["Café de especialidad", "Desde el barrio", "20% de descuento", "El mejor café"])
def test_exact_copy_rejects_added_claims_and_template_placeholder_text(added):
    assert unexpected_copy(finalize_svg(svg(f'<text>{added}</text>')), 'Tu pausa, tu café.', 'Marca Pausa, una cafetería') == [added]


def test_export_gate_rejects_unrequested_text_even_if_agent_skips_local_policy(monkeypatch):
    store.init_db()
    pid = store.create_project("Texto exacto")["id"]
    brief.maybe_start(pid, "Creá una imagen para la cafetería Pausa", "content", [], quiet=True)
    answers = brief.Answers(subject="Café", copy_mode="exact", copy_text="Tu pausa, tu café.")
    with store.connection() as db:
        db.execute("UPDATE project_briefs SET answers=?,status='generating' WHERE project_id=?", (answers.model_dump_json(), pid))
    class Response:
        status_code = 200
        def json(self): return {"choices":[{"message":{"content":"Listo."}}],"usage":{"input_tokens":100,"output_tokens":20}}
    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, **kwargs):
            folder = store.DATA/'hermes'/pid
            assert (folder/'copy-policy.json').exists()
            policy = json.loads((folder/'copy-policy.json').read_text())
            assert "cafetería Pausa" in policy['provided_text']
            (folder/'final.svg').write_bytes(svg('<text>El mejor café</text>'))
            return Response()
    def no_import(*args, **kwargs): raise AssertionError("Unrequested copy must not be published")
    monkeypatch.setattr(agent.httpx, "AsyncClient", Client)
    monkeypatch.setattr(agent, "import_hermes_media", no_import)
    with pytest.raises(HTTPException, match="exactamente"):
        asyncio.run(agent._hermes_chat(pid, "Creá una imagen", "content", [], {}))
