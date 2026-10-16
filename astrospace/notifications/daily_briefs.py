"""Write each profile's daily brief before the reader opens Today.

Runs in the notification worker every 15 minutes. For every user with the app
installed (an active push token), and for each of their profiles, it writes
the agent brief for the Vedic day that contains local noon today, in the
reader's saved tone and experience mode, and stores it
(context/daily_brief_store.py). A day already written is skipped, so after
the first run past local midnight each later run only picks up what is new: a
profile added, a place or setting changed, a failure to retry.

For Plus readers it also renders the natural-voice audio of the spoken script
into the durable TTS bucket, so tapping Listen plays at once instead of
waiting 8-13 s for synthesis. Without ASTROSPACE_TTS_BUCKET the audio would
only land in this worker's memory, so it is skipped.

The place, ayanamsha and node type are resolved the way the app asks for
them (vedic.service.ts dailyParams), so the stored brief is the one Today
reads. If they ever differ, Today writes its own once and stores that.
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, time as dtime
from typing import Callable

from sqlalchemy.orm import Session

from ..agents.daily_brief_agent import daily_brief_enabled
from ..context.daily_brief_store import brief_hash, ensure_brief, update_stored
from ..db import crud, crud_mobile as cm
from ..db.models import PushToken
from .morning_brief import CATEGORY as MORNING_CATEGORY, _zone

log = logging.getLogger("astrospace.notifications")

MAX_PROFILES_PER_USER = 6
# One worker run writes at most this many briefs and stops after this many
# seconds; the next run 15 minutes later carries on. Keeps a run well inside
# the job's timeout however many readers there are.
MAX_BRIEFS_PER_RUN = 40
RUN_BUDGET_SECONDS = 360


def _settings(db: Session, user_id: str) -> dict:
    row = crud.get_user_settings(db, user_id)
    tone = getattr(row, "tone", None)
    mode = getattr(row, "experience_mode", None)
    return {
        "tone": tone if tone in ("gentle", "direct") else "gentle",
        "mode": mode if mode in ("guided", "balanced", "practitioner") else "balanced",
        "ayanamsha": getattr(row, "ayanamsha", None) or "lahiri",
        "node_type": getattr(row, "node_type", None) or "mean",
        "timezone_mode": getattr(row, "timezone_mode", None) or "browser",
        "panchanga_place": getattr(row, "panchanga_place", None) or None,
    }


def _viewer_place(db: Session, user_id: str, settings: dict) -> tuple[str | None, str | None, str | None]:
    """(timezone, city, nation) as the app sends them."""
    prefs = cm.get_notification_preferences(db, user_id).get(MORNING_CATEGORY, {})
    tokens = cm.list_active_push_tokens(db, user_id)
    device_tz = prefs.get("timezone") or next((t.timezone for t in tokens if t.timezone), None)
    place = settings["panchanga_place"] or {}
    timezone = device_tz
    if settings["timezone_mode"] == "panchanga_place" and place.get("timezone"):
        timezone = place["timezone"]
    return timezone, place.get("city") or None, place.get("nation") or None


def _natural_voice_allowed(db: Session, user_id: str) -> bool:
    from ..entitlements.resolver import resolve_entitlements

    try:
        return resolve_entitlements(db, user_id).decide("audio.natural_voice").allowed
    except Exception:
        return False


def prerender_audio(spoken: list[dict]) -> int:
    """Render each section the way the Listen sheet will request it, so its
    request is a cache hit. Returns the sections rendered."""
    from ..voice.tts import natural_speech

    rendered = 0
    for section in spoken:
        for chunk in natural_chunks(section.get("text", "")):
            natural_speech(chunk, "en")
        rendered += 1
    return rendered


# Mirrors naturalChunks in ui/src/app/core/natural-voice.service.ts: the audio
# cache is keyed by the exact text, so the split must match the app's.
NATURAL_CHUNK_MAX_CHARS = 1200


def natural_chunks(text: str, max_chars: int = NATURAL_CHUNK_MAX_CHARS) -> list[str]:
    import re

    clean = " ".join(text.split())
    if not clean:
        return []
    if len(clean) <= max_chars:
        return [clean]
    out: list[str] = []
    current = ""
    for sentence in re.split(r"(?<=[.!?।])\s+", clean):
        if current and len(current) + 1 + len(sentence) > max_chars:
            out.append(current)
            current = ""
        current = f"{current} {sentence}" if current else sentence
    if current:
        out.append(current)
    return out


def schedule_daily_briefs(db: Session, now: datetime | None = None,
                          ensure: Callable | None = None,
                          prerender: Callable[[list[dict]], int] = prerender_audio,
                          max_briefs: int = MAX_BRIEFS_PER_RUN,
                          budget_seconds: float = RUN_BUDGET_SECONDS) -> dict:
    """Idempotent: a profile's brief for the day is written once.

    `ensure` and `prerender` are injectable so tests need neither a model
    nor the TTS service.
    """
    from ..api.context_routes import _daily_payload

    ensure = ensure or ensure_brief
    summary = {"written": 0, "already": 0, "failed": 0, "audio": 0, "deferred": 0}
    if not daily_brief_enabled():
        return summary
    started = time.monotonic()
    audio_ready = bool(os.getenv("ASTROSPACE_TTS_BUCKET", "").strip())
    user_ids = sorted({
        row.user_id for row in db.query(PushToken.user_id).filter(PushToken.revoked_at.is_(None))
    })
    for user_id in user_ids:
        settings = _settings(db, user_id)
        timezone, city, nation = _viewer_place(db, user_id, settings)
        zone = _zone(timezone)
        local_now = (now.astimezone(zone) if now else datetime.now(zone))
        # Local noon is always inside the Vedic day that began at today's
        # sunrise, which is the day Today shows from sunrise on.
        as_of = datetime.combine(local_now.date(), dtime(12, 0), tzinfo=zone)
        voice = audio_ready and _natural_voice_allowed(db, user_id)
        for kundli in crud.list_kundlis(db, user_id)[:MAX_PROFILES_PER_USER]:
            if summary["written"] >= max_briefs or time.monotonic() - started > budget_seconds:
                summary["deferred"] += 1
                continue
            try:
                payload = _daily_payload(kundli, settings["ayanamsha"], settings["node_type"],
                                         as_of, timezone, city, nation)
                value, written = ensure(db, kundli, payload, tone=settings["tone"], mode=settings["mode"],
                                        ayanamsha=settings["ayanamsha"], node_type=settings["node_type"],
                                        trigger="scheduled")
            except Exception:
                log.exception("daily brief for kundli %s failed", kundli.id)
                db.rollback()
                summary["failed"] += 1
                continue
            if not value:
                summary["failed"] += 1
                continue
            summary["written" if written else "already"] += 1
            if voice and not value.get("audio_prerendered"):
                try:
                    prerender(value["brief"]["spoken"])
                    key = brief_hash(kundli, payload, settings["tone"], settings["mode"],
                                     settings["ayanamsha"], settings["node_type"])
                    update_stored(db, kundli.id, payload, key, audio_prerendered=True)
                    summary["audio"] += 1
                except Exception:
                    log.exception("daily brief audio for kundli %s failed", kundli.id)
                    db.rollback()
    return summary
