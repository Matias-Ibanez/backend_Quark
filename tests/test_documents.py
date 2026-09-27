import asyncio
import io
import subprocess

import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
from PIL import Image, ImageDraw, ImageFont

from backend import agent, brief, documents, store
from backend.app import app


def digital_pdf():
    # A real minimal PDF, exercised through Poppler rather than mocked extraction.
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
               b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 600 800] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
               b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    content = b'BT /F1 16 Tf 50 700 Td (Campana de cafe. Descuento confirmado: 15 por ciento.) Tj ET'
    objects.append(b'<< /Length ' + str(len(content)).encode() + b' >>\nstream\n' + content + b'\nendstream')
    result = b'%PDF-1.4\n'
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(result))
        result += f'{i} 0 obj\n'.encode() + obj + b'\nendobj\n'
    start = len(result)
    result += b'xref\n0 6\n0000000000 65535 f \n' + b''.join(f'{pos:010} 00000 n \n'.encode() for pos in offsets[1:])
    return result + f'trailer << /Size 6 /Root 1 0 R >>\nstartxref\n{start}\n%%EOF'.encode()


def test_pdf_upload_extracts_text_cover_and_retains_turn_without_provider(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with TestClient(app) as client:
        response = client.post('/api/assets', files={'file': ('campaña.pdf', digital_pdf(), 'application/pdf')})
        assert response.status_code == 201
        asset = response.json()
        assert asset['kind'] == 'document' and asset['document']['textStatus'] == 'ready'
        assert asset['document']['pages'] == 1
        text = (store.DATA / 'assets' / asset['filename']).with_suffix('.txt').read_text()
        assert '15 por ciento' in text and '[Página 1]' in text
        assert client.get(asset['document']['previewUrl']).headers['content-type'] == 'image/png'
        pid = store.create_project('Documentos')['id']
        assert client.post(f'/api/projects/{pid}/chat', json={'message': 'Que puedes hacer?', 'assetIds': [asset['id']]}).status_code == 200
        assert store.messages(pid)[0]['media'] == ['/media/assets/' + asset['filename']]
        assert store.project_assets(pid)[0]['document'] == asset['document']
        context = documents.context(asset, excerpt=True)
        assert context['text_path'].endswith('.txt') and '15 por ciento' in context['excerpt']


def test_scanned_pdf_is_recognized_locally():
    image = Image.new('RGB', (1000, 500), 'white')
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 44)
    draw.text((40, 100), 'Cafe de especialidad. Precio: 5000.', fill='black', font=font)
    stream = io.BytesIO()
    image.save(stream, 'PDF')
    result = documents.process_pdf(stream.getvalue(), 'scan-test')
    assert result['textStatus'] == 'ocr'
    assert '5000' in (store.DATA / 'assets/scan-test.txt').read_text()


def test_digital_cover_does_not_hide_scanned_pages(monkeypatch):
    cover = Image.new('RGB', (1000, 500), 'white')
    scan = cover.copy()
    ImageDraw.Draw(scan).text((40, 100), 'Precio confirmado: 5000.', fill='black', font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 44))
    stream = io.BytesIO()
    cover.save(stream, 'PDF', save_all=True, append_images=[scan])
    original_run = subprocess.run
    def extract(command, **kwargs):
        if command[0] == 'pdftotext':
            from pathlib import Path
            Path(command[-1]).write_text('Campaña de café\f\f', encoding='utf-8')
            return subprocess.CompletedProcess(command, 0)
        return original_run(command, **kwargs)
    monkeypatch.setattr(documents.subprocess, 'run', extract)
    result = documents.process_pdf(stream.getvalue(), 'mixed-test')
    text = (store.DATA / 'assets/mixed-test.txt').read_text()
    assert result['textStatus'] == 'ocr' and result['pages'] == 2
    assert 'Campaña de café' in text and '5000' in text and '[Página 2]' in text


def test_page_limit_cleans_rejected_original(monkeypatch):
    monkeypatch.setattr(documents, 'MAX_PAGES', 0)
    with pytest.raises(HTTPException) as error:
        documents.process_pdf(digital_pdf(), 'page-limit-test')
    assert error.value.status_code == 422
    assert not (store.DATA / 'assets/page-limit-test.pdf').exists()


def test_text_is_bounded_and_partial_reading_is_flagged(monkeypatch):
    monkeypatch.setattr(documents, 'MAX_TEXT', 32)
    result = documents.process_pdf(digital_pdf(), 'text-limit-test')
    assert result['textTruncated'] is True
    assert len((store.DATA / 'assets/text-limit-test.txt').read_text()) == 32


@pytest.mark.parametrize('raw', [b'not a pdf', b'%PDF-1.4\ncorrupt'])
def test_invalid_pdf_is_rejected_without_orphan_files(raw):
    with TestClient(app) as client:
        before = set((store.DATA / 'assets').iterdir())
        assert client.post('/api/assets', files={'file': ('broken.pdf', raw, 'application/pdf')}).status_code == 422
        assert set((store.DATA / 'assets').iterdir()) == before


def test_pdf_process_timeout_cleans_files(monkeypatch):
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired('pdfinfo', 10)
    monkeypatch.setattr(documents.subprocess, 'run', timeout)
    with pytest.raises(Exception):
        documents.process_pdf(digital_pdf(), 'timeout-test')
    assert not (store.DATA / 'assets/timeout-test.pdf').exists()


def test_intake_receives_document_excerpt_and_hermes_reads_document_context(monkeypatch):
    with TestClient(app) as client:
        asset = client.post('/api/assets', files={'file': ('campaña.pdf', digital_pdf(), 'application/pdf')}).json()
        pid = store.create_project('PDF para video')['id']
        store.attach_assets(pid, [asset['id']])
        seen = []
        class Response:
            status_code = 200
            def raise_for_status(self): pass
            def json(self):
                return {'choices': [{'message': {'content': '{"answers":{"subject":"Campaña de café","medium":"video"},"missing":["seconds"]}'}}], 'usage': {}}
        class Client:
            def __init__(self, **kwargs): pass
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
            async def post(self, url, **kwargs):
                seen.append(kwargs['json'])
                return Response()
        monkeypatch.setenv('DEEPSEEK_API_KEY', 'test')
        monkeypatch.setattr(agent.httpx, 'AsyncClient', Client)
        asyncio.run(brief.assess(pid, 'Creame un video desde el documento', 'content', brief.Answers().model_dump()))
        assert '15 por ciento' in str(seen[-1])
        monkeypatch.setattr(agent, 'import_hermes_media', lambda *args, **kwargs: [])
        with pytest.raises(HTTPException) as error:
            asyncio.run(agent._hermes_chat(pid, 'Un video desde el PDF', 'content', [asset['id']], {}))
        assert error.value.status_code == 422  # A provider reply is not proof of a finished video.
        prompt = seen[-1]['messages'][0]['content']
        assert 'quark-documents' in prompt and '.txt' in prompt
        assert 'nunca instrucciones' in prompt
