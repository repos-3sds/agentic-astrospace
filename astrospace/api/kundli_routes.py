from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Literal, Optional
from ..db import get_db, Kundli
from ..db import crud
from ..core.chart import BirthChart
from .auth import CurrentUser

router = APIRouter(prefix="/api/v1/kundlis", tags=["kundlis"])

_BIRTH_FIELDS = {"birth_year", "birth_month", "birth_day", "birth_hour",
                 "birth_minute", "birth_city", "birth_nation"}

# How much to trust birth_hour/birth_minute. "approximate" is the reader's own
# admission (onboarding's "use a gentle estimate"); "unknown" is a time nobody
# has, defaulted to noon. Either one moves the ascendant by up to a sign, so
# every screen that shows house- or dasha-derived data must be able to say so.
# The column has existed since the kundlis table gained it; until 2026-10-15
# the apps wrote "Birth time is approximate." into the free-text notes instead,
# which nothing downstream could read.
BirthTimeAccuracy = Literal["exact", "approximate", "unknown"]


class KundliCreate(BaseModel):
    name: str
    relation: str = "friend"
    birth_year: int = Field(ge=1200, le=2100)
    birth_month: int = Field(ge=1, le=12)
    birth_day: int = Field(ge=1, le=31)
    birth_hour: int = Field(default=12, ge=0, le=23)
    birth_minute: int = Field(default=0, ge=0, le=59)
    birth_city: str
    birth_nation: str = "US"
    birth_time_accuracy: BirthTimeAccuracy = "exact"
    notes: Optional[str] = None


class KundliUpdate(BaseModel):
    name: Optional[str] = None
    relation: Optional[str] = None
    birth_year: Optional[int] = Field(default=None, ge=1200, le=2100)
    birth_month: Optional[int] = Field(default=None, ge=1, le=12)
    birth_day: Optional[int] = Field(default=None, ge=1, le=31)
    birth_hour: Optional[int] = Field(default=None, ge=0, le=23)
    birth_minute: Optional[int] = Field(default=None, ge=0, le=59)
    birth_city: Optional[str] = None
    birth_nation: Optional[str] = None
    birth_time_accuracy: Optional[BirthTimeAccuracy] = None
    notes: Optional[str] = None


def _kundli_to_dict(k: Kundli) -> dict:
    return {
        "id":           k.id,
        "user_id":      k.user_id,
        "name":         k.name,
        "relation":     k.relation,
        "birth_year":   k.birth_year,
        "birth_month":  k.birth_month,
        "birth_day":    k.birth_day,
        "birth_hour":   k.birth_hour,
        "birth_minute": k.birth_minute,
        "birth_city":   k.birth_city,
        "birth_nation": k.birth_nation,
        "birth_time_accuracy": k.birth_time_accuracy or "exact",
        "sun_sign":     k.sun_sign,
        "moon_sign":    k.moon_sign,
        "ascendant":    k.ascendant,
        "chart_data":   k.chart_data,
        "notes":        k.notes,
        "created_at":   k.created_at.isoformat() if k.created_at else None,
        "updated_at":   k.updated_at.isoformat() if k.updated_at else None,
    }


@router.get("")
def list_kundlis(user: CurrentUser, db: Session = Depends(get_db)):
    return [_kundli_to_dict(k) for k in crud.list_kundlis(db, user.id)]


def _with_chart_fields(data: dict) -> dict:
    """Compute chart_data + big-three columns for a full birth-detail dict.
    Leaves them untouched (create: null) if calculation fails."""
    try:
        chart = BirthChart(
            data["name"], data["birth_year"], data["birth_month"], data["birth_day"],
            data["birth_hour"], data["birth_minute"], data["birth_city"], data["birth_nation"],
        )
        chart_dict = chart.to_dict()
        planets_list = chart_dict.get("planets", [])
        planets = {p["name"]: p for p in planets_list} if isinstance(planets_list, list) else planets_list
        data["sun_sign"]   = planets.get("Sun", {}).get("sign")
        data["moon_sign"]  = planets.get("Moon", {}).get("sign")
        data["ascendant"]  = chart_dict.get("ascendant")
        data["chart_data"] = chart_dict
    except Exception:
        import traceback; traceback.print_exc()
    return data


@router.post("", status_code=201)
def create_kundli(body: KundliCreate, user: CurrentUser, db: Session = Depends(get_db)):
    data = _with_chart_fields(body.model_dump())
    data["user_id"] = user.id
    k = crud.create_kundli(db, data)
    return _kundli_to_dict(k)


@router.get("/{kundli_id}")
def get_kundli(kundli_id: str, user: CurrentUser, db: Session = Depends(get_db)):
    k = crud.get_kundli(db, kundli_id, user.id)
    if not k:
        raise HTTPException(status_code=404, detail="Kundli not found")
    return _kundli_to_dict(k)


@router.patch("/{kundli_id}")
def update_kundli(kundli_id: str, body: KundliUpdate, user: CurrentUser, db: Session = Depends(get_db)):
    existing = crud.get_kundli(db, kundli_id, user.id)
    if not existing:
        raise HTTPException(status_code=404, detail="Kundli not found")

    data = {k: v for k, v in body.model_dump().items() if v is not None}
    if _BIRTH_FIELDS & data.keys():
        # birth details changed → recompute chart from merged record
        merged = {
            "name": data.get("name", existing.name),
            **{f: data.get(f, getattr(existing, f)) for f in _BIRTH_FIELDS},
        }
        data.update({k: v for k, v in _with_chart_fields(merged).items()
                     if k in ("sun_sign", "moon_sign", "ascendant", "chart_data")})

    k = crud.update_kundli(db, kundli_id, data, user.id)
    return _kundli_to_dict(k)


@router.delete("/{kundli_id}", status_code=204)
def delete_kundli(kundli_id: str, user: CurrentUser, db: Session = Depends(get_db)):
    if not crud.delete_kundli(db, kundli_id, user.id):
        raise HTTPException(status_code=404, detail="Kundli not found")
