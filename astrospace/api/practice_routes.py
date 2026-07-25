"""What the user actually keeps: remedies in progress, observances, saved
windows, and past compatibility checks.

Ownership note: several CRUD helpers here take only a row id
(`log_remedy_completion`, `get_remedy_streak`) because the delivery worker
calls them too. This layer therefore resolves the row through a user-filtered
query first — `_owned_remedy` — rather than trusting the id from the request.
"""
from datetime import date as date_cls, datetime, time as time_cls

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import crud, crud_mobile as cm, get_db
from ..db.models import UserRemedy
from .auth import CurrentUser

router = APIRouter(prefix="/api/v1/practice", tags=["practice"])

REMEDY_STATUSES = {"active", "paused", "completed", "abandoned"}
OBSERVANCE_STATUSES = {"planned", "observed", "skipped"}


# ── Payloads ─────────────────────────────────────────────────────────────────

class StartRemedy(BaseModel):
    kundli_id: str
    remedy_id: str
    target_count: int | None = Field(None, ge=1, le=1_000_000)
    cadence: str | None = None
    reminder_enabled: bool = False
    reminder_time: time_cls | None = None  # "HH:MM"; column is SQL TIME
    reminder_weekday: int | None = Field(None, ge=0, le=6)
    timezone: str | None = None


class UpdateRemedy(BaseModel):
    status: str | None = None
    target_count: int | None = Field(None, ge=1, le=1_000_000)
    cadence: str | None = None
    reminder_enabled: bool | None = None
    reminder_time: time_cls | None = None  # "HH:MM"; column is SQL TIME
    reminder_weekday: int | None = Field(None, ge=0, le=6)
    timezone: str | None = None


class LogCompletion(BaseModel):
    occurred_on: date_cls | None = None
    count: int = Field(1, ge=1, le=10_000)


class SetObservance(BaseModel):
    festival_id: str
    occurs_on: date_cls
    status: str = "planned"
    kundli_id: str | None = None
    reminder_enabled: bool = True
    reminder_lead_days: int = Field(3, ge=0, le=30)
    notes: str | None = None


class SaveMuhurta(BaseModel):
    kundli_id: str
    starts_at: datetime
    ends_at: datetime
    goal_slug: str | None = None
    label: str | None = None
    quality: str | None = None
    why: dict | None = None
    device_calendar_event_id: str | None = None


class SaveCompatibility(BaseModel):
    kundli_id: str
    partner_kundli_id: str
    total_score: float | None = None
    max_score: float = 36.0
    koota_breakdown: dict | None = None
    dosha_flags: dict | None = None
    verdict: str | None = None
    conventions: dict | None = None


# ── Helpers ──────────────────────────────────────────────────────────────────

def _owned_remedy(db: Session, user_remedy_id: str, user_id: str) -> UserRemedy:
    row = (
        db.query(UserRemedy)
        .filter(UserRemedy.id == user_remedy_id, UserRemedy.user_id == user_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Remedy not found")
    return row


def _require_kundli(db: Session, kundli_id: str, user_id: str):
    if not crud.get_kundli(db, kundli_id, user_id):
        raise HTTPException(status_code=404, detail="Kundli not found")


def _remedy(row, streak: int | None = None) -> dict:
    out = {
        "id": row.id,
        "kundli_id": row.kundli_id,
        "remedy_id": row.remedy_id,
        "status": row.status,
        "target_count": row.target_count,
        "cadence": row.cadence,
        "reminder_enabled": row.reminder_enabled,
        "reminder_time": (row.reminder_time.strftime("%H:%M")
                          if row.reminder_time else None),
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }
    if streak is not None:
        out["streak"] = streak
    return out


# ── Remedies in progress ─────────────────────────────────────────────────────

@router.post("/remedies")
def start_remedy(payload: StartRemedy, user: CurrentUser,
                 db: Session = Depends(get_db)):
    _require_kundli(db, payload.kundli_id, user.id)
    row = cm.start_user_remedy(
        db, user.id, payload.kundli_id, payload.remedy_id,
        **payload.model_dump(exclude={"kundli_id", "remedy_id"}, exclude_none=True),
    )
    return _remedy(row, streak=0)


@router.get("/remedies")
def list_remedies(user: CurrentUser,
                  kundli_id: str | None = None,
                  status: str | None = Query("active"),
                  db: Session = Depends(get_db)):
    if status is not None and status not in REMEDY_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"status must be one of {sorted(REMEDY_STATUSES)}",
        )
    rows = cm.list_user_remedies(db, user.id, kundli_id=kundli_id, status=status)
    return {"count": len(rows), "remedies": [
        # The streak is the whole point of the practice card, so it is computed
        # here rather than left to a follow-up request per row.
        _remedy(r, streak=cm.get_remedy_streak(db, r.id)) for r in rows
    ]}


@router.patch("/remedies/{user_remedy_id}")
def update_remedy(user_remedy_id: str, payload: UpdateRemedy, user: CurrentUser,
                  db: Session = Depends(get_db)):
    _owned_remedy(db, user_remedy_id, user.id)
    data = payload.model_dump(exclude_unset=True, exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    if "status" in data and data["status"] not in REMEDY_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"status must be one of {sorted(REMEDY_STATUSES)}",
        )
    row = cm.update_user_remedy(db, user_remedy_id, user.id, data)
    return _remedy(row, streak=cm.get_remedy_streak(db, row.id))


@router.post("/remedies/{user_remedy_id}/completions")
def log_completion(user_remedy_id: str, payload: LogCompletion, user: CurrentUser,
                   db: Session = Depends(get_db)):
    """Idempotent per day — logging twice increments the day's count."""
    _owned_remedy(db, user_remedy_id, user.id)
    on = payload.occurred_on or date_cls.today()
    if on > date_cls.today():
        raise HTTPException(status_code=400,
                            detail="occurred_on cannot be in the future")
    completion = cm.log_remedy_completion(db, user_remedy_id, on=on,
                                          count=payload.count)
    return {
        "occurred_on": completion.occurred_on.isoformat(),
        "count": completion.count,
        "streak": cm.get_remedy_streak(db, user_remedy_id),
    }


@router.get("/remedies/{user_remedy_id}/streak")
def remedy_streak(user_remedy_id: str, user: CurrentUser,
                  db: Session = Depends(get_db)):
    _owned_remedy(db, user_remedy_id, user.id)
    return {"streak": cm.get_remedy_streak(db, user_remedy_id)}


# ── Observances ──────────────────────────────────────────────────────────────

@router.put("/observances")
def set_observance(payload: SetObservance, user: CurrentUser,
                   db: Session = Depends(get_db)):
    """Upsert per (user, festival, date) — the same festival recurs yearly."""
    if payload.status not in OBSERVANCE_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"status must be one of {sorted(OBSERVANCE_STATUSES)}",
        )
    if payload.kundli_id:
        _require_kundli(db, payload.kundli_id, user.id)
    row = cm.set_observance(
        db, user.id, payload.festival_id, payload.occurs_on,
        **payload.model_dump(exclude={"festival_id", "occurs_on"},
                             exclude_none=True),
    )
    return {
        "id": row.id,
        "festival_id": row.festival_id,
        "occurs_on": row.occurs_on.isoformat(),
        "status": row.status,
        "reminder_enabled": row.reminder_enabled,
        "reminder_lead_days": row.reminder_lead_days,
        "notes": row.notes,
    }


# ── Saved muhurtas ───────────────────────────────────────────────────────────

@router.post("/saved-muhurtas")
def save_muhurta(payload: SaveMuhurta, user: CurrentUser,
                 db: Session = Depends(get_db)):
    if payload.ends_at <= payload.starts_at:
        raise HTTPException(status_code=400,
                            detail="ends_at must be after starts_at")
    _require_kundli(db, payload.kundli_id, user.id)
    row = cm.save_muhurta(
        db, user.id, payload.kundli_id, payload.starts_at, payload.ends_at,
        **payload.model_dump(exclude={"kundli_id", "starts_at", "ends_at"},
                             exclude_none=True),
    )
    return {"id": row.id, "goal_slug": row.goal_slug, "label": row.label,
            "quality": row.quality,
            "starts_at": row.starts_at.isoformat(),
            "ends_at": row.ends_at.isoformat()}


@router.get("/saved-muhurtas")
def list_saved_muhurtas(user: CurrentUser, upcoming_only: bool = True,
                        db: Session = Depends(get_db)):
    rows = cm.list_saved_muhurtas(db, user.id, upcoming_only=upcoming_only)
    return {"count": len(rows), "muhurtas": [
        {"id": r.id, "kundli_id": r.kundli_id, "goal_slug": r.goal_slug,
         "label": r.label, "quality": r.quality, "why": r.why,
         "starts_at": r.starts_at.isoformat(), "ends_at": r.ends_at.isoformat()}
        for r in rows
    ]}


# ── Compatibility history ────────────────────────────────────────────────────

@router.post("/compatibility-checks")
def save_compatibility_check(payload: SaveCompatibility, user: CurrentUser,
                             db: Session = Depends(get_db)):
    _require_kundli(db, payload.kundli_id, user.id)
    _require_kundli(db, payload.partner_kundli_id, user.id)
    row = cm.save_compatibility_check(
        db, user.id, payload.kundli_id, payload.partner_kundli_id,
        **payload.model_dump(exclude={"kundli_id", "partner_kundli_id"},
                             exclude_none=True),
    )
    return {"id": row.id, "total_score": row.total_score,
            "max_score": row.max_score, "verdict": row.verdict}


@router.get("/compatibility-checks")
def list_compatibility_checks(user: CurrentUser,
                              limit: int = Query(20, ge=1, le=100),
                              db: Session = Depends(get_db)):
    rows = cm.list_compatibility_checks(db, user.id, limit=limit)
    return {"count": len(rows), "checks": [
        {"id": r.id, "kundli_id": r.kundli_id,
         "partner_kundli_id": r.partner_kundli_id,
         "total_score": r.total_score, "max_score": r.max_score,
         "verdict": r.verdict, "koota_breakdown": r.koota_breakdown,
         # Surfaced, never suppressed — a dosha is a flag, not a verdict.
         "dosha_flags": r.dosha_flags, "conventions": r.conventions,
         "created_at": r.created_at.isoformat() if r.created_at else None}
        for r in rows
    ]}
