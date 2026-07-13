from calendar import monthrange
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher
import re
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Literal, Optional
from ..db import get_db
from ..db import crud
from ..core.cities import lookup_city
from ..agents.period_agent import PeriodAgent
from .auth import CurrentUser

router = APIRouter(prefix="/api/v1/readings", tags=["readings"])

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


def _period_label(period: str, now: datetime) -> str:
    if period == "quarterly":
        return f"Q{(now.month - 1) // 3 + 1} {now.year}"
    return now.strftime({
        "daily":   "%Y-%m-%d",
        "weekly":  "Week of %b %d, %Y",
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


def _reading_to_dict(r) -> dict:
    return {
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


def _claim_to_dict(c) -> dict:
    return {
        "id": c.id,
        "kundli_id": c.kundli_id,
        "reading_id": c.reading_id,
        "reading_type": c.reading_type,
        "period_label": c.period_label,
        "generated_local_date": c.generated_local_date,
        "target_start_date": c.target_start_date,
        "target_end_date": c.target_end_date,
        "category": c.category,
        "claim_text": c.claim_text,
        "confidence": c.confidence,
        "source_excerpt": c.source_excerpt,
        "status": c.status,
        "user_feedback": c.user_feedback,
        "reviewed_at": c.reviewed_at.isoformat() if c.reviewed_at else None,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def _period_window(period: str, now_local: datetime) -> tuple[str, str]:
    start = now_local.date()
    if period == "daily":
        end = start
    elif period == "weekly":
        end = start + timedelta(days=6)
    elif period == "monthly":
        end = start.replace(day=monthrange(start.year, start.month)[1])
    elif period == "quarterly":
        quarter_end_month = ((now_local.month - 1) // 3 + 1) * 3
        end = start.replace(
            month=quarter_end_month,
            day=monthrange(start.year, quarter_end_month)[1],
        )
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
    normalized = re.sub(r"\s+", " ", content.replace("•", ".")).strip()
    pieces = re.split(r"(?<=[.!?])\s+|(?:\s+-\s+)", normalized)
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
    target_start_date, target_end_date = _period_window(body.period, now_local)

    if not body.force_refresh:
        latest = crud.get_latest_period_reading(db, kundli_id, body.period, label)
        if latest:
            if body.period == "daily":
                # a daily reading is stale as soon as the local date changes
                fresh = latest.period_label == label
            else:
                age_limits = {
                    "weekly":    timedelta(days=6),
                    "monthly":   timedelta(days=25),
                    "quarterly": timedelta(days=80),
                    "yearly":    timedelta(days=350),
                }
                age = datetime.now(timezone.utc) - latest.generated_at.replace(tzinfo=timezone.utc)
                fresh = age < age_limits[body.period]
            if fresh:
                return {"cached": True, **_reading_to_dict(latest)}

    agent = PeriodAgent()
    content = agent.generate_reading(
        period=body.period,
        name=k.name,
        year=k.birth_year,
        month=k.birth_month,
        day=k.birth_day,
        hour=k.birth_hour,
        minute=k.birth_minute,
        city=k.birth_city,
        nation=k.birth_nation,
    )

    previous = crud.get_latest_period_reading(db, kundli_id, body.period, label)
    next_version = (previous.version or 1) + 1 if previous else 1
    deviation_score, deviation_summary = _deviation(previous.content if previous else None, content)
    r = crud.save_reading(
        db,
        kundli_id,
        body.period,
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
        user_id=user.id,
        reading_type=body.period,
        period_label=label,
        generated_local_date=local_date,
        target_start_date=target_start_date,
        target_end_date=target_end_date,
    )
    crud.replace_prediction_claims(db, r.id, claims)
    return {"cached": False, **_reading_to_dict(r)}


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
        period,
        period_label=period_label,
        generated_local_date=generated_date,
    )
    return [_reading_to_dict(r) for r in readings]


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
    r = crud.update_reading_feedback(db, kundli_id, reading_id, body.rating, body.feedback)
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
    return [_claim_to_dict(c) for c in claims]


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
    r = crud.get_latest_reading(db, kundli_id, period)
    if not r:
        raise HTTPException(status_code=404, detail="No reading found for this period")
    return _reading_to_dict(r)
