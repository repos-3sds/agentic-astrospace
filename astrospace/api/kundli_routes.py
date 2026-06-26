from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from ..db import get_db, Kundli
from ..db import crud
from ..core.chart import BirthChart

router = APIRouter(prefix="/api/v1/kundlis", tags=["kundlis"])


class KundliCreate(BaseModel):
    name: str
    relation: str = "friend"
    birth_year: int
    birth_month: int
    birth_day: int
    birth_hour: int = 12
    birth_minute: int = 0
    birth_city: str
    birth_nation: str = "US"
    notes: Optional[str] = None


class KundliUpdate(BaseModel):
    name: Optional[str] = None
    relation: Optional[str] = None
    birth_hour: Optional[int] = None
    birth_minute: Optional[int] = None
    birth_city: Optional[str] = None
    birth_nation: Optional[str] = None
    notes: Optional[str] = None


def _kundli_to_dict(k: Kundli) -> dict:
    return {
        "id":           k.id,
        "name":         k.name,
        "relation":     k.relation,
        "birth_year":   k.birth_year,
        "birth_month":  k.birth_month,
        "birth_day":    k.birth_day,
        "birth_hour":   k.birth_hour,
        "birth_minute": k.birth_minute,
        "birth_city":   k.birth_city,
        "birth_nation": k.birth_nation,
        "sun_sign":     k.sun_sign,
        "moon_sign":    k.moon_sign,
        "ascendant":    k.ascendant,
        "chart_data":   k.chart_data,
        "notes":        k.notes,
        "created_at":   k.created_at.isoformat() if k.created_at else None,
        "updated_at":   k.updated_at.isoformat() if k.updated_at else None,
    }


@router.get("")
def list_kundlis(db: Session = Depends(get_db)):
    return [_kundli_to_dict(k) for k in crud.list_kundlis(db)]


@router.post("", status_code=201)
def create_kundli(body: KundliCreate, db: Session = Depends(get_db)):
    try:
        chart = BirthChart(
            body.name, body.birth_year, body.birth_month, body.birth_day,
            body.birth_hour, body.birth_minute, body.birth_city, body.birth_nation,
        )
        chart_dict = chart.to_dict()
        planets_list = chart_dict.get("planets", [])
        planets = {p["name"]: p for p in planets_list} if isinstance(planets_list, list) else planets_list
        data = body.model_dump()
        data["sun_sign"]   = planets.get("Sun", {}).get("sign")
        data["moon_sign"]  = planets.get("Moon", {}).get("sign")
        data["ascendant"]  = chart_dict.get("ascendant")
        data["chart_data"] = chart_dict
    except Exception as exc:
        import traceback; traceback.print_exc()
        data = body.model_dump()

    k = crud.create_kundli(db, data)
    return _kundli_to_dict(k)


@router.get("/{kundli_id}")
def get_kundli(kundli_id: str, db: Session = Depends(get_db)):
    k = crud.get_kundli(db, kundli_id)
    if not k:
        raise HTTPException(status_code=404, detail="Kundli not found")
    return _kundli_to_dict(k)


@router.patch("/{kundli_id}")
def update_kundli(kundli_id: str, body: KundliUpdate, db: Session = Depends(get_db)):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    k = crud.update_kundli(db, kundli_id, data)
    if not k:
        raise HTTPException(status_code=404, detail="Kundli not found")
    return _kundli_to_dict(k)


@router.delete("/{kundli_id}", status_code=204)
def delete_kundli(kundli_id: str, db: Session = Depends(get_db)):
    if not crud.delete_kundli(db, kundli_id):
        raise HTTPException(status_code=404, detail="Kundli not found")
