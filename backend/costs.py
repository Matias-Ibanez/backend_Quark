"""Persist provider usage and conservative USD estimates without recording prompts or keys."""
import json
import logging
import sys
from datetime import datetime, timezone

from . import store

log = logging.getLogger("quark.usage")
log.setLevel(logging.INFO)
log.propagate = False
if not log.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(handler)

# DeepSeek public API rates per million tokens, checked 2026-09-24.
# Keep the exact rate used with each record so later price changes do not rewrite history.
RATES = {
    "deepseek-flash": {"peak": (0.30, 1.20, 0.006), "off_peak": (0.15, 0.60, 0.003)},
}
RATE_SOURCE = "https://api-docs.deepseek.com/quick_start/pricing/ (2026-09-24)"


def rate_period(timestamp=None):
    moment = timestamp or datetime.now(timezone.utc)
    hour = moment.astimezone(timezone.utc).hour
    return "peak" if moment.weekday() < 5 and (1 <= hour < 4 or 6 <= hour < 10) else "off_peak"


def token_usage(raw):
    if not isinstance(raw, dict):
        return None
    try:
        incoming = int(raw.get("input_tokens", raw.get("prompt_tokens", 0)) or 0)
        outgoing = int(raw.get("output_tokens", raw.get("completion_tokens", 0)) or 0)
        cached = int(raw.get("cache_read_tokens", raw.get("prompt_cache_hit_tokens", 0)) or 0)
    except (ValueError, TypeError):
        return None
    if incoming < 0 or outgoing < 0 or cached < 0 or incoming + outgoing == 0:
        return None
    return incoming, outgoing, min(cached, incoming)


def estimate(provider, model, tokens):
    if not tokens or provider != "deepseek" or model not in RATES:
        return None, None
    input_rate, output_rate, cache_rate = RATES[model][rate_period()]
    incoming, outgoing, cached = tokens
    return round(((incoming - cached) * input_rate + cached * cache_rate + outgoing * output_rate) / 1_000_000, 8), RATE_SOURCE


def record(*, run_id, project_id, provider, model, status, usage, media_kind, media_count, duration_seconds):
    tokens = token_usage(usage)
    cost, rate_source = estimate(provider, model, tokens)
    with store.connection() as db:
        db.execute(
            "INSERT INTO agent_usage VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (store.uid(), run_id, project_id, provider, model, status,
             tokens[0] if tokens else None, tokens[1] if tokens else None,
             tokens[2] if tokens else None, cost, rate_source,
             media_kind, media_count, round(duration_seconds, 3), store.now()),
        )
    log.info(json.dumps({"event": "agent_usage", "run_id": run_id, "project_id": project_id,
                         "provider": provider, "model": model, "status": status,
                         "input_tokens": tokens[0] if tokens else None,
                         "output_tokens": tokens[1] if tokens else None,
                         "cache_read_tokens": tokens[2] if tokens else None,
                         "estimated_usd": cost, "media_kind": media_kind,
                         "media_count": media_count, "duration_seconds": round(duration_seconds, 3)}))


def record_aux(*, source, provider, model, status, usage, duration_seconds):
    tokens = token_usage(usage)
    cost, rate_source = estimate(provider, model, tokens)
    with store.connection() as db:
        db.execute("INSERT INTO aux_usage VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                   (store.uid(), source, provider, model, status,
                    tokens[0] if tokens else None, tokens[1] if tokens else None,
                    tokens[2] if tokens else None, cost, rate_source,
                    round(duration_seconds, 3), store.now()))
    log.info(json.dumps({"event": "aux_usage", "source": source, "provider": provider,
                         "model": model, "status": status,
                         "input_tokens": tokens[0] if tokens else None,
                         "output_tokens": tokens[1] if tokens else None,
                         "cache_read_tokens": tokens[2] if tokens else None,
                         "estimated_usd": cost, "duration_seconds": round(duration_seconds, 3)}))


def summary():
    with store.connection() as db:
        rows = [dict(row) for row in db.execute("SELECT * FROM agent_usage ORDER BY created_at DESC")]
        aux_rows = [dict(row) for row in db.execute("SELECT * FROM aux_usage ORDER BY created_at DESC")]
    priced = [r for r in rows if r["cost_usd"] is not None]
    priced_aux = [r for r in aux_rows if r["cost_usd"] is not None]
    unpriced = len(rows) + len(aux_rows) - len(priced) - len(priced_aux)
    total = sum(r["cost_usd"] for r in priced) + sum(r["cost_usd"] for r in priced_aux)
    image_rows = [r for r in priced if r["media_kind"] == "image" and r["media_count"]]
    video_rows = [r for r in priced if r["media_kind"] == "video" and r["media_count"]]
    def group(items):
        count = sum(r["media_count"] for r in items)
        return {"pieces": count, "directCostUsd": round(sum(r["cost_usd"] for r in items), 6),
                "averageDirectUsd": round(sum(r["cost_usd"] for r in items) / count, 6) if count else None}
    images, videos = group(image_rows), group(video_rows)
    pieces = images["pieces"] + videos["pieces"]
    return {"estimatedSpendUsd": round(total, 6), "otherSpendUsd": round(sum(r["cost_usd"] for r in priced_aux), 6), "unpricedRuns": unpriced,
            "allInAverageUsd": round(total / pieces, 6) if pieces else None,
            "images": images, "videos": videos,
            "runs": [{"runId": r["run_id"], "projectId": r["project_id"], "model": r["model"],
                      "status": r["status"], "inputTokens": r["input_tokens"],
                      "outputTokens": r["output_tokens"], "cacheReadTokens": r["cache_read_tokens"],
                      "estimatedUsd": r["cost_usd"], "mediaKind": r["media_kind"],
                      "mediaCount": r["media_count"], "durationSeconds": r["duration_seconds"],
                      "createdAt": r["created_at"]} for r in rows[:30]],
            "rateSource": RATE_SOURCE}
