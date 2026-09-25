"""Instagram publishing, signed inbox webhooks, and opt-in FAQ automation."""
import asyncio
import hashlib
import hmac
import json
import os
import re
import time
import unicodedata
from typing import Literal
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse
import httpx
from pydantic import BaseModel, Field
from . import store

router = APIRouter()


class FaqRule(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=80)
    keywords: list[str] = Field(min_length=1, max_length=8)
    reply: str = Field(min_length=1, max_length=1000)


class AutomationSettings(BaseModel):
    mode: Literal["off", "review", "auto_faq"] = "off"
    rules: list[FaqRule] = Field(default_factory=list, max_length=20)


def automation_settings():
    return AutomationSettings.model_validate(store.get_setting("instagram_automation", {}))


def normalize(value):
    return " ".join("".join(c for c in unicodedata.normalize("NFKD", value.casefold()) if not unicodedata.combining(c)).split())


def matched_rule(message, settings=None):
    settings = settings or automation_settings()
    value = normalize(message)
    matches = [rule for rule in settings.rules if any(re.search(r"(?<!\w)" + re.escape(normalize(word)) + r"(?!\w)", value) for word in rule.keywords if word.strip())]
    return matches[0] if len(matches) == 1 else None


@router.get("/api/instagram/automation")
def get_automation():
    return {**automation_settings().model_dump(), "connected": configured()}


@router.put("/api/instagram/automation")
def put_automation(body: AutomationSettings):
    if len({rule.id for rule in body.rules}) != len(body.rules):
        raise HTTPException(422, "Cada respuesta frecuente necesita un ID distinto")
    if any(not all(word.strip() for word in rule.keywords) for rule in body.rules):
        raise HTTPException(422, "Las palabras clave no pueden estar vacías")
    store.set_setting("instagram_automation", body.model_dump())
    return get_automation()


class PreviewQuestion(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


@router.post("/api/instagram/automation/preview")
def preview_automation(body: PreviewQuestion):
    rule = matched_rule(body.text)
    return {"matched": bool(rule), "rule": rule.name if rule else None, "reply": rule.reply if rule else None}


def configured():
    return bool(os.getenv("INSTAGRAM_ACCESS_TOKEN") and os.getenv("INSTAGRAM_ACCOUNT_ID"))


async def graph(method, path, **kwargs):
    if not configured():
        raise HTTPException(503, "Configurá INSTAGRAM_ACCESS_TOKEN e INSTAGRAM_ACCOUNT_ID en .env y recreá el contenedor")
    base = f'https://graph.instagram.com/{os.getenv("INSTAGRAM_API_VERSION", "v22.0")}'
    async with httpx.AsyncClient(timeout=40) as client:
        response = await client.request(method, f"{base}/{path}", headers={"Authorization": f'Bearer {os.environ["INSTAGRAM_ACCESS_TOKEN"]}'}, **kwargs)
        if not response.is_success:
            raise HTTPException(502, f"Instagram devolvió HTTP {response.status_code}. Revisá permisos, token y estado de la cuenta.")
        return response.json()


@router.get("/api/instagram/check")
async def check():
    return await graph("GET", os.getenv("INSTAGRAM_ACCOUNT_ID", ""), params={"fields": "id,username"})


@router.get("/api/inbox")
def inbox():
    with store.connection() as db:
        return [dict(r) for r in db.execute("SELECT * FROM inbox ORDER BY timestamp DESC LIMIT 100")]


@router.post("/api/inbox/{message_id}/suggest")
async def suggest(message_id: str):
    with store.connection() as db:
        row = db.execute("SELECT * FROM inbox WHERE id=?", (message_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Mensaje no encontrado")
    if row["suggestion"]:
        return {"suggestion": row["suggestion"], "source": row["suggestion_source"]}
    rule = matched_rule(row["text"])
    if rule:
        content, source = rule.reply, "faq"
    else:
        raise HTTPException(422, "Todavía no hay sugerencias con IA para Instagram. Configurá una respuesta FAQ o escribila manualmente.")
    with store.connection() as db:
        db.execute("UPDATE inbox SET suggestion=?,suggestion_source=? WHERE id=? AND suggestion IS NULL", (content, source, message_id))
    return {"suggestion": content, "source": source}


async def process_pending_inbox():
    settings = automation_settings()
    if settings.mode != "auto_faq" or not configured():
        return
    with store.connection() as db:
        rows = [dict(row) for row in db.execute("SELECT * FROM inbox WHERE replied_at IS NULL AND timestamp>? ORDER BY timestamp", (time.time() - 24 * 3600,))]
    for row in rows:
        rule = matched_rule(row["text"], settings)
        if not rule:
            continue
        with store.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            newer = db.execute("SELECT 1 FROM inbox WHERE sender=? AND timestamp>? LIMIT 1", (row["sender"], row["timestamp"])).fetchone()
            recent = db.execute("SELECT 1 FROM inbox WHERE sender=? AND replied_at IS NOT NULL AND timestamp>? LIMIT 1", (row["sender"], row["timestamp"] - 60)).fetchone()
            if newer or recent:
                continue
            claimed = db.execute("UPDATE inbox SET reply=?,replied_at='pending',suggestion=?,suggestion_source='faq' WHERE id=? AND replied_at IS NULL", (rule.reply, rule.reply, row["id"]))
            if claimed.rowcount != 1:
                continue
        try:
            await graph("POST", f'{os.environ["INSTAGRAM_ACCOUNT_ID"]}/messages', json={"recipient": {"id": row["sender"]}, "message": {"text": rule.reply}})
        except Exception:
            # Network timeouts can mean Meta accepted the message. Never retry blindly.
            with store.connection() as db:
                db.execute("UPDATE inbox SET suggestion_source='send_unconfirmed' WHERE id=?", (row["id"],))
        else:
            with store.connection() as db:
                db.execute("UPDATE inbox SET replied_at=? WHERE id=?", (store.now(), row["id"]))
        return


@router.get("/webhooks/instagram")
def verify(request: Request):
    expected = os.getenv("INSTAGRAM_VERIFY_TOKEN", "")
    if expected and request.query_params.get("hub.mode") == "subscribe" and hmac.compare_digest(request.query_params.get("hub.verify_token", ""), expected):
        return PlainTextResponse(request.query_params.get("hub.challenge", ""))
    raise HTTPException(403, "Verificación inválida")


@router.post("/webhooks/instagram")
async def webhook(request: Request):
    body = await request.body()
    if len(body) > 1_000_000:
        raise HTTPException(413, "Evento demasiado grande")
    secret = os.getenv("INSTAGRAM_APP_SECRET", "")
    signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not secret or not hmac.compare_digest(signature, request.headers.get("x-hub-signature-256", "")):
        raise HTTPException(403, "Firma inválida")
    try:
        event = json.loads(body)
    except ValueError:
        raise HTTPException(400, "Evento inválido")
    with store.connection() as db:
        for entry in event.get("entry", []):
            if str(entry.get("id")) != os.getenv("INSTAGRAM_ACCOUNT_ID"):
                continue
            for item in entry.get("messaging", []):
                message = item.get("message", {})
                if message.get("mid") and message.get("text") and not message.get("is_echo"):
                    db.execute("INSERT OR IGNORE INTO inbox (id,sender,text,timestamp) VALUES (?,?,?,?)", (message["mid"], str(item["sender"]["id"]), message["text"][:10000], item.get("timestamp", 0) / 1000))
    return {"received": True}


class Reply(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


@router.post("/api/inbox/{message_id}/reply")
async def reply(message_id: str, body: Reply):
    with store.connection() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM inbox WHERE id=?", (message_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Mensaje no encontrado")
        if row["replied_at"]:
            raise HTTPException(409, "Este mensaje ya se respondió o su envío está pendiente de verificar")
        latest = db.execute("SELECT MAX(timestamp) FROM inbox WHERE sender=?", (row["sender"],)).fetchone()[0]
        if time.time() - latest > 24 * 3600:
            raise HTTPException(422, "La ventana de respuesta automática de 24 horas está cerrada")
        if not configured():
            raise HTTPException(503, "Configurá Instagram antes de enviar")
        db.execute("UPDATE inbox SET reply=?,replied_at='pending' WHERE id=?", (body.text, message_id))
    # A timeout is ambiguous. Preserve pending instead of risking a duplicate send.
    await graph("POST", f'{os.environ["INSTAGRAM_ACCOUNT_ID"]}/messages', json={"recipient": {"id": row["sender"]}, "message": {"text": body.text}})
    with store.connection() as db:
        db.execute("UPDATE inbox SET replied_at=? WHERE id=?", (store.now(), message_id))
    return {"sent": True}


@router.get("/api/publications")
def publications():
    with store.connection() as db:
        return [dict(r) for r in db.execute("SELECT * FROM publications ORDER BY created_at DESC")]


@router.post("/api/jobs/{job_id}/publish")
async def publish(job_id: str):
    job = store.get_job(job_id)
    base_url = os.getenv("PUBLIC_MEDIA_BASE_URL", "").rstrip("/")
    if not configured() or not base_url.startswith("https://"):
        raise HTTPException(503, "Instagram requiere credenciales y PUBLIC_MEDIA_BASE_URL con HTTPS accesible por Meta")
    if job["kind"] != "render" or job["status"] != "done":
        raise HTTPException(422, "Primero terminá la exportación")
    if job["payload"]["quality"] != "final":
        raise HTTPException(422, "Publicá una exportación en calidad final")
    publication_id = store.uid()
    with store.connection() as db:
        if db.execute("SELECT id FROM publications WHERE job_id=?", (job_id,)).fetchone():
            raise HTTPException(409, "Esta exportación ya tiene un envío registrado. Verificá su estado antes de crear otro.")
        db.execute("INSERT INTO publications (id,job_id,status,created_at) VALUES (?,?,?,?)", (publication_id, job_id, "preparing", store.now()))
    try:
        media_url = base_url + job["result"]["url"]
        # Instagram image publishing accepts JPEG; convert the PNG without changing the render.
        if job["payload"]["kind"] == "png":
            from PIL import Image
            name = job_id + ".jpg"
            with Image.open(store.DATA / "exports" / job["result"]["filename"]) as img:
                img.convert("RGB").save(store.DATA / "exports" / name, "JPEG", quality=95)
            fields = {"image_url": base_url + "/media/exports/" + name}
        else:
            fields = {"media_type": "REELS", "video_url": media_url}
        fields["caption"] = job["payload"]["document"]["caption"]
        account = os.environ["INSTAGRAM_ACCOUNT_ID"]
        container = await graph("POST", f"{account}/media", data=fields)
        container_id = container["id"]
        with store.connection() as db:
            db.execute("UPDATE publications SET container_id=?,status='processing' WHERE id=?", (container_id, publication_id))
        for _ in range(30):
            status = await graph("GET", container_id, params={"fields": "status_code"})
            if status.get("status_code") == "FINISHED":
                break
            if status.get("status_code") in ("ERROR", "EXPIRED"):
                raise HTTPException(422, "Meta rechazó el archivo multimedia")
            await asyncio.sleep(2)
        else:
            raise HTTPException(504, "Meta sigue procesando. El contenedor quedó registrado; no se publicó automáticamente.")
        with store.connection() as db:
            db.execute("UPDATE publications SET status='publishing' WHERE id=?", (publication_id,))
        result = await graph("POST", f"{account}/media_publish", data={"creation_id": container_id})
        with store.connection() as db:
            db.execute("UPDATE publications SET status='published',media_id=? WHERE id=?", (result["id"], publication_id))
        return result
    except Exception as error:
        with store.connection() as db:
            db.execute("UPDATE publications SET status='needs_review',error=? WHERE id=?", (str(getattr(error, "detail", "No se pudo confirmar el envío. Verificá Instagram.")), publication_id))
        if isinstance(error, HTTPException):
            raise
        raise HTTPException(502, "No se pudo confirmar la publicación. Verificá Instagram antes de reintentar.")
