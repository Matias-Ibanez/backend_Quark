"""Persist licensed audio selections and mix an exact excerpt into finished MP4s."""
import json
import logging
import subprocess

from fastapi import APIRouter, HTTPException
from pydantic import Field, model_validator

from . import store
from .models import Strict

router = APIRouter()
log = logging.getLogger("quark.music")


class MusicSelection(Strict):
    assetId: str
    sourceStart: float = Field(ge=0)
    sourceEnd: float = Field(gt=0)
    videoStart: float = Field(default=0, ge=0, le=180)
    volume: float = Field(default=0.2, ge=0, le=1)

    @model_validator(mode="after")
    def valid_range(self):
        if self.sourceEnd <= self.sourceStart or self.sourceEnd - self.sourceStart > 180:
            raise ValueError("Elegí un tramo de hasta 180 segundos")
        return self


def audio_duration(path):
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                            capture_output=True, text=True, timeout=15)
    try:
        return float(result.stdout.strip()) if result.returncode == 0 else 0
    except ValueError:
        return 0


def get_selection(project_id):
    store.get_project(project_id)
    with store.connection() as db:
        row = db.execute("SELECT * FROM project_music WHERE project_id=?", (project_id,)).fetchone()
    if not row:
        return None
    asset = store.get_asset(row["asset_id"])
    return {"assetId": row["asset_id"], "sourceStart": row["source_start"],
            "sourceEnd": row["source_end"], "videoStart": row["video_start"],
            "volume": row["volume"], "asset": asset}


@router.get("/api/projects/{project_id}/music")
def selected_music(project_id: str):
    return get_selection(project_id)


@router.put("/api/projects/{project_id}/music")
def select_music(project_id: str, body: MusicSelection):
    store.get_project(project_id)
    asset = store.get_asset(body.assetId)
    if asset["kind"] != "audio" or body.assetId not in {a["id"] for a in store.project_assets(project_id)}:
        raise HTTPException(422, "Adjuntá primero un archivo de audio a esta conversación")
    duration = audio_duration(store.DATA / "assets" / asset["filename"])
    if not duration or body.sourceEnd > duration + 0.05:
        raise HTTPException(422, "El tramo supera la duración del archivo")
    with store.connection() as db:
        db.execute("INSERT INTO project_music VALUES (?,?,?,?,?,?) ON CONFLICT(project_id) DO UPDATE SET asset_id=excluded.asset_id,source_start=excluded.source_start,source_end=excluded.source_end,video_start=excluded.video_start,volume=excluded.volume",
                   (project_id, body.assetId, body.sourceStart, body.sourceEnd, body.videoStart, body.volume))
    return get_selection(project_id)


@router.delete("/api/projects/{project_id}/music", status_code=204)
def clear_music(project_id: str):
    store.get_project(project_id)
    with store.connection() as db:
        db.execute("DELETE FROM project_music WHERE project_id=?", (project_id,))


def mix(source, destination, selection, duration):
    """Keep the original picture and voice; music plays only over the chosen window."""
    asset = store.get_asset(selection["assetId"])
    audio = store.DATA / "assets" / asset["filename"]
    span = min(selection["sourceEnd"] - selection["sourceStart"], duration - selection["videoStart"])
    if span <= 0:
        raise HTTPException(422, "El tramo de música empieza después de que termina el video")
    delay = round(selection["videoStart"] * 1000)
    music_filter = (f"[1:a]atrim=start={selection['sourceStart']}:duration={span},"
                    f"asetpts=PTS-STARTPTS,volume={selection['volume']},adelay={delay}:all=1[bg]")
    from .agent import video_has_audio
    if video_has_audio(source):
        filters = music_filter + ";[0:a][bg]amix=inputs=2:duration=longest:dropout_transition=0[a]"
    else:
        filters = music_filter + ";[bg]apad[a]"
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source), "-i", str(audio),
               "-filter_complex", filters, "-map", "0:v:0", "-map", "[a]", "-c:v", "copy", "-c:a", "aac",
               "-t", str(duration), "-movflags", "+faststart", str(destination)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=240)
    if result.returncode or not destination.is_file() or not destination.stat().st_size:
        destination.unlink(missing_ok=True)
        log.error("FFmpeg music mix failed: %s", result.stderr[-1000:])
        raise HTTPException(422, "No se pudo mezclar la música con el video")


def mix_export(project_id, source, duration):
    selection = get_selection(project_id)
    if not selection:
        return source, None
    name = f"music-{project_id}-{store.uid()}.mp4"
    destination = store.DATA / "exports" / name
    mix(source, destination, selection, duration)
    return destination, selection


class ApplyMusic(Strict):
    jobId: str | None = None


@router.post("/api/projects/{project_id}/music/apply")
def apply_music(project_id: str, body: ApplyMusic):
    selection = get_selection(project_id)
    if not selection:
        raise HTTPException(422, "Elegí primero una canción y su tramo")
    with store.connection() as db:
        rows = db.execute("SELECT id FROM jobs WHERE id=? AND project_id=? AND status='done' AND kind='render'", (body.jobId, project_id)).fetchall() if body.jobId else db.execute("SELECT id FROM jobs WHERE project_id=? AND status='done' AND kind='render' ORDER BY created_at DESC LIMIT 40", (project_id,)).fetchall()
    row = next((candidate for candidate in rows if (store.get_job(candidate["id"])["result"] or {}).get("url", "").endswith(".mp4")), None)
    if not row:
        raise HTTPException(404, "No hay un video terminado en esta conversación")
    job = store.get_job(row["id"])
    original_url = job["result"].get("originalUrl") or job["result"].get("url", "")
    if not original_url.startswith("/media/exports/") or not original_url.endswith(".mp4"):
        raise HTTPException(422, "La pieza elegida no es un video")
    source = store.DATA / "exports" / original_url.rsplit("/", 1)[-1]
    if not source.is_file():
        raise HTTPException(404, "No se encontró el video original")
    from .agent import video_duration
    duration = video_duration(source)
    if duration < 1:
        raise HTTPException(422, "El video no es válido")
    destination, _ = mix_export(project_id, source, duration)
    url = "/media/exports/" + destination.name
    result = {"url": url, "filename": destination.name, "originalUrl": original_url}
    with store.connection() as db:
        db.execute("INSERT INTO jobs (id,project_id,kind,status,progress,payload,result,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
                   (store.uid(), project_id, "render", "done", 1, json.dumps({**job["payload"], "music": {k: v for k, v in selection.items() if k != "asset"}}), json.dumps(result), store.now(), store.now()))
    store.add_message(project_id, "assistant", "Listo, agregué el tramo de música al video.", media=[url])
    return result
