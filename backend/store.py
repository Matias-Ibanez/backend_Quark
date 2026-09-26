import json
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from fastapi import HTTPException
from .models import Document, initial_document

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get("DATA_DIR", ROOT / "data")).resolve()
for folder in (DATA, DATA / "assets", DATA / "exports", DATA / "jobs"):
    folder.mkdir(parents=True, exist_ok=True)


def now():
    return datetime.now(timezone.utc).isoformat()


def uid():
    return uuid.uuid4().hex


@contextmanager
def connection():
    db = sqlite3.connect(DATA / "studio.sqlite", timeout=20)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    with connection() as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.executescript('''
        CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY, name TEXT NOT NULL, document TEXT NOT NULL, revision INTEGER NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS versions(id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id), revision INTEGER NOT NULL, document TEXT NOT NULL, label TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(project_id, revision));
        CREATE TABLE IF NOT EXISTS assets(id TEXT PRIMARY KEY, name TEXT NOT NULL, filename TEXT NOT NULL, kind TEXT NOT NULL, width INTEGER, height INTEGER, parent_id TEXT, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS templates(id TEXT PRIMARY KEY, name TEXT NOT NULL, document TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id), role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL, media TEXT NOT NULL DEFAULT '[]');
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, project_id TEXT, kind TEXT NOT NULL, status TEXT NOT NULL, progress REAL DEFAULT 0, payload TEXT NOT NULL, result TEXT, error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS inbox(id TEXT PRIMARY KEY, sender TEXT NOT NULL, text TEXT NOT NULL, timestamp REAL NOT NULL, reply TEXT, replied_at TEXT);
        CREATE TABLE IF NOT EXISTS publications(id TEXT PRIMARY KEY, job_id TEXT NOT NULL UNIQUE, status TEXT NOT NULL, container_id TEXT, media_id TEXT, error TEXT, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS project_assets(project_id TEXT NOT NULL REFERENCES projects(id), asset_id TEXT NOT NULL REFERENCES assets(id), PRIMARY KEY(project_id,asset_id));
        CREATE TABLE IF NOT EXISTS project_music(project_id TEXT PRIMARY KEY REFERENCES projects(id), asset_id TEXT NOT NULL REFERENCES assets(id), source_start REAL NOT NULL, source_end REAL NOT NULL, video_start REAL NOT NULL, volume REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id), status TEXT NOT NULL, error TEXT, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS project_briefs(project_id TEXT PRIMARY KEY REFERENCES projects(id), id TEXT NOT NULL, status TEXT NOT NULL, version INTEGER NOT NULL, request TEXT NOT NULL, function TEXT NOT NULL, asset_ids TEXT NOT NULL, answers TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS brief_questions(brief_id TEXT PRIMARY KEY, fields TEXT NOT NULL);
        CREATE UNIQUE INDEX IF NOT EXISTS active_run ON runs(project_id) WHERE status='running';
        CREATE TABLE IF NOT EXISTS calendar(id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id), job_id TEXT REFERENCES jobs(id), title TEXT NOT NULL, scheduled_at TEXT NOT NULL, status TEXT NOT NULL, error TEXT, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS agent_usage(id TEXT PRIMARY KEY, run_id TEXT, project_id TEXT NOT NULL REFERENCES projects(id), provider TEXT NOT NULL, model TEXT NOT NULL, status TEXT NOT NULL, input_tokens INTEGER, output_tokens INTEGER, cache_read_tokens INTEGER, cost_usd REAL, rate_source TEXT, media_kind TEXT, media_count INTEGER NOT NULL DEFAULT 0, duration_seconds REAL NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS aux_usage(id TEXT PRIMARY KEY, source TEXT NOT NULL, provider TEXT NOT NULL, model TEXT NOT NULL, status TEXT NOT NULL, input_tokens INTEGER, output_tokens INTEGER, cache_read_tokens INTEGER, cost_usd REAL, rate_source TEXT, duration_seconds REAL NOT NULL, created_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS agent_usage_project ON agent_usage(project_id, created_at);
        CREATE UNIQUE INDEX IF NOT EXISTS calendar_job ON calendar(job_id) WHERE job_id IS NOT NULL;
        ''')
        columns = {row["name"] for row in db.execute("PRAGMA table_info(inbox)")}
        if "suggestion" not in columns:
            db.execute("ALTER TABLE inbox ADD COLUMN suggestion TEXT")
        if "suggestion_source" not in columns:
            db.execute("ALTER TABLE inbox ADD COLUMN suggestion_source TEXT")
        message_columns = {row["name"] for row in db.execute("PRAGMA table_info(messages)")}
        if "media" not in message_columns:
            db.execute("ALTER TABLE messages ADD COLUMN media TEXT NOT NULL DEFAULT '[]'")
        # Older Hermes replies could contain base64 images or file paths. Migrate
        # once into separate, verified media references before they reach the UI.
        from . import guardrails
        for row in db.execute("SELECT id,content,media FROM messages WHERE role='assistant'").fetchall():
            content = row["content"]
            existing = json.loads(row["media"])
            urls = list(dict.fromkeys([*existing, *re.findall(
                r"/media/exports/[A-Za-z0-9][A-Za-z0-9._-]*\.(?:mp4|png|svg)", content)]))
            urls = [url for url in urls if (DATA / "exports" / url.rsplit("/", 1)[-1]).is_file()]
            cleaned = guardrails.public_reply(content, urls)
            if cleaned != content or urls != existing:
                db.execute("UPDATE messages SET content=?,media=? WHERE id=?", (cleaned, json.dumps(urls), row["id"]))


def get_setting(key, default=None):
    with connection() as db:
        row = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return json.loads(row[0]) if row else default


def set_setting(key, value):
    with connection() as db:
        db.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (key, json.dumps(value)))


def get_project(project_id):
    with connection() as db:
        row = db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Proyecto no encontrado")
    result = dict(row)
    result["document"] = json.loads(result["document"])
    return result


def validate_assets(document):
    for scene in document["scenes"]:
        for element in scene["elements"]:
            if element["assetId"]:
                if get_asset(element["assetId"])["kind"] != "image":
                    raise HTTPException(422, "El elemento debe referenciar una imagen")
    if document.get("audioAssetId") and get_asset(document["audioAssetId"])["kind"] != "audio":
        raise HTTPException(422, "La pista de audio debe referenciar un archivo de audio")


def create_project(name, template_id=None):
    document = initial_document()
    with connection() as db:
        if template_id:
            row = db.execute("SELECT document FROM templates WHERE id=?", (template_id,)).fetchone()
            if not row:
                raise HTTPException(404, "Plantilla no encontrada")
            document = json.loads(row[0])
        project_id = uid()
        timestamp = now()
        encoded = json.dumps(document)
        db.execute("INSERT INTO projects VALUES (?,?,?,?,?)", (project_id, name, encoded, 1, timestamp))
        db.execute("INSERT INTO versions VALUES (?,?,?,?,?,?)", (uid(), project_id, 1, encoded, "Proyecto creado", timestamp))
    return get_project(project_id)


def update_project(project_id, document, revision, label="Edición", name=None):
    document = Document.model_validate(document).model_dump()
    validate_assets(document)
    with connection() as db:
        encoded, timestamp = json.dumps(document), now()
        updated = db.execute("UPDATE projects SET document=?, revision=revision+1, updated_at=?, name=COALESCE(?,name) WHERE id=? AND revision=?", (encoded, timestamp, name, project_id, revision))
        if updated.rowcount != 1:
            raise HTTPException(409, "El proyecto cambió. Recargá la versión actual antes de guardar.")
        db.execute("INSERT INTO versions VALUES (?,?,?,?,?,?)", (uid(), project_id, revision + 1, encoded, label[:120], timestamp))
    return get_project(project_id)


def get_asset(asset_id):
    with connection() as db:
        row = db.execute("SELECT * FROM assets WHERE id=?", (asset_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Recurso no encontrado")
    return dict(row)


def add_asset(name, filename, kind, width=None, height=None, parent=None, asset_id=None):
    asset_id = asset_id or uid()
    with connection() as db:
        db.execute("INSERT INTO assets VALUES (?,?,?,?,?,?,?,?)", (asset_id, name[:180], filename, kind, width, height, parent, now()))
    return get_asset(asset_id)


def list_assets():
    with connection() as db:
        return [dict(row) for row in db.execute("SELECT * FROM assets ORDER BY created_at DESC")]


def attach_assets(project_id, asset_ids):
    get_project(project_id)
    for asset_id in asset_ids:
        get_asset(asset_id)
    with connection() as db:
        db.executemany("INSERT OR IGNORE INTO project_assets VALUES (?,?)", [(project_id, i) for i in asset_ids])


def project_assets(project_id):
    document = get_project(project_id)["document"]
    ids = {e["assetId"] for s in document["scenes"] for e in s["elements"] if e.get("assetId")}
    if document.get("audioAssetId"):
        ids.add(document["audioAssetId"])
    with connection() as db:
        ids.update(r[0] for r in db.execute("SELECT asset_id FROM project_assets WHERE project_id=?", (project_id,)))
    return [get_asset(i) for i in sorted(ids)]


def add_message(project_id, role, content, media=None):
    with connection() as db:
        db.execute("INSERT INTO messages (id,project_id,role,content,created_at,media) VALUES (?,?,?,?,?,?)",
                   (uid(), project_id, role, content, now(), json.dumps(media or [])))


def messages(project_id):
    with connection() as db:
        rows = [dict(row) for row in db.execute("SELECT * FROM messages WHERE project_id=? ORDER BY created_at", (project_id,))]
    for row in rows:
        row["media"] = json.loads(row["media"])
    return rows


def get_job(job_id):
    with connection() as db:
        row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Trabajo no encontrado")
    result = dict(row)
    result["payload"] = json.loads(result["payload"])
    result["result"] = json.loads(result["result"]) if result["result"] else None
    return result
