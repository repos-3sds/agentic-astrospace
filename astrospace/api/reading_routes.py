from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from ..db import get_db
from ..db import crud
from ..agents.period_agent import PeriodAgent

router = APIRouter(prefix="/api/v1/readings", tags=["readings"])

VALID_PERIODS = {"daily", "weekly", "monthly", "quarterly", "yearly"}


class GenerateRequest(BaseModel):
    period: str
    force_refresh: bool = False


def _reading_to_dict(r) -> dict:
    return {
        "id":           r.id,
        "kundli_id":    r.kundli_id,
        "reading_type": r.reading_type,
        "period_label": r.period_label,
        "content":      r.content,
        "generated_at": r.generated_at.isoformat() if r.generated_at else None,
    }


@router.post("/{kundli_id}/generate")
def generate_reading(
    kundli_id: str,
    body: GenerateRequest,
    db: Session = Depends(get_db),
):
    if body.period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"period must be one of {sorted(VALID_PERIODS)}")

    k = crud.get_kundli(db, kundli_id)
    if not k:
        raise HTTPException(status_code=404, detail="Kundli not found")

    if not body.force_refresh:
        latest = crud.get_latest_reading(db, kundli_id, body.period)
        if latest:
            from datetime import datetime, timezone, timedelta
            age_limits = {
                "daily":     timedelta(hours=20),
                "weekly":    timedelta(days=6),
                "monthly":   timedelta(days=25),
                "quarterly": timedelta(days=80),
                "yearly":    timedelta(days=350),
            }
            age = datetime.now(timezone.utc) - latest.generated_at.replace(tzinfo=timezone.utc)
            if age < age_limits[body.period]:
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

    from datetime import datetime
    period_label = datetime.utcnow().strftime({
        "daily":     "%Y-%m-%d",
        "weekly":    "Week of %b %d, %Y",
        "monthly":   "%B %Y",
        "quarterly": "Q{q} %Y",
        "yearly":    "%Y",
    }[body.period])
    if body.period == "quarterly":
        from datetime import datetime as dt
        now = dt.utcnow()
        q = (now.month - 1) // 3 + 1
        period_label = f"Q{q} {now.year}"

    r = crud.save_reading(db, kundli_id, body.period, content, period_label)
    return {"cached": False, **_reading_to_dict(r)}


@router.get("/{kundli_id}")
def list_readings(
    kundli_id: str,
    period: Optional[str] = None,
    db: Session = Depends(get_db),
):
    k = crud.get_kundli(db, kundli_id)
    if not k:
        raise HTTPException(status_code=404, detail="Kundli not found")
    readings = crud.get_readings(db, kundli_id, period)
    return [_reading_to_dict(r) for r in readings]


@router.get("/{kundli_id}/latest/{period}")
def latest_reading(kundli_id: str, period: str, db: Session = Depends(get_db)):
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"period must be one of {sorted(VALID_PERIODS)}")
    k = crud.get_kundli(db, kundli_id)
    if not k:
        raise HTTPException(status_code=404, detail="Kundli not found")
    r = crud.get_latest_reading(db, kundli_id, period)
    if not r:
        raise HTTPException(status_code=404, detail="No reading found for this period")
    return _reading_to_dict(r)
