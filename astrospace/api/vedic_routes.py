from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from ..db import get_db
from ..db import crud
from ..core.cities import city_for_timezone, lookup_city
from ..core.vedic import VedicChart, LocationError
from ..core.vedic.compatibility import gun_milan
from ..core.vedic.vargas import VARGA_FUNCTIONS
from .auth import CurrentUser

router = APIRouter(prefix="/api/v1/vedic", tags=["vedic"])


class VedicBirthInfo(BaseModel):
    name: str
    year: int
    month: int
    day: int
    hour: int = 12
    minute: int = 0
    city: Optional[str] = None
    nation: str = "IN"
    lat: Optional[float] = None
    lng: Optional[float] = None
    tz_str: Optional[str] = None
    ayanamsha: str = "lahiri"
    node_type: str = "mean"


def _chart_from_kundli(k, ayanamsha: str = "lahiri", node_type: str = "mean") -> VedicChart:
    try:
        return VedicChart(
            k.name, k.birth_year, k.birth_month, k.birth_day,
            k.birth_hour, k.birth_minute, k.birth_city, k.birth_nation,
            ayanamsha=ayanamsha, node_type=node_type,
        )
    except LocationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except (ValueError, OverflowError) as e:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid birth details on this kundli "
                   f"({k.birth_year}-{k.birth_month}-{k.birth_day} "
                   f"{k.birth_hour}:{k.birth_minute}): {e}. "
                   "Edit the kundli to fix the date (DD/MM/YYYY order).",
        )


def _get_kundli(db: Session, kundli_id: str, user_id: str):
    k = crud.get_kundli(db, kundli_id, user_id)
    if not k:
        raise HTTPException(status_code=404, detail="Kundli not found")
    return k


def _validate_timezone(tz_str: Optional[str], fallback: str) -> str:
    if not tz_str:
        return fallback
    try:
        ZoneInfo(tz_str)
    except Exception:
        raise HTTPException(status_code=400, detail="timezone must be a valid IANA timezone")
    return tz_str


def _reading_calendar_marker(r) -> dict:
    rating_labels = {
        1: "missed",
        2: "not applicable",
        3: "partly accurate",
        4: "mostly accurate",
        5: "accurate",
    }
    return {
        "id": r.id,
        "reading_type": r.reading_type,
        "period_label": r.period_label,
        "generated_local_date": r.generated_local_date,
        "version": r.version or 1,
        "deviation_score": r.deviation_score,
        "deviation_band": (r.deviation_summary or {}).get("band"),
        "user_rating": r.user_rating,
        "feedback_status": rating_labels.get(r.user_rating, "pending validation"),
        "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
        "generated_at": r.generated_at.isoformat() if r.generated_at else None,
    }


def _claim_calendar_marker(c) -> dict:
    return {
        "id": c.id,
        "reading_id": c.reading_id,
        "reading_type": c.reading_type,
        "period_label": c.period_label,
        "target_start_date": c.target_start_date,
        "target_end_date": c.target_end_date,
        "category": c.category,
        "claim_text": c.claim_text,
        "confidence": c.confidence,
        "status": c.status,
        "reviewed_at": c.reviewed_at.isoformat() if c.reviewed_at else None,
    }


def _attach_readings_to_calendar(payload: dict, db: Session, kundli_id: str, user_id: str) -> dict:
    readings = crud.get_readings_for_calendar(
        db,
        kundli_id,
        user_id,
        payload["start_date"],
        payload["end_date"],
    )
    readings_by_date: dict[str, list[dict]] = {}
    reading_events = []
    for reading in readings:
        date = reading.generated_local_date
        if not date:
            continue
        marker = _reading_calendar_marker(reading)
        readings_by_date.setdefault(date, []).append(marker)
        event = {
            "date": date,
            "category": "reading",
            "title": f"{reading.reading_type.title()} reading v{reading.version or 1}",
            "detail": (
                f"{reading.period_label or 'Generated AI prediction'} · "
                f"{marker['feedback_status']}"
            ),
            "tone": "neutral",
            "strength": 55,
            "meta": {
                "reading_id": reading.id,
                "version": reading.version or 1,
                "deviation_score": reading.deviation_score,
                "deviation_band": marker["deviation_band"],
                "user_rating": reading.user_rating,
            },
        }
        reading_events.append(event)
        payload.setdefault("by_date", {}).setdefault(date, []).append(event)

    payload["readings_by_date"] = readings_by_date
    payload.setdefault("current", {})["readings"] = readings_by_date.get(payload["start_date"], [])

    claims = crud.get_prediction_claims(
        db,
        kundli_id,
        user_id,
        start_date=payload["start_date"],
        end_date=payload["end_date"],
        limit=300,
    )
    claims_by_date: dict[str, list[dict]] = {}
    claim_events = []
    for claim in claims:
        date = claim.target_start_date or claim.generated_local_date
        if not date:
            continue
        marker = _claim_calendar_marker(claim)
        claims_by_date.setdefault(date, []).append(marker)
        event = {
            "date": date,
            "category": "prediction",
            "title": f"{claim.category.title()} claim · {claim.status.replace('_', ' ')}",
            "detail": claim.claim_text[:140],
            "tone": "neutral",
            "strength": int((claim.confidence or 0.5) * 100),
            "meta": {
                "claim_id": claim.id,
                "reading_id": claim.reading_id,
                "status": claim.status,
                "target_end_date": claim.target_end_date,
            },
        }
        claim_events.append(event)
        payload.setdefault("by_date", {}).setdefault(date, []).append(event)

    payload["prediction_claims_by_date"] = claims_by_date
    payload.setdefault("current", {})["prediction_claims"] = claims_by_date.get(payload["start_date"], [])
    payload.setdefault("events", []).extend(reading_events)
    payload.setdefault("events", []).extend(claim_events)
    payload["events"].sort(key=lambda event: (event["date"], -event.get("strength", 0), event["category"]))
    return payload


@router.post("/chart")
def compute_chart(b: VedicBirthInfo):
    """Full Vedic chart from raw birth details (no DB record needed)."""
    try:
        chart = VedicChart(b.name, b.year, b.month, b.day, b.hour, b.minute,
                           b.city, b.nation, b.lat, b.lng, b.tz_str,
                           b.ayanamsha, b.node_type)
    except LocationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return chart.to_dict()


@router.get("/{kundli_id}/all")
def full_vedic_chart(
    kundli_id: str,
    user: CurrentUser,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    return _chart_from_kundli(_get_kundli(db, kundli_id, user.id), ayanamsha, node_type).to_dict()


@router.get("/{kundli_id}/avkahada")
def avkahada(kundli_id: str, user: CurrentUser, db: Session = Depends(get_db)):
    chart = _chart_from_kundli(_get_kundli(db, kundli_id, user.id))
    return {
        "meta": chart.meta(),
        "avkahada": chart.avkahada(),
        "ghatak": chart.ghatak(),
        "favourable": chart.favourable(),
    }


@router.get("/{kundli_id}/panchanga")
def panchanga(kundli_id: str, user: CurrentUser, db: Session = Depends(get_db)):
    return _chart_from_kundli(_get_kundli(db, kundli_id, user.id)).panchanga


@router.get("/{kundli_id}/dashas")
def dashas(
    kundli_id: str,
    user: CurrentUser,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    return _chart_from_kundli(_get_kundli(db, kundli_id, user.id), ayanamsha, node_type).dashas()


@router.get("/{kundli_id}/ashtakavarga")
def ashtakavarga(
    kundli_id: str,
    user: CurrentUser,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    return _chart_from_kundli(_get_kundli(db, kundli_id, user.id), ayanamsha, node_type).ashtakavarga()


@router.get("/{kundli_id}/shadbala")
def shadbala(
    kundli_id: str,
    user: CurrentUser,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    return _chart_from_kundli(_get_kundli(db, kundli_id, user.id), ayanamsha, node_type).shadbala()


@router.get("/{kundli_id}/planetary-conditions")
def planetary_conditions(
    kundli_id: str,
    user: CurrentUser,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    return _chart_from_kundli(_get_kundli(db, kundli_id, user.id), ayanamsha, node_type).planetary_conditions()


@router.get("/{kundli_id}/doshas")
def doshas(
    kundli_id: str,
    user: CurrentUser,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    return _chart_from_kundli(_get_kundli(db, kundli_id, user.id), ayanamsha, node_type).doshas()


@router.get("/{kundli_id}/yogas")
def yogas(
    kundli_id: str,
    user: CurrentUser,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    return _chart_from_kundli(_get_kundli(db, kundli_id, user.id), ayanamsha, node_type).yogas()


@router.get("/{kundli_id}/yogas-doshas")
def yogas_doshas(
    kundli_id: str,
    user: CurrentUser,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    chart = _chart_from_kundli(_get_kundli(db, kundli_id, user.id), ayanamsha, node_type)
    return {"yogas": chart.yogas(), "doshas": chart.doshas()}


@router.get("/{kundli_id}/jaimini")
def jaimini(
    kundli_id: str,
    user: CurrentUser,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    return _chart_from_kundli(_get_kundli(db, kundli_id, user.id), ayanamsha, node_type).jaimini()


@router.get("/{kundli_id}/special-lagnas")
def special_lagnas(
    kundli_id: str,
    user: CurrentUser,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    return _chart_from_kundli(_get_kundli(db, kundli_id, user.id), ayanamsha, node_type).special_lagnas()


@router.get("/{kundli_id}/masa")
def masa(
    kundli_id: str,
    user: CurrentUser,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    return _chart_from_kundli(_get_kundli(db, kundli_id, user.id), ayanamsha, node_type).masa()


@router.get("/{kundli_id}/yogini-dashas")
def yogini_dashas(
    kundli_id: str,
    user: CurrentUser,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    return _chart_from_kundli(_get_kundli(db, kundli_id, user.id), ayanamsha, node_type).yogini_dashas()


@router.get("/{kundli_id}/transit-context")
def transit_context(
    kundli_id: str,
    user: CurrentUser,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    return _chart_from_kundli(_get_kundli(db, kundli_id, user.id), ayanamsha, node_type).transit_context()


@router.get("/{kundli_id}/transits")
def transits(
    kundli_id: str,
    user: CurrentUser,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    return _chart_from_kundli(_get_kundli(db, kundli_id, user.id), ayanamsha, node_type).transits()


@router.get("/{kundli_id}/gocharam")
def gocharam(
    kundli_id: str,
    user: CurrentUser,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    return _chart_from_kundli(_get_kundli(db, kundli_id, user.id), ayanamsha, node_type).gocharam()


@router.get("/{kundli_id}/calendar-intelligence")
def calendar_intelligence(
    kundli_id: str,
    user: CurrentUser,
    days: int = Query(30, ge=1, le=60),
    timezone: Optional[str] = Query(None, description="Viewer IANA timezone"),
    city: Optional[str] = Query(None, description="Optional panchanga place override"),
    nation: Optional[str] = None,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    k = _get_kundli(db, kundli_id, user.id)
    chart = _chart_from_kundli(k, ayanamsha, node_type)
    display_tz = _validate_timezone(timezone, chart.moment.tz_str)
    viewer_city = city_for_timezone(display_tz) if timezone and not city else None
    loc_city = city or (viewer_city[0] if viewer_city else k.birth_city)
    loc_nation = nation or (viewer_city[1] if viewer_city else k.birth_nation)
    geo = lookup_city(loc_city, loc_nation)
    if not geo:
        raise HTTPException(status_code=422, detail=f"City {loc_city!r} not in offline database.")
    lat, lng, tz_str = geo
    as_of = datetime.now(ZoneInfo(display_tz))
    payload = chart.calendar_intelligence(
        as_of=as_of,
        city=loc_city,
        nation=loc_nation,
        lat=lat,
        lng=lng,
        tz_str=tz_str,
        display_tz_str=display_tz,
        days=days,
    )
    return _attach_readings_to_calendar(payload, db, kundli_id, user.id)


@router.get("/{kundli_id}/compatibility/{partner_id}")
def compatibility(
    kundli_id: str,
    partner_id: str,
    user: CurrentUser,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    chart_a = _chart_from_kundli(_get_kundli(db, kundli_id, user.id), ayanamsha, node_type)
    chart_b = _chart_from_kundli(_get_kundli(db, partner_id, user.id), ayanamsha, node_type)
    return gun_milan(chart_a, chart_b)


@router.get("/{kundli_id}/vargas")
def all_vargas(
    kundli_id: str,
    user: CurrentUser,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    chart = _chart_from_kundli(_get_kundli(db, kundli_id, user.id), ayanamsha, node_type)
    return {"lagna": chart.lagna_details(), "vargas": chart.all_varga_charts(),
            "dignities": chart.dignities()}


@router.get("/{kundli_id}/d/{n}")
def varga_chart(
    kundli_id: str,
    n: int,
    user: CurrentUser,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    varga = f"D{n}"
    if varga not in VARGA_FUNCTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown varga D{n}; available: {sorted(VARGA_FUNCTIONS)}",
        )
    return _chart_from_kundli(_get_kundli(db, kundli_id, user.id), ayanamsha, node_type).varga_chart(varga)
