from calendar import monthrange
from datetime import date, datetime, timezone, timedelta
from difflib import SequenceMatcher
import logging
import re
import threading
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Literal, Optional
from ..db import get_db
from ..db import crud
from ..core.cities import lookup_city
from ..core.vedic.chart import VedicChart
from ..core.vedic.positions import LocationError
from ..agents.period_agent import PeriodAgent
from ..agents.safety import REFER_OUT_ANSWERS
from .auth import CurrentUser

router = APIRouter(prefix="/api/v1/readings", tags=["readings"])
logger = logging.getLogger(__name__)

# What the person sees when the model call fails. The provider's own error
# (a 400 body, a quota message) goes to the log, never to the screen.
READING_UNAVAILABLE = "Your reading couldn't be written just now. Please try again in a minute."
NO_ANSWER = "Unable to generate a response."

VALID_PERIODS = {"daily", "weekly", "monthly", "quarterly", "yearly"}
CLAIM_STATUSES = {"pending", "accurate", "partly", "missed", "not_applicable"}

CLAIM_CATEGORY_KEYWORDS = {
    "career": {"career", "work", "job", "business", "profession", "project", "leadership"},
    "finance": {"money", "finance", "income", "expense", "investment", "wealth", "cash"},
    "relationship": {"relationship", "partner", "family", "marriage", "love", "friend"},
    "health": {"health", "energy", "stress", "rest", "body", "sleep", "vitality"},
    "learning": {"study", "learning", "skill", "education", "research", "knowledge"},
    "spiritual": {"spiritual", "meditation", "ritual", "faith", "inner", "intuition"},
    "timing": {"today", "week", "month", "quarter", "year", "delay", "window", "timing"},
}


def _kundli_now(k) -> datetime:
    """Current time in the kundli's birth-place timezone (fallback UTC),
    so period labels match the person's local calendar day."""
    geo = lookup_city(k.birth_city, k.birth_nation)
    tz = ZoneInfo(geo[2]) if geo else timezone.utc
    return datetime.now(tz)


def _period_start(period: str, local_day: date) -> date:
    """First day of the calendar period that contains `local_day`.

    Weeks run Monday to Sunday. That is a calendar convention for grouping
    readings, not an astrological one (the Vedic weekday cycle starts on
    Ravivara); it only decides which readings count as "this week".

    On Saturday and Sunday the weekly reading is the week ahead: one asked
    for on Sat 17 Oct covered 12-18 Oct, five days already gone
    (regression 2026-10-17).
    """
    if period == "weekly":
        monday = local_day - timedelta(days=local_day.weekday())
        return monday + timedelta(days=7) if local_day.weekday() >= 5 else monday
    if period == "monthly":
        return local_day.replace(day=1)
    if period == "quarterly":
        return local_day.replace(month=((local_day.month - 1) // 3) * 3 + 1, day=1)
    if period == "yearly":
        return local_day.replace(month=1, day=1)
    return local_day


def _period_label(period: str, now: datetime) -> str:
    """The label a reading is filed and looked up under.

    It names the period, not the moment of writing, so it is the same for
    every request inside one period. Weekly used to read "Week of <today>",
    which changed every day: the cache lookup missed daily and each miss
    wrote another paid "Version 1" (production audit 2026-10-15, R1).
    `now` is the kundli-local time from `_kundli_now`.
    """
    start = _period_start(period, now.date())
    if period == "weekly":
        return f"Week of {start.strftime('%b')} {start.day}, {start.year}"
    if period == "quarterly":
        return f"Q{(start.month - 1) // 3 + 1} {start.year}"
    return start.strftime({
        "daily":   "%Y-%m-%d",
        "monthly": "%B %Y",
        "yearly":  "%Y",
    }[period])


class GenerateRequest(BaseModel):
    period: str
    force_refresh: bool = False


class FeedbackRequest(BaseModel):
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    feedback: Optional[str] = Field(default=None, max_length=4000)


class ClaimFeedbackRequest(BaseModel):
    status: Literal["pending", "accurate", "partly", "missed", "not_applicable"]
    feedback: Optional[str] = Field(default=None, max_length=2000)


def _reading_words(content: str) -> set[str]:
    words = re.findall(r"[a-zA-Z]{4,}", content.lower())
    stop = {
        "this", "that", "with", "from", "your", "will", "have", "into",
        "about", "there", "their", "should", "could", "would", "because",
        "astrological", "basis", "reading", "period",
    }
    return {w for w in words if w not in stop}


def _deviation(previous: str | None, current: str) -> tuple[float | None, dict | None]:
    if not previous:
        return None, None
    sequence_similarity = SequenceMatcher(None, previous, current).ratio()
    prev_words = _reading_words(previous)
    curr_words = _reading_words(current)
    overlap = len(prev_words & curr_words) / max(1, len(prev_words | curr_words))
    similarity = (sequence_similarity * 0.55) + (overlap * 0.45)
    score = round((1 - similarity) * 100, 1)
    if score < 20:
        band = "low"
    elif score < 45:
        band = "moderate"
    else:
        band = "high"
    added = sorted(curr_words - prev_words)[:12]
    removed = sorted(prev_words - curr_words)[:12]
    return score, {
        "band": band,
        "similarity": round(similarity * 100, 1),
        "added_terms": added,
        "removed_terms": removed,
    }


def _reading_range(r) -> tuple[str | None, str | None]:
    """The calendar period a saved reading belongs to, from the kundli-local
    date it was written on. Rows written under the old "Week of <today>"
    labels get the Monday–Sunday week they fall in, so the client can title
    them by date either way."""
    try:
        day = date.fromisoformat(r.generated_local_date or "")
    except ValueError:
        return None, None
    if r.reading_type not in VALID_PERIODS:
        return None, None
    return _period_window(r.reading_type, datetime(day.year, day.month, day.day))


def _reading_to_dict(r, current_label: str | None = None) -> dict:
    period_start, period_end = _reading_range(r)
    return {
        "period_start": period_start,
        "period_end":   period_end,
        # Whether this row is a version of the period the person is in now
        # (production audit R2). Only set where the caller knows "now".
        "is_current_period": (r.period_label == current_label) if current_label is not None else None,
        "id":           r.id,
        "kundli_id":    r.kundli_id,
        "reading_type": r.reading_type,
        "period_label": r.period_label,
        "generated_local_date": r.generated_local_date,
        "version":      r.version or 1,
        "parent_reading_id": r.parent_reading_id,
        "deviation_score": r.deviation_score,
        "deviation_summary": r.deviation_summary,
        "user_rating":  r.user_rating,
        "user_feedback": r.user_feedback,
        "reviewed_at":  r.reviewed_at.isoformat() if r.reviewed_at else None,
        "content":      r.content,
        "generated_at": r.generated_at.isoformat() if r.generated_at else None,
    }


def _display_claim_text(c) -> str:
    """Claims saved before headers were stripped read "## Career and money A
    delayed payment...". Drop the fused section heading on the way out; the
    stored row is left as it is."""
    text = c.claim_text or ""
    if not text.lstrip().startswith("#"):
        return text
    body = text.lstrip().lstrip("#").strip()
    content = c.reading.content if c.reading else ""
    for heading in _HEADING.findall(content or ""):
        title = heading.strip().lstrip("#").strip()
        if title and body.lower().startswith(title.lower() + " "):
            return body[len(title):].strip()
    return body


def _claim_to_dict(c) -> dict:
    return {
        "id": c.id,
        "kundli_id": c.kundli_id,
        "reading_id": c.reading_id,
        "reading_type": c.reading_type,
        "reading_version": (c.reading.version or 1) if c.reading else None,
        "period_label": c.period_label,
        "generated_local_date": c.generated_local_date,
        "target_start_date": c.target_start_date,
        "target_end_date": c.target_end_date,
        "category": c.category,
        "claim_text": _display_claim_text(c),
        "confidence": c.confidence,
        "source_excerpt": c.source_excerpt,
        "status": c.status,
        "user_feedback": c.user_feedback,
        "reviewed_at": c.reviewed_at.isoformat() if c.reviewed_at else None,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def _period_window(period: str, now_local: datetime) -> tuple[str, str]:
    """ISO start and end of the calendar period `now_local` falls in, the
    same period `_period_label` names. Claims carry this as their window,
    so "Week of Oct 12" covers Oct 12 – 18, not the seven days from
    whenever it happened to be written."""
    start = _period_start(period, now_local.date())
    if period == "daily":
        end = start
    elif period == "weekly":
        end = start + timedelta(days=6)
    elif period == "monthly":
        end = start.replace(day=monthrange(start.year, start.month)[1])
    elif period == "quarterly":
        end_month = start.month + 2
        end = start.replace(month=end_month, day=monthrange(start.year, end_month)[1])
    else:
        end = start.replace(month=12, day=31)
    return start.isoformat(), end.isoformat()


def _claim_category(text: str) -> str:
    words = set(re.findall(r"[a-zA-Z]{3,}", text.lower()))
    best = ("general", 0)
    for category, keywords in CLAIM_CATEGORY_KEYWORDS.items():
        hits = len(words & keywords)
        if hits > best[1]:
            best = (category, hits)
    return best[0]


def _claim_confidence(text: str) -> float:
    lower = text.lower()
    confidence = 0.62
    if any(token in lower for token in ("likely", "strong", "clear", "high chance", "supports")):
        confidence += 0.14
    if any(token in lower for token in ("may", "might", "could", "possible", "tendency")):
        confidence -= 0.14
    if any(token in lower for token in ("avoid", "caution", "watch", "risk")):
        confidence += 0.04
    return round(max(0.25, min(0.9, confidence)), 2)


_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+.*$", re.MULTILINE)
_LIST_MARKER = re.compile(r"^\s*(?:[-*+•]|\d+[.)])\s+", re.MULTILINE)
_EMPHASIS = re.compile(r"(\*\*|__|\*|_|`)")


def _plain_prose(content: str) -> str:
    """The reading's sentences without its markdown scaffolding.

    Readings are written with `##` section headers. Claims used to be cut
    from the whitespace-collapsed text, so a header ran into the first
    sentence after it ("## Career and money A delayed payment…") and that
    fused string was what people were asked to review. Headers carry no
    prediction, so they go; list markers and emphasis are unwrapped. One
    line per paragraph or bullet, so a sentence never spans two of them.
    """
    text = _HEADING.sub("", content)
    text = _LIST_MARKER.sub("", text)
    text = _EMPHASIS.sub("", text)
    return text


def _extract_prediction_claims(
    content: str,
    *,
    kundli_id: str,
    reading_id: str,
    user_id: str,
    reading_type: str,
    period_label: str,
    generated_local_date: str,
    target_start_date: str,
    target_end_date: str,
) -> list[dict]:
    normalized = re.sub(r"\s+", " ", _plain_prose(content)).strip()
    pieces = [
        piece
        for line in _plain_prose(content).splitlines()
        for piece in re.split(r"(?<=[.!?])\s+|(?:\s+-\s+)", line.strip())
    ]
    claims: list[dict] = []
    seen: set[str] = set()
    predictive_terms = re.compile(
        r"\b(will|may|might|could|likely|expect|avoid|watch|support|favour|favor|"
        r"opportunity|challenge|delay|improve|increase|decrease|focus|good|better)\b",
        re.IGNORECASE,
    )
    for piece in pieces:
        claim_text = piece.strip(" -*\n\t")
        if len(claim_text) < 45 or len(claim_text) > 360:
            continue
        if not predictive_terms.search(claim_text):
            continue
        key = claim_text.lower()
        if key in seen:
            continue
        seen.add(key)
        claims.append({
            "kundli_id": kundli_id,
            "reading_id": reading_id,
            "user_id": user_id,
            "reading_type": reading_type,
            "period_label": period_label,
            "generated_local_date": generated_local_date,
            "target_start_date": target_start_date,
            "target_end_date": target_end_date,
            "category": _claim_category(claim_text),
            "claim_text": claim_text,
            "confidence": _claim_confidence(claim_text),
            "source_excerpt": claim_text[:240],
            "status": "pending",
        })
        if len(claims) >= 12:
            break
    if not claims:
        claims.append({
            "kundli_id": kundli_id,
            "reading_id": reading_id,
            "user_id": user_id,
            "reading_type": reading_type,
            "period_label": period_label,
            "generated_local_date": generated_local_date,
            "target_start_date": target_start_date,
            "target_end_date": target_end_date,
            "category": "general",
            "claim_text": normalized[:320] or "Generated reading needs manual claim review.",
            "confidence": 0.35,
            "source_excerpt": normalized[:240],
            "status": "pending",
        })
    return claims


# ── Generation guard ─────────────────────────────────────────────────────────
#
# A reading is one model call of 20-40 s. Two taps on "New version", or the
# same screen open twice, used to start two paid generations for the same
# period (production audit 2026-10-15, R6). A request that arrives while one
# is in flight for the same (kundli, period, label) now waits for it and
# returns its result. The registry is per process: with several workers a
# duplicate can still slip through on another worker, and the daily cap
# below (which counts saved rows, so it holds across workers) bounds that.

class _InFlight:
    def __init__(self) -> None:
        self.done = threading.Event()
        self.reading_id: str | None = None
        self.waiters = 0


_IN_FLIGHT: dict[tuple[str, str, str], _InFlight] = {}
_IN_FLIGHT_LOCK = threading.Lock()
IN_FLIGHT_WAIT_SECONDS = 180

# New versions per kundli and period per kundli-local day. The first reading
# of a period is not counted; only regenerations of it are.
MAX_NEW_VERSIONS_PER_DAY = 3
NEW_VERSION_LIMIT = (
    "You’ve asked for {limit} new versions of this {period} reading today. "
    "Your latest version is still here, and you can ask for another tomorrow."
)


def _join_in_flight(db: Session, kundli_id: str, user_id: str, entry: _InFlight) -> dict:
    """Wait for the generation already running and answer with what it made."""
    entry.done.wait(IN_FLIGHT_WAIT_SECONDS)
    reading = crud.get_reading(db, kundli_id, entry.reading_id, user_id) if entry.reading_id else None
    if reading is None:
        # The run we waited on failed or is still going; don't start another.
        raise HTTPException(status_code=503, detail=READING_UNAVAILABLE)
    return {"cached": True, **_reading_to_dict(reading, reading.period_label)}


@router.post("/{kundli_id}/generate")
def generate_reading(
    kundli_id: str,
    body: GenerateRequest,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    if body.period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"period must be one of {sorted(VALID_PERIODS)}")

    k = crud.get_kundli(db, kundli_id, user.id)
    if not k:
        raise HTTPException(status_code=404, detail="Kundli not found")

    now_local = _kundli_now(k)
    label = _period_label(body.period, now_local)
    local_date = now_local.strftime("%Y-%m-%d")

    if not body.force_refresh:
        # The label names the period, so a reading filed under it is this
        # period's reading however long ago in the period it was written.
        latest = crud.get_latest_period_reading(db, kundli_id, body.period, label, user.id)
        if latest:
            return {"cached": True, **_reading_to_dict(latest, label)}

    key = (kundli_id, body.period, label)
    with _IN_FLIGHT_LOCK:
        entry = _IN_FLIGHT.get(key)
        owner = entry is None
        if owner:
            entry = _IN_FLIGHT[key] = _InFlight()
        else:
            entry.waiters += 1
    if not owner:
        return _join_in_flight(db, kundli_id, user.id, entry)

    try:
        if body.force_refresh and crud.count_new_period_versions(
            db, kundli_id, body.period, local_date, user.id,
        ) >= MAX_NEW_VERSIONS_PER_DAY:
            raise HTTPException(status_code=429, detail=NEW_VERSION_LIMIT.format(
                limit=MAX_NEW_VERSIONS_PER_DAY, period=body.period,
            ))
        r = _generate_and_save(db, k, body.period, label, local_date, now_local, user.id)
        entry.reading_id = r.id
        return {"cached": False, **_reading_to_dict(r, label)}
    finally:
        with _IN_FLIGHT_LOCK:
            _IN_FLIGHT.pop(key, None)
        entry.done.set()


def _generate_and_save(db: Session, k, period: str, label: str, local_date: str, now_local: datetime, user_id: str):
    kundli_id = k.id
    target_start_date, target_end_date = _period_window(period, now_local)
    try:
        chart = VedicChart(
            k.name, k.birth_year, k.birth_month, k.birth_day,
            k.birth_hour, k.birth_minute, k.birth_city, k.birth_nation,
        )
    except LocationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except (ValueError, OverflowError) as e:
        raise HTTPException(status_code=422, detail=f"Invalid birth details on this kundli: {e}")

    try:
        content, crossed = PeriodAgent(chart).generate_reading(period, now=now_local)
    except Exception:
        logger.exception("reading generation failed (kundli=%s period=%s)", kundli_id, period)
        raise HTTPException(status_code=503, detail=READING_UNAVAILABLE)
    if not content.strip() or content.strip() == NO_ANSWER:
        # The agent loop ran out without an answer. Saving it would publish
        # the placeholder as this period's reading and mint claims from it.
        logger.error("reading generation returned no text (kundli=%s period=%s)", kundli_id, period)
        raise HTTPException(status_code=503, detail=READING_UNAVAILABLE)
    if crossed:
        # Output-side safety net, same tier as Ask's verifier. Nothing is
        # persisted and no claims are extracted: a reading that crossed the
        # boundary twice is declined, not trimmed.
        raise HTTPException(status_code=422, detail={
            "kind": "refer_out",
            "domain": crossed,
            "message": (
                "This reading was not published because it crossed a boundary "
                "AstroSpace does not cross. "
                + REFER_OUT_ANSWERS.get(crossed, "A dosha is a flag, not a verdict.")
                + " Try generating it again."
            ),
        })

    previous = crud.get_latest_period_reading(db, kundli_id, period, label, user_id)
    next_version = (previous.version or 1) + 1 if previous else 1
    deviation_score, deviation_summary = _deviation(previous.content if previous else None, content)
    r = crud.save_reading(
        db,
        kundli_id,
        period,
        content,
        label,
        generated_local_date=local_date,
        version=next_version,
        parent_reading_id=previous.id if previous else None,
        deviation_score=deviation_score,
        deviation_summary=deviation_summary,
    )
    claims = _extract_prediction_claims(
        content,
        kundli_id=kundli_id,
        reading_id=r.id,
        user_id=user_id,
        reading_type=period,
        period_label=label,
        generated_local_date=local_date,
        target_start_date=target_start_date,
        target_end_date=target_end_date,
    )
    crud.replace_prediction_claims(db, r.id, claims, user_id)
    return r


@router.get("/{kundli_id}")
def list_readings(
    kundli_id: str,
    user: CurrentUser,
    period: Optional[str] = None,
    period_label: Optional[str] = None,
    generated_date: Optional[str] = None,
    db: Session = Depends(get_db),
):
    k = crud.get_kundli(db, kundli_id, user.id)
    if not k:
        raise HTTPException(status_code=404, detail="Kundli not found")
    readings = crud.get_readings(
        db,
        kundli_id,
        user.id,
        period,
        period_label=period_label,
        generated_local_date=generated_date,
    )
    # Every row says whether it belongs to the period the person is in now,
    # so "versions of this week" and "past weeks" are not mixed together.
    now_local = _kundli_now(k)
    current = {p: _period_label(p, now_local) for p in VALID_PERIODS}
    return [_reading_to_dict(r, current.get(r.reading_type, "")) for r in readings]


@router.patch("/{kundli_id}/{reading_id}/feedback")
def update_feedback(
    kundli_id: str,
    reading_id: str,
    body: FeedbackRequest,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    k = crud.get_kundli(db, kundli_id, user.id)
    if not k:
        raise HTTPException(status_code=404, detail="Kundli not found")
    r = crud.update_reading_feedback(db, kundli_id, reading_id, user.id, body.rating, body.feedback)
    if not r:
        raise HTTPException(status_code=404, detail="Reading not found")
    return _reading_to_dict(r)


@router.get("/{kundli_id}/claims")
def list_prediction_claims(
    kundli_id: str,
    user: CurrentUser,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(default=200, ge=1, le=500),
    include_superseded: bool = False,
    db: Session = Depends(get_db),
):
    if status and status not in CLAIM_STATUSES:
        raise HTTPException(status_code=400, detail=f"status must be one of {sorted(CLAIM_STATUSES)}")
    k = crud.get_kundli(db, kundli_id, user.id)
    if not k:
        raise HTTPException(status_code=404, detail="Kundli not found")
    claims = crud.get_prediction_claims(
        db,
        kundli_id,
        user.id,
        status=status,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    if not include_superseded:
        superseded = _superseded_reading_ids(db, kundli_id, user.id)
        claims = [c for c in claims if c.status != "pending" or c.reading_id not in superseded]
    return [_claim_to_dict(c) for c in claims]


def _superseded_reading_ids(db: Session, kundli_id: str, user_id: str) -> set[str]:
    """Readings that a newer version of the same period has replaced.

    Every "Generate new" writes a fresh version with its own claims, and the
    old version's unreviewed claims used to stay in the review queue beside
    the new ones: the same sentence twice, for a reading the person had
    already thrown away. Those are hidden by default. A claim someone already
    reviewed stays, whatever version it came from: that verdict is history.
    """
    latest: dict[tuple[str, str | None], tuple] = {}
    superseded: set[str] = set()
    for r in crud.get_readings(db, kundli_id, user_id, limit=500):
        key = (r.reading_type, r.period_label)
        rank = (r.version or 1, r.generated_at)
        current = latest.get(key)
        if current is None or rank > current[0]:
            if current is not None:
                superseded.add(current[1])
            latest[key] = (rank, r.id)
        else:
            superseded.add(r.id)
    return superseded


@router.patch("/{kundli_id}/claims/{claim_id}")
def update_prediction_claim(
    kundli_id: str,
    claim_id: str,
    body: ClaimFeedbackRequest,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    k = crud.get_kundli(db, kundli_id, user.id)
    if not k:
        raise HTTPException(status_code=404, detail="Kundli not found")
    claim = crud.update_prediction_claim_feedback(
        db,
        kundli_id,
        claim_id,
        user.id,
        body.status,
        body.feedback,
    )
    if not claim:
        raise HTTPException(status_code=404, detail="Prediction claim not found")
    return _claim_to_dict(claim)


@router.get("/{kundli_id}/latest/{period}")
def latest_reading(kundli_id: str, period: str, user: CurrentUser, db: Session = Depends(get_db)):
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"period must be one of {sorted(VALID_PERIODS)}")
    k = crud.get_kundli(db, kundli_id, user.id)
    if not k:
        raise HTTPException(status_code=404, detail="Kundli not found")
    r = crud.get_latest_reading(db, kundli_id, period, user.id)
    if not r:
        raise HTTPException(status_code=404, detail="No reading found for this period")
    return _reading_to_dict(r)
