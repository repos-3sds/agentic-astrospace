"""Write each profile's daily brief before the reader opens Today.

Runs in the notification worker every 15 minutes. For every user with the app
installed (an active push token), and for each of their profiles, it writes
the agent brief for the Vedic day that contains local noon today, and from
22:30 local the next day's as well, so it is ready at midnight, in the
reader's saved tone and experience mode, and stores it
(context/daily_brief_store.py). A day already written is skipped, so after
the first run past 22:30 each later run only picks up what is new: a
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
from datetime import datetime, time as dtime, timedelta
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
# From this local time each run also writes tomorrow's brief, so it is
# stored before midnight: six runs of headroom at 22:30. DAILY_BRIEF_LOOKAHEAD
# ("HH:MM") overrides it on the worker job without a release, e.g. to try
# the night run in the afternoon.
DEFAULT_LOOKAHEAD_FROM = dtime(22, 30)


def lookahead_from() -> dtime:
    raw = os.getenv("DAILY_BRIEF_LOOKAHEAD", "").strip()
    try:
        hh, mm = raw.split(":")[:2]
        return dtime(int(hh), int(mm))
    except (ValueError, TypeError):
        return DEFAULT_LOOKAHEAD_FROM


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
    # The app asks with the phone's own timezone, which it reports on every
    # open with its push token; the newest token is where the phone is now.
    # The morning-brief preference is a send-time setting and only a fallback:
    # preferring it wrote briefs for a place the app never asked about.
    tokens = sorted(cm.list_active_push_tokens(db, user_id),
                    key=lambda t: t.last_seen_at or datetime.min, reverse=True)
    device_tz = next((t.timezone for t in tokens if t.timezone), None) or prefs.get("timezone")
    if not device_tz:
        # An email-only reader: the timezone their app or browser last reported.
        recipient = cm.get_email_recipient(db, user_id)
        device_tz = recipient.timezone if recipient else None
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


def listen_requests(spoken: list[dict]) -> list[str]:
    """The exact texts the Listen sheet sends to /voice/speech for this script.

    The sheet joins every section into one script, splits that with
    naturalChunks, and cleans each piece with prepareForSpeech
    (listen-sheet.component.ts chunks() / speakNaturalFrom). The audio cache
    is keyed by the final text, so rendering per section, or skipping the
    cleanup, would fill the cache with audio the app never asks for.
    """
    script = " ".join(section.get("text", "") for section in spoken if section.get("text", "").strip())
    return [prepare_for_speech(chunk) for chunk in natural_chunks(script)]


def prerender_audio(spoken: list[dict]) -> int:
    """Render the script the way the Listen sheet will request it, so its
    request is a cache hit, in English and in Telugu. Returns the pieces
    rendered.

    Telugu is the sheet's Telugu switch: it translates the same sections
    (voice.translate, stored in the bucket for the API to reuse) and reads
    them with the te-IN voice. A failed translation only skips Telugu.
    """
    from ..voice.translate import Section, TranslationUnavailable, telugu_sections
    from ..voice.tts import natural_speech

    requests = listen_requests(spoken)
    for text in requests:
        natural_speech(text, "en")
    sections = [s for s in spoken if s.get("text", "").strip()]
    try:
        telugu = telugu_sections([Section(s.get("label", ""), s["text"]) for s in sections])
    except TranslationUnavailable:
        log.warning("daily brief Telugu translation unavailable; English audio only")
        return len(requests)
    telugu_requests = listen_requests([{"label": s.label, "text": s.text} for s in telugu])
    for text in telugu_requests:
        natural_speech(text)
    return len(requests) + len(telugu_requests)


def prepare_for_speech(chunk: str) -> str:
    """Mirrors prepareForSpeech in natural-voice.service.ts."""
    import re

    text = re.sub(r"\bTarabala\b", "Tara bala", chunk)
    text = re.sub(r"\bChandrabala\b", "Chandra bala", text)
    text = re.sub(r"\bpanchang\b", "panchangam", text, flags=re.IGNORECASE)
    text = re.sub(r"\bgochara\b", "gocharam", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+—\s+", ", ", text)
    return " ".join(text.split())


# Mirrors naturalChunks in ui/src/app/core/natural-voice.service.ts: the audio
# cache is keyed by the exact text, so the split must match the app's. The
# first piece is a short opening so the voice starts quickly.
NATURAL_CHUNK_MAX_CHARS = 1200
NATURAL_FIRST_CHUNK_MAX_CHARS = 160


def natural_chunks(text: str, max_chars: int = NATURAL_CHUNK_MAX_CHARS) -> list[str]:
    import re

    clean = " ".join(text.split())
    if not clean:
        return []
    opening = min(NATURAL_FIRST_CHUNK_MAX_CHARS, max_chars)
    if len(clean) <= opening:
        return [clean]
    sentences = re.split(r"(?<=[.!?।])\s+", clean)
    first = sentences.pop(0)
    while sentences and len(first) + 1 + len(sentences[0]) <= opening:
        first = f"{first} {sentences.pop(0)}"
    out: list[str] = [first]
    current = ""
    for sentence in sentences:
        if current and len(current) + 1 + len(sentence) > max_chars:
            out.append(current)
            current = ""
        current = f"{current} {sentence}" if current else sentence
    if current:
        out.append(current)
    return out


def _rotated(user_ids: list[str], now: datetime | None) -> list[str]:
    """The readers, starting at a different one each 15-minute run."""
    if not user_ids:
        return user_ids
    moment = now or datetime.now().astimezone()
    start = int(moment.timestamp() // (15 * 60)) % len(user_ids)
    return user_ids[start:] + user_ids[:start]


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
    # Readers with the app, and readers who get the daily reading by email
    # (who may only use the web app and have no push token).
    user_ids = sorted({
        row.user_id for row in db.query(PushToken.user_id).filter(PushToken.revoked_at.is_(None))
    } | {row.user_id for row in cm.email_subscribers(db, "daily_email")})
    # Gather the run's work first, then write today's briefs for everyone
    # before anyone's tomorrow: a reader opening the app now is waiting on
    # today's. Within each, the starting reader rotates every run (I5), so
    # when the budget runs out it is not the same readers, the ones whose ids
    # sort last, who are left to the on-open path night after night.
    today_items: list[tuple] = []
    tomorrow_items: list[tuple] = []
    for user_id in _rotated(user_ids, now):
        settings = _settings(db, user_id)
        timezone, city, nation = _viewer_place(db, user_id, settings)
        zone = _zone(timezone)
        local_now = (now.astimezone(zone) if now else datetime.now(zone))
        # Local noon is always inside the Vedic day that began at that date's
        # sunrise. From lookahead_from() the next day is written too, so it is
        # stored before midnight rather than in the first runs after it.
        days = [local_now.date()]
        if local_now.time() >= lookahead_from():
            days.append(local_now.date() + timedelta(days=1))
        voice = audio_ready and _natural_voice_allowed(db, user_id)
        kundlis = crud.list_kundlis(db, user_id)[:MAX_PROFILES_PER_USER]
        for index, day in enumerate(days):
            as_of = datetime.combine(day, dtime(12, 0), tzinfo=zone)
            bucket = today_items if index == 0 else tomorrow_items
            bucket.extend((kundli, settings, voice, as_of, timezone, city, nation) for kundli in kundlis)

    for kundli, settings, voice, as_of, timezone, city, nation in today_items + tomorrow_items:
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
