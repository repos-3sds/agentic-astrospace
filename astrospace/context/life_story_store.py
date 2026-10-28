"""Your Story in the agent's words, written once per profile and kept.

GET /vedic/{id}/story reads it from `life_stories`, and writes it the first
time the screen is opened. The row key hashes everything that changes the
words: the prompt version, the profile's name and birth details, ayanamsha and
node type, and the running periods (mahadasha and antardasha), because the
current chapter names them. A new sub-period is a new story, about once a
year or two; nothing else expires it.

When the table is missing (the SQL not yet applied), the agent is off or the
model fails, the caller gets None and serves the code backup
(story_classics.fallback_story). Nothing is written without a row to keep it
in, so a missing table can never turn into a model call on every open.
"""
from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from ..agents.story_agent import STORY_VERSION, LifeStoryAgent, story_gaps, to_payload
from ..db.models import LifeStory

log = logging.getLogger("astrospace.life_story")

# New stories one account may have written in a day. Practitioner has 10
# profiles, so a real reader stays below this; it caps what a script editing
# birth details in a loop can spend.
DAILY_WRITE_CEILING = 12

_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def story_key(kundli, signals: dict, ayanamsha: str, node_type: str) -> str:
    running = {level: (row or {}).get("lord") for level, row in (signals.get("running") or {}).items()}
    material = [STORY_VERSION, kundli.name, kundli.birth_year, kundli.birth_month, kundli.birth_day,
                kundli.birth_hour, kundli.birth_minute, kundli.birth_city, kundli.birth_nation,
                ayanamsha, node_type, running]
    return hashlib.sha256(json.dumps(material, default=str).encode()).hexdigest()[:40]


def _stored(db: Session, kundli_id: str, key: str) -> dict | None:
    row = db.query(LifeStory).filter(LifeStory.kundli_id == kundli_id, LifeStory.key == key).first()
    return dict(row.payload) if row else None


def _written_today(db: Session, user_id: str) -> int:
    since = datetime.utcnow() - timedelta(days=1)
    return db.query(LifeStory).filter(LifeStory.user_id == user_id, LifeStory.created_at >= since).count()


def ensure_story(db: Session, user_id: str, kundli, signals: dict, *, ayanamsha: str, node_type: str,
                 agent_factory=LifeStoryAgent) -> tuple[dict | None, bool]:
    """(story, written_now). The stored story when there is one, else one
    written now and stored; (None, False) when neither is possible."""
    key = story_key(kundli, signals, ayanamsha, node_type)
    try:
        found = _stored(db, kundli.id, key)
    except SQLAlchemyError:
        db.rollback()
        log.warning("life_stories is not readable; serving the code backup", exc_info=True)
        return None, False
    if found:
        return found, False
    with _locks_guard:
        lock = _locks.setdefault(key, threading.Lock())
    with lock:
        try:
            found = _stored(db, kundli.id, key)
            if found:
                return found, False
            if _written_today(db, user_id) >= DAILY_WRITE_CEILING:
                return None, False
            return _write(db, user_id, kundli, key, signals, agent_factory)
        finally:
            with _locks_guard:
                _locks.pop(key, None)


def _write(db: Session, user_id: str, kundli, key: str, signals: dict, agent_factory) -> tuple[dict | None, bool]:
    agent = agent_factory()
    started = time.monotonic()
    story = None
    try:
        story = agent.write(signals)
    except Exception:
        log.exception("life story generation failed")
    usage = agent.usage_totals() if hasattr(agent, "usage_totals") else {}
    try:
        log.info(json.dumps({
            "event": "life_story.cost", "status": "written" if story else "fallback",
            "kundli_id": kundli.id, "seconds": round(time.monotonic() - started, 2),
            "gaps": story_gaps(story, signals) if story else [],
            **{k: usage.get(k) for k in ("provider", "model", "calls", "input_tokens", "output_tokens")},
        }))
    except Exception:  # accounting never costs a reader their story
        log.warning("life story cost line failed", exc_info=True)
    if not story:
        return None, False
    value = {
        "source": "agent",
        "story": to_payload(story, signals),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        db.add(LifeStory(user_id=user_id, kundli_id=kundli.id, key=key, payload=value))
        db.commit()
    except IntegrityError:
        db.rollback()
        return _stored(db, kundli.id, key) or value, False
    except SQLAlchemyError:
        db.rollback()
        log.warning("life story could not be stored", exc_info=True)
    return value, True
