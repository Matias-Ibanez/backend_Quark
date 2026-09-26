"""Persistent chat turns and a calendar of immutable, human-approved exports."""
import asyncio
import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Literal
from fastapi import APIRouter, HTTPException
from pydantic import Field, AwareDatetime
from . import store, agent, instagram
from .models import Chat, Strict

router = APIRouter()
tasks: set[asyncio.Task] = set()


def recover_runs():
    with store.connection() as db:
        db.execute("UPDATE project_briefs SET status='failed' WHERE status IN ('generating','confirmed')")
        db.execute("UPDATE runs SET status='failed',error='El servicio se reinició. Los cambios guardados se conservan.' WHERE status='running'")
        db.execute("UPDATE calendar SET status='needs_review',error='Envío interrumpido: verificá Instagram antes de reintentar.' WHERE status='publishing'")


async def execute_run(run_id, project_id, body):
    try:
        await agent.chat(project_id, body.message, body.function, body.assetIds, run_id=run_id, brief_id=body.briefId)
        status, error = "done", None
    except asyncio.CancelledError:
        status, error = "failed", "El servicio se detuvo. Los cambios guardados se conservan."
    except Exception as exc:
        status, error = "failed", str(getattr(exc, "detail", "El agente no pudo completar el pedido. Revisá la conexión."))
    with store.connection() as db:
        db.execute("UPDATE runs SET status=?,error=? WHERE id=?", (status, error, run_id))


@router.post("/api/projects/{project_id}/runs", status_code=202)
async def start_run(project_id: str, body: Chat):
    store.attach_assets(project_id, body.assetIds)
    if not agent.deepseek_key_configured():
        raise HTTPException(503, "El agente no está disponible en este momento. Contactá a soporte.")
    run_id = store.uid()
    try:
        with store.connection() as db:
            db.execute("INSERT INTO runs VALUES (?,?, 'running',NULL,?)", (run_id, project_id, store.now()))
    except sqlite3.IntegrityError:
        raise HTTPException(409, "QUARK ya está trabajando en esta conversación")
    task = asyncio.create_task(execute_run(run_id, project_id, body))
    tasks.add(task)
    task.add_done_callback(tasks.discard)
    return {"id": run_id, "status": "running"}


@router.get("/api/projects/{project_id}/runs")
def runs(project_id: str):
    store.get_project(project_id)
    with store.connection() as db:
        return [dict(r) for r in db.execute("SELECT * FROM runs WHERE project_id=? ORDER BY created_at DESC LIMIT 10", (project_id,))]


@router.get("/api/projects/{project_id}/assets")
def assets(project_id: str):
    return store.project_assets(project_id)


class AttachAsset(Strict):
    assetId: str


@router.post("/api/projects/{project_id}/assets")
def attach_asset(project_id: str, body: AttachAsset):
    store.attach_assets(project_id, [body.assetId])
    return store.get_asset(body.assetId)


class CalendarDraft(Strict):
    project_id: str
    job_id: str | None = None
    title: str = Field(min_length=1, max_length=160)
    scheduled_at: AwareDatetime


def create_draft(body: CalendarDraft):
    store.get_project(body.project_id)
    if body.job_id:
        job = store.get_job(body.job_id)
        if job["project_id"] != body.project_id or job["kind"] != "render" or job["status"] != "done":
            raise HTTPException(422, "La pieza debe pertenecer a esta conversación y estar terminada")
    event_id = store.uid()
    try:
        with store.connection() as db:
            db.execute("INSERT INTO calendar VALUES (?,?,?,?,?,'draft',NULL,?)", (event_id, body.project_id, body.job_id, body.title, body.scheduled_at.astimezone(timezone.utc).isoformat(), store.now()))
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Esta pieza ya está en el calendario")
    return get_event(event_id)


def get_event(event_id):
    with store.connection() as db:
        row = db.execute("SELECT * FROM calendar WHERE id=?", (event_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Evento no encontrado")
    return dict(row)


@router.get("/api/calendar")
def calendar():
    with store.connection() as db:
        return [dict(r) for r in db.execute("SELECT * FROM calendar ORDER BY scheduled_at")]


@router.post("/api/calendar", status_code=201)
def draft(body: CalendarDraft):
    return create_draft(body)


class CalendarChange(Strict):
    action: Literal["reschedule", "approve", "schedule", "cancel"]
    scheduled_at: AwareDatetime | None = None


@router.patch("/api/calendar/{event_id}")
def change_event(event_id: str, body: CalendarChange):
    with store.connection() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM calendar WHERE id=?", (event_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Evento no encontrado")
        event = dict(row)
        if event["status"] in ("publishing", "published", "needs_review", "cancelled"):
            raise HTTPException(409, "Este evento ya no puede modificarse")
        state, date = event["status"], event["scheduled_at"]
        if body.action == "reschedule":
            if not body.scheduled_at:
                raise HTTPException(422, "Indicá una fecha con zona horaria")
            date = body.scheduled_at.astimezone(timezone.utc).isoformat()
            state = "draft"  # A changed schedule requires a new explicit approval.
        elif body.action == "cancel":
            state = "cancelled"
        else:
            if not event["job_id"]:
                raise HTTPException(422, "Primero agregá una exportación final al calendario desde la galería")
            job = store.get_job(event["job_id"])
            if job["status"] != "done" or job["payload"].get("quality") != "final":
                raise HTTPException(422, "Se necesita una exportación terminada en calidad final")
            if body.action == "approve":
                if state != "draft":
                    raise HTTPException(409, "Solo se puede aprobar un borrador")
                state = "approved"
            else:
                if state != "approved":
                    raise HTTPException(409, "Aprobá la pieza antes de programar su publicación")
                if datetime.fromisoformat(date) <= datetime.now(timezone.utc):
                    raise HTTPException(422, "Elegí una fecha futura")
                if not instagram.configured() or not os.getenv("PUBLIC_MEDIA_BASE_URL", "").startswith("https://"):
                    raise HTTPException(503, "Conectá Instagram y configurá la URL pública HTTPS antes de programar")
                state = "scheduled"
        db.execute("UPDATE calendar SET status=?,scheduled_at=? WHERE id=?", (state, date, event_id))
    return get_event(event_id)


async def publish_due():
    with store.connection() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM calendar WHERE status='scheduled' AND scheduled_at<=? ORDER BY scheduled_at LIMIT 1", (store.now(),)).fetchone()
        if not row:
            return
        db.execute("UPDATE calendar SET status='publishing' WHERE id=?", (row["id"],))
    try:
        await instagram.publish(row["job_id"])
        state, error = "published", None
    except Exception as exc:
        state, error = "needs_review", str(getattr(exc, "detail", "No se pudo confirmar la publicación"))
    with store.connection() as db:
        db.execute("UPDATE calendar SET status=?,error=? WHERE id=?", (state, error, row["id"]))


async def scheduler():
    while True:
        await publish_due()
        await instagram.process_pending_inbox()
        await asyncio.sleep(15)
