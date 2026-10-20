"""The agent-written "About you two" section, written once per pair and kept.

GET /vedic/{id}/compatibility/{partner}/insight reads it from
`compatibility_insights`, and writes it the first time a pair is opened. The
row key hashes everything that changes the words: the prompt version, both
people's names and birth details, ayanamsha and node type, married or
planning, and both running periods (mahadasha and antardasha). A new period
is a new section, usually once every year or two per person; nothing else
expires it.

When the table is missing (the SQL not yet applied) or the model fails, the
caller gets None and the app keeps the fixed guidance. Nothing is written
without a row to keep it in, so a missing table can never turn into a model
call on every open.
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

from ..agents.compat_insight_agent import INSIGHT_VERSION, CompatInsightAgent, insight_gaps, insight_input
from ..db.models import CompatibilityInsight

log = logging.getLogger("astrospace.compat_insight")

# New sections one account may have written in a day. Plus has 3 profiles and
# Practitioner 10, so a real reader stays far below this; it caps what a
# script editing birth details in a loop can spend.
DAILY_WRITE_CEILING = 12

_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _birth(k) -> list:
    return [k.name, k.birth_year, k.birth_month, k.birth_day, k.birth_hour, k.birth_minute,
            k.birth_city, k.birth_nation]


def insight_key(kundli, partner, signals: dict, ayanamsha: str, node_type: str) -> str:
    periods = [person.get("running_period") for person in signals.get("people") or []]
    material = [INSIGHT_VERSION, _birth(kundli), _birth(partner), ayanamsha, node_type,
                signals.get("stage"), periods]
    return hashlib.sha256(json.dumps(material, default=str).encode()).hexdigest()[:40]


def _stored(db: Session, kundli_id: str, partner_id: str, key: str) -> dict | None:
    row = (
        db.query(CompatibilityInsight)
        .filter(CompatibilityInsight.kundli_id == kundli_id,
                CompatibilityInsight.partner_kundli_id == partner_id,
                CompatibilityInsight.key == key)
        .first()
    )
    return dict(row.payload) if row else None


def _written_today(db: Session, user_id: str) -> int:
    since = datetime.utcnow() - timedelta(days=1)
    return (
        db.query(CompatibilityInsight)
        .filter(CompatibilityInsight.user_id == user_id, CompatibilityInsight.created_at >= since)
        .count()
    )


def ensure_insight(db: Session, user_id: str, kundli, partner, chart_a, chart_b, result: dict, *,
                   stage: str, ayanamsha: str, node_type: str, as_of: datetime | None = None,
                   agent_factory=CompatInsightAgent) -> tuple[dict | None, bool]:
    """(section, written_now). The stored section when there is one, else one
    written now and stored; (None, False) when neither is possible."""
    signals = insight_input(chart_a, chart_b, result, stage, as_of or datetime.now(timezone.utc))
    key = insight_key(kundli, partner, signals, ayanamsha, node_type)
    try:
        found = _stored(db, kundli.id, partner.id, key)
    except SQLAlchemyError:
        db.rollback()
        log.warning("compatibility_insights is not readable; serving the fixed guidance", exc_info=True)
        return None, False
    if found:
        return found, False
    with _locks_guard:
        lock = _locks.setdefault(key, threading.Lock())
    with lock:
        try:
            found = _stored(db, kundli.id, partner.id, key)
            if found:
                return found, False
            if _written_today(db, user_id) >= DAILY_WRITE_CEILING:
                return None, False
            return _write(db, user_id, kundli, partner, key, signals, agent_factory)
        finally:
            with _locks_guard:
                _locks.pop(key, None)


def _write(db: Session, user_id: str, kundli, partner, key: str, signals: dict,
           agent_factory) -> tuple[dict | None, bool]:
    agent = agent_factory()
    started = time.monotonic()
    insight = None
    try:
        insight = agent.write(signals)
    except Exception:
        log.exception("compatibility insight generation failed")
    usage = agent.usage_totals() if hasattr(agent, "usage_totals") else {}
    try:
        log.info(json.dumps({
            "event": "compat_insight.cost", "status": "written" if insight else "fallback",
            "kundli_id": kundli.id, "partner_kundli_id": partner.id, "stage": signals.get("stage"),
            "seconds": round(time.monotonic() - started, 2),
            "gaps": insight_gaps(insight, signals) if insight else [],
            **{k: usage.get(k) for k in ("provider", "model", "calls", "input_tokens", "output_tokens")},
        }))
    except Exception:  # accounting never costs a reader their section
        log.warning("compatibility insight cost line failed", exc_info=True)
    if not insight:
        return None, False
    value = {
        "source": "agent",
        "insight": insight.model_dump(),
        "stage": signals.get("stage"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        db.add(CompatibilityInsight(user_id=user_id, kundli_id=kundli.id, partner_kundli_id=partner.id,
                                    key=key, stage=signals.get("stage") or "married", payload=value))
        db.commit()
    except IntegrityError:
        db.rollback()
        return _stored(db, kundli.id, partner.id, key) or value, False
    except SQLAlchemyError:
        db.rollback()
        log.warning("compatibility insight could not be stored", exc_info=True)
    return value, True
