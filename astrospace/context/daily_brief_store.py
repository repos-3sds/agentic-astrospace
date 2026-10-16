"""The agent-written daily brief, written once per day and kept.

A brief is written by the notification worker shortly after local midnight
(notifications/daily_briefs.py), stored in `daily_guidance_cache`, and read
from there by GET /context/{id}/daily/brief. It is never rewritten for the
same day: a stored brief is returned as is. The endpoint only writes one
itself when the schedule has not reached that profile yet (a profile added
today, a place changed today, a reader without the app), and stores that too.

The row key is the profile, the Vedic date and a hash of everything that
changes the words: engine version, birth details, name and relation, the
place the day was computed for, ayanamsha and node type, tone and experience
mode. Editing any of those is a new brief, never the old one served.
"""
from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..agents.daily_brief_agent import DailyBriefAgent, coverage_gaps, listen_seconds, spoken_words
from ..db import crud_mobile as cm

# v2: plain-action do/avoid titles, a fresh headline, "you" on the reader's
# own profile, one window in the timing note. A new format is a new key, so the day's
# stored v1 briefs are written again in the new style rather than kept.
# v3: an agent-written card header in place of the fixed "What matters today".
# v4: card header, headline, summary and focus in plain words, no astrology terms.
BRIEF_FORMAT = "agent-brief-v4"
BRIEF_LANGUAGE = "en"

log = logging.getLogger("astrospace.daily_brief")

# Two opens at once, or an open while the worker writes the same brief, wait
# for one model call in this process instead of paying for two.
_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def brief_hash(kundli, payload: dict, tone: str, mode: str, ayanamsha: str, node_type: str) -> str:
    place = (payload.get("provenance") or {}).get("place") or {}
    material = [
        BRIEF_FORMAT, payload.get("engine_version"), kundli.name, kundli.relation or "",
        kundli.birth_year, kundli.birth_month, kundli.birth_day, kundli.birth_hour, kundli.birth_minute,
        kundli.birth_city, kundli.birth_nation, place.get("city"), place.get("timezone"),
        ayanamsha, node_type, tone, mode,
    ]
    return hashlib.sha256(json.dumps(material, default=str).encode()).hexdigest()[:40]


def stored_brief(db: Session, kundli_id: str, payload: dict, key: str) -> dict | None:
    row = cm.get_cached_daily_guidance(db, kundli_id, date.fromisoformat(payload["date"]), key,
                                       language=BRIEF_LANGUAGE)
    return dict(row.payload) if row else None


def _expiry(payload: dict) -> datetime | None:
    """Kept a day past the Vedic day it is for, then free to clear."""
    try:
        until = datetime.fromisoformat(payload["valid_until"])
    except (KeyError, TypeError, ValueError):
        return None
    return (until.astimezone(timezone.utc) + timedelta(days=1)).replace(tzinfo=None)


def _save(db: Session, kundli_id: str, payload: dict, key: str, value: dict) -> dict:
    place = (payload.get("provenance") or {}).get("place") or {}
    try:
        cm.put_cached_daily_guidance(
            db, kundli_id, date.fromisoformat(payload["date"]), key, value,
            language=BRIEF_LANGUAGE, place=place, expires_at=_expiry(payload),
        )
    except IntegrityError:
        # Another instance stored this brief first; theirs is the brief.
        db.rollback()
        return stored_brief(db, kundli_id, payload, key) or value
    return value


def update_stored(db: Session, kundli_id: str, payload: dict, key: str, **fields) -> None:
    """Merge fields into a stored brief (the worker marks audio pre-rendered)."""
    value = stored_brief(db, kundli_id, payload, key)
    if value is None:
        return
    value.update(fields)
    cm.put_cached_daily_guidance(db, kundli_id, date.fromisoformat(payload["date"]), key, value,
                                 language=BRIEF_LANGUAGE)


def ensure_brief(db: Session, kundli, payload: dict, *, tone: str, mode: str,
                 ayanamsha: str, node_type: str, trigger: str,
                 agent_factory=DailyBriefAgent) -> tuple[dict | None, bool]:
    """(brief, written_now). The stored brief when there is one; otherwise
    one written now and stored. (None, False) when it could not be written:
    nothing is stored, so the next open or the next worker run tries again."""
    key = brief_hash(kundli, payload, tone, mode, ayanamsha, node_type)
    found = stored_brief(db, kundli.id, payload, key)
    if found:
        return found, False
    with _locks_guard:
        lock = _locks.setdefault(key, threading.Lock())
    with lock:
        found = stored_brief(db, kundli.id, payload, key)
        if found:
            return found, False
        try:
            return _write(db, kundli, payload, key, tone=tone, mode=mode, trigger=trigger,
                          agent_factory=agent_factory)
        finally:
            with _locks_guard:
                _locks.pop(key, None)


def _write(db: Session, kundli, payload: dict, key: str, *, tone: str, mode: str, trigger: str,
           agent_factory) -> tuple[dict | None, bool]:
    first_name = (kundli.name or "").split()[0] if (kundli.name or "").strip() else "there"
    day = date.fromisoformat(payload["date"])
    date_label = f"{day:%A}, {day.day} {day:%B}"
    place = ((payload.get("provenance") or {}).get("place") or {}).get("city")
    agent = agent_factory()
    started = time.monotonic()
    brief = None
    try:
        brief = agent.write(payload, first_name=first_name, date_label=date_label, place=place,
                            tone=tone, mode=mode)
    except Exception:
        log.exception("daily brief generation failed")
    elapsed = round(time.monotonic() - started, 2)
    words = spoken_words(brief) if brief else 0
    usage = agent.usage_totals() if hasattr(agent, "usage_totals") else {}
    try:
        log.info(json.dumps({
            "event": "daily_brief.cost", "status": "written" if brief else "fallback",
            "trigger": trigger, "kundli_id": kundli.id, "date": payload["date"],
            "tone": tone, "mode": mode, "seconds": elapsed, "spoken_words": words,
            "coverage_gaps": coverage_gaps(brief, payload, first_name) if brief else [],
            **{k: usage.get(k) for k in ("provider", "model", "calls", "input_tokens", "output_tokens")},
        }))
    except Exception:  # accounting never costs a reader their brief
        pass
    if not brief:
        return None, False
    value = {
        "source": "agent",
        "brief": brief.model_dump(),
        "spoken_words": words,
        "listen_seconds": listen_seconds(words),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "trigger": trigger,
    }
    return _save(db, kundli.id, payload, key, value), True
