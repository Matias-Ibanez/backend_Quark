"""Topic-only Spanish shorts through a private MoneyPrinterTurbo API."""
import asyncio
import json
import logging
import os
import re
from decimal import Decimal, InvalidOperation

import httpx
from fastapi import HTTPException

from . import store

log = logging.getLogger("quark.shorts")


async def deepseek_usd_balance():
    """Optional billing observation; a missing response must never block rendering."""
    key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not key:
        return None
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.get("https://api.deepseek.com/user/balance", headers={"Authorization": f"Bearer {key}"})
            response.raise_for_status()
            balances = response.json().get("balance_infos", [])
            entry = next((item for item in balances if item.get("currency") == "USD"), None)
            return Decimal(str(entry["total_balance"])) if entry else None
    except (httpx.HTTPError, KeyError, InvalidOperation, TypeError, ValueError):
        return None


def is_short_request(message, function):
    return function == "shorts" or bool(re.search(r"\b(?:shorts?|reels? autom[aá]ticos?)\b", message, re.I))


def topic(message, function):
    text = message.strip()
    if function != "shorts":
        text = re.sub(r"^(?:(?:hac[eé]|cre[aá]|gener[aá]|arm[aá])(?:me)?\s+)?(?:un\s+)?(?:short|reel)(?:\s+(?:autom[aá]tico|sobre|de))?\s*[:,-]?\s*", "", text, flags=re.I)
    return text.strip() or message.strip()


async def create_short(project_id, message, function, asset_ids, metrics):
    if not os.getenv("PEXELS_API_KEY", "").strip():
        raise HTTPException(503, "Para crear shorts falta configurar la biblioteca de clips del servicio.")
    subject = topic(message, function)
    if len(subject) < 3 or len(subject) > 300:
        raise HTTPException(422, "Escribí un tema de entre 3 y 300 caracteres para el short.")
    store.attach_assets(project_id, asset_ids or [])
    store.add_message(project_id, "user", message)
    store.add_message(project_id, "assistant", "Entendido, estoy preparando tu short.")
    before_balance = await deepseek_usd_balance()
    base = os.getenv("SHORTS_BASE_URL", "http://shorts:8080").rstrip("/")
    headers = {"x-api-key": os.getenv("SHORTS_API_KEY", "")}
    params = {
        "video_subject": subject,
        "video_language": "es",
        "video_aspect": "9:16",
        "video_source": "pexels",
        "voice_name": "es-AR-ElenaNeural",
        "voice_rate": 1.0,
        "paragraph_number": 1,
        "video_count": 1,
        "video_concat_mode": "sequential",
        "match_materials_to_script": True,
        "video_clip_duration": 5,
        "n_threads": 3,
        "bgm_type": "",
        "bgm_volume": 0,
        "subtitle_enabled": True,
        "subtitle_display_mode": "word_by_word",
        "video_script_prompt": "Escribí un guion breve en español rioplatense para un short de marketing de unos 25 a 40 segundos. Abrí con un gancho concreto, desarrollá una idea útil y cerrá con una llamada a la acción natural. No inventes cifras ni promesas. Sin markdown.",
    }
    try:
        async with httpx.AsyncClient(timeout=40) as client:
            response = await client.post(f"{base}/api/v1/videos", headers=headers, json=params)
            response.raise_for_status()
            task_id = response.json()["data"]["task_id"]
            for _ in range(180):
                await asyncio.sleep(5)
                response = await client.get(f"{base}/api/v1/tasks/{task_id}", headers=headers)
                response.raise_for_status()
                task = response.json()["data"]
                if task.get("state") == -1:
                    log.warning("Short failed at stage %s: %s", task.get("failed_stage"), str(task.get("error", ""))[:300])
                    raise HTTPException(422, "No se pudo terminar el short. Probá con otro tema.")
                if task.get("state") == 1:
                    break
            else:
                raise HTTPException(504, "El short tardó demasiado. Probá de nuevo más tarde.")
            # MPT's combined_videos are montage-only clips; videos carry narration.
            videos = task.get("videos") or []
            video_path = next((p for p in videos if isinstance(p, str) and re.fullmatch(r"/tasks/[A-Za-z0-9_./-]+\.mp4", p) and ".." not in p), None)
            if not video_path:
                raise HTTPException(422, "El short terminó sin un video descargable.")
            export = store.DATA / "exports" / f"short-{project_id}-{store.uid()}.mp4"
            try:
                async with client.stream("GET", base + video_path, headers=headers, timeout=180) as stream:
                    stream.raise_for_status()
                    size = 0
                    with export.open("wb") as output:
                        async for chunk in stream.aiter_bytes():
                            size += len(chunk)
                            if size > 200 * 1024 * 1024:
                                raise HTTPException(422, "El short supera el tamaño permitido.")
                            output.write(chunk)
            except Exception:
                export.unlink(missing_ok=True)
                raise
    except HTTPException:
        raise
    except (httpx.HTTPError, KeyError, ValueError, TypeError):
        raise HTTPException(502, "El generador de shorts no está disponible. Probá de nuevo más tarde.")
    from .agent import video_duration, video_has_audio
    duration = video_duration(export)
    if not 5 <= duration <= 180 or not video_has_audio(export):
        export.unlink(missing_ok=True)
        raise HTTPException(422, "El short generado no pasó la validación de video y voz.")
    from . import music
    final, selection = music.mix_export(project_id, export, duration)
    url = "/media/exports/" + final.name
    result = {"url": url, "filename": final.name}
    if selection:
        result["originalUrl"] = "/media/exports/" + export.name
    project = store.get_project(project_id)
    payload = {"document": project["document"], "revision": project["revision"], "kind": "mp4", "quality": "final", "short": True, "topic": subject}
    with store.connection() as db:
        db.execute("INSERT INTO jobs (id,project_id,kind,status,progress,payload,result,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
                   (store.uid(), project_id, "render", "done", 1, json.dumps(payload), json.dumps(result), store.now(), store.now()))
    reply = "Listo, preparé un short vertical sobre " + subject[:100] + "."
    store.add_message(project_id, "assistant", reply, media=[url])
    metrics["provider"] = "deepseek-via-moneyprinterturbo"
    metrics["model"] = "deepseek-v4-flash"
    if before_balance is not None:
        for attempt in range(3):
            after_balance = await deepseek_usd_balance()
            if after_balance is not None and after_balance < before_balance:
                metrics["billed_usd"] = float(before_balance - after_balance)
                break
            if attempt < 2:
                await asyncio.sleep(2)
    metrics["media_kind"] = "video"
    metrics["media_count"] = 1
    return {"message": reply, "media": [url], "project": project}
