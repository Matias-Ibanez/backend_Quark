import asyncio
import io
import json
import os
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, Field
from . import store, agent, instagram, workspace, costs, music
from .models import CreateProject, EditProject, Crop, Brand, Chat

Image.MAX_IMAGE_PIXELS = 25_000_000
store.init_db()
chat_locks: dict[str, asyncio.Lock] = {}


@asynccontextmanager
async def lifespan(app):
    workspace.recover_runs()
    scheduler = asyncio.create_task(workspace.scheduler())
    yield
    scheduler.cancel()
    for task in workspace.tasks.copy():
        task.cancel()


app = FastAPI(title="QUARK · Asistente de marketing", lifespan=lifespan)


@app.middleware("http")
async def local_origin(request: Request, call_next):
    # The public TLS origin is opt-in; the API port stays bound to loopback.
    if request.url.path.startswith("/api/"):
        host = request.headers.get("host", "").split(":")[0]
        public_origin = os.getenv("PUBLIC_APP_ORIGIN", "").rstrip("/")
        public_host = urlparse(public_origin).hostname if public_origin else None
        if host not in ("localhost", "127.0.0.1", "testserver", "studio", public_host):
            return JSONResponse({"detail": "El estudio solo admite acceso local"}, status_code=403)
        origin = request.headers.get("origin")
        allowed = {f"http://localhost:{os.getenv('WEB_PORT', '8010')}", f"http://127.0.0.1:{os.getenv('WEB_PORT', '8010')}", "http://localhost:3000", "http://127.0.0.1:3000"}
        if public_origin:
            allowed.add(public_origin)
        if origin and urlparse(origin).netloc != request.headers.get("host") and origin not in allowed:
            return JSONResponse({"detail": "Origen no permitido"}, status_code=403)
    response = await call_next(request)
    if request.url.path.startswith("/media/"):
        if request.url.path.startswith("/media/exports/") and request.url.path.endswith(".svg"):
            response.headers["Content-Security-Policy"] = "sandbox; default-src 'none'; img-src data:"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        origin = request.headers.get("origin", "")
        if urlparse(origin).hostname in ("localhost", "127.0.0.1"):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
    return response


@app.get("/api/health")
def health():
    return {"status": "ok", "name": "QUARK", "storage": "sqlite", "mode": "local-single-user"}


@app.get("/api/settings")
def settings():
    return {**agent.configuration(), "hasDeepSeekKey": agent.deepseek_key_configured(), "instagramConfigured": instagram.configured(), "brand": store.get_setting("brand", Brand().model_dump())}


@app.get("/api/costs")
def usage_costs():
    return costs.summary()


@app.get("/api/deepseek/balance")
async def deepseek_balance():
    import httpx
    key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not key:
        return {"configured": False, "available": False, "balances": []}
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.get("https://api.deepseek.com/user/balance", headers={"Authorization": f"Bearer {key}"})
        response.raise_for_status()
        data = response.json()
        return {"configured": True, "available": bool(data.get("is_available")),
                "balances": [{"currency": info["currency"], "total": info["total_balance"]}
                             for info in data.get("balance_infos", []) if info.get("currency") in ("USD", "CNY")]}
    except (httpx.HTTPError, ValueError, KeyError):
        raise HTTPException(502, "No se pudo consultar el saldo de DeepSeek")


@app.get("/api/connections/check")
async def connections_check():
    import httpx
    async with httpx.AsyncClient(timeout=5) as client:
        result = {"hermes": False, "deepseekKey": agent.deepseek_key_configured()}
        try:
            url = os.getenv("HERMES_BASE_URL", "http://hermes:8642/v1").rstrip("/").removesuffix("/v1") + "/health"
            response = await client.get(url, headers={"Authorization": f'Bearer {os.getenv("HERMES_API_KEY", "")}'})
            result["hermes"] = response.is_success
        except httpx.HTTPError:
            pass
        return result


@app.put("/api/brand")
def update_brand(body: Brand):
    store.set_setting("brand", body.model_dump())
    return body


@app.get("/api/projects")
def projects():
    with store.connection() as db:
        rows = db.execute("SELECT id,name,revision,updated_at FROM projects ORDER BY updated_at DESC").fetchall()
    return [dict(row) for row in rows]


@app.post("/api/projects", status_code=201)
def create_project(body: CreateProject):
    return store.create_project(body.name, body.templateId)


@app.get("/api/projects/{project_id}")
def get_project(project_id: str):
    return store.get_project(project_id)


@app.put("/api/projects/{project_id}")
def edit_project(project_id: str, body: EditProject):
    return store.update_project(project_id, body.document.model_dump(), body.revision, body.label, body.name)


@app.get("/api/projects/{project_id}/versions")
def versions(project_id: str):
    store.get_project(project_id)
    with store.connection() as db:
        return [dict(row) for row in db.execute("SELECT id,revision,label,created_at FROM versions WHERE project_id=? ORDER BY revision DESC", (project_id,))]


class Restore(BaseModel):
    revision: int


@app.post("/api/projects/{project_id}/restore/{version_id}")
def restore(project_id: str, version_id: str, body: Restore):
    with store.connection() as db:
        row = db.execute("SELECT document,revision FROM versions WHERE id=? AND project_id=?", (version_id, project_id)).fetchone()
    if not row:
        raise HTTPException(404, "Versión no encontrada")
    return store.update_project(project_id, json.loads(row["document"]), body.revision, f"Restaurada versión {row['revision']}")


@app.get("/api/assets")
def assets():
    return store.list_assets()


@app.post("/api/assets", status_code=201)
def upload(file: UploadFile = File(...)):
    raw = file.file.read(30 * 1024 * 1024 + 1)
    if len(raw) > 30 * 1024 * 1024:
        raise HTTPException(413, "El límite es de 30 MB por archivo")
    asset_id = store.uid()
    extension = Path(file.filename or "").suffix.lower()
    if extension in (".mp3", ".wav", ".m4a", ".ogg"):
        filename = asset_id + extension
        path = store.DATA / "assets" / filename
        path.write_bytes(raw)
        try:
            result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "json", str(path)], capture_output=True, timeout=10)
            probe = json.loads(result.stdout)
            if result.returncode or not any(s.get("codec_type") == "audio" for s in probe.get("streams", [])):
                raise ValueError()
        except Exception:
            path.unlink(missing_ok=True)
            raise HTTPException(422, "El archivo no contiene audio válido")
        return store.add_asset(file.filename or "Audio", filename, "audio", asset_id=asset_id)
    try:
        with Image.open(io.BytesIO(raw)) as img:
            img = ImageOps.exif_transpose(img).convert("RGBA")
            img.thumbnail((4096, 4096))
            filename = asset_id + ".png"
            img.save(store.DATA / "assets" / filename, "PNG")
            width, height = img.size
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, ValueError):
        raise HTTPException(422, "Subí una imagen PNG, JPEG o WebP válida de hasta 25 megapíxeles")
    return store.add_asset(file.filename or "Imagen", filename, "image", width, height, asset_id=asset_id)


@app.post("/api/assets/{asset_id}/crop")
def crop(asset_id: str, body: Crop):
    asset = store.get_asset(asset_id)
    if asset["kind"] != "image" or body.right <= body.left or body.bottom <= body.top:
        raise HTTPException(422, "El rectángulo de recorte no es válido")
    new_id = store.uid()
    with Image.open(store.DATA / "assets" / asset["filename"]) as img:
        box = (round(body.left * img.width), round(body.top * img.height), round(body.right * img.width), round(body.bottom * img.height))
        if box[2] <= box[0] or box[3] <= box[1]:
            raise HTTPException(422, "El recorte debe contener al menos un píxel")
        result = img.crop(box)
        result.save(store.DATA / "assets" / f"{new_id}.png")
        width, height = result.size
    return store.add_asset(asset["name"] + " · recorte", f"{new_id}.png", "image", width, height, asset_id, new_id)


@app.post("/api/assets/{asset_id}/mask")
def apply_mask(asset_id: str, file: UploadFile = File(...)):
    asset = store.get_asset(asset_id)
    if asset["kind"] != "image":
        raise HTTPException(422, "Se requiere una imagen")
    raw = file.file.read(10 * 1024 * 1024 + 1)
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(413, "Máscara demasiado grande")
    try:
        with Image.open(io.BytesIO(raw)) as mask:
            mask = mask.convert("L")
            with Image.open(store.DATA / "assets" / asset["filename"]) as original:
                image = original.convert("RGBA")
                image.putalpha(mask.resize(image.size))
                new_id = store.uid()
                image.save(store.DATA / "assets" / f"{new_id}.png")
                return store.add_asset(asset["name"] + " · máscara", f"{new_id}.png", "image", image.width, image.height, asset_id, new_id)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(422, "Máscara inválida")


@app.get("/api/jobs")
def jobs(project_id: str | None = None):
    with store.connection() as db:
        if project_id:
            rows = db.execute("SELECT id FROM jobs WHERE project_id=? ORDER BY created_at DESC LIMIT 40", (project_id,)).fetchall()
        else:
            rows = db.execute("SELECT id FROM jobs ORDER BY created_at DESC LIMIT 40").fetchall()
    return [store.get_job(row["id"]) for row in rows]


@app.get("/api/jobs/{job_id}")
def job(job_id: str):
    return store.get_job(job_id)


@app.get("/api/projects/{project_id}/messages")
def messages(project_id: str):
    store.get_project(project_id)
    return store.messages(project_id)


@app.post("/api/projects/{project_id}/chat")
async def chat(project_id: str, body: Chat):
    store.get_project(project_id)
    lock = chat_locks.setdefault(project_id, asyncio.Lock())
    if lock.locked():
        raise HTTPException(409, "El agente ya está trabajando en este proyecto")
    async with lock:
        return await agent.chat(project_id, body.message, body.function, body.assetIds)


@app.get("/api/projects/{project_id}/download")
def download_project(project_id: str):
    import zipfile
    project = store.get_project(project_id)
    path = store.DATA / "exports" / f"project-{project_id}-v{project['revision']}.zip"
    ids = {e["assetId"] for scene in project["document"]["scenes"] for e in scene["elements"] if e["assetId"]}
    if project["document"].get("audioAssetId"):
        ids.add(project["document"]["audioAssetId"])
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("project.json", json.dumps(project, ensure_ascii=False, indent=2))
        manifest = {}
        for asset_id in ids:
            asset = store.get_asset(asset_id)
            manifest[asset_id] = asset
            archive.write(store.DATA / "assets" / asset["filename"], "assets/" + asset["filename"])
        archive.writestr("assets.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    return FileResponse(path, filename=path.name)


app.include_router(instagram.router)
app.include_router(workspace.router)
app.include_router(music.router)
app.mount("/media/assets", StaticFiles(directory=store.DATA / "assets"), name="assets")
app.mount("/media/exports", StaticFiles(directory=store.DATA / "exports"), name="exports")
