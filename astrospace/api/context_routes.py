from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..context import KeywordRouter, assemble, daily_guidance, domain_ids
from ..core.cities import city_for_timezone, lookup_city
from ..core.vedic import LocationError, VedicChart
from ..db import crud, get_db
from .auth import CurrentUser

router = APIRouter(prefix="/api/v1/context", tags=["context-engine"])


class ContextRequest(BaseModel):
    question: Optional[str] = Field(default=None, max_length=2000)
    domains: Optional[list[str]] = None
    include_gochara: bool = True
    as_of: Optional[datetime] = None
    ayanamsha: str = "lahiri"
    node_type: str = "mean"


def _chart_from_kundli(k, ayanamsha: str, node_type: str) -> VedicChart:
    try:
        return VedicChart(
            k.name,
            k.birth_year,
            k.birth_month,
            k.birth_day,
            k.birth_hour,
            k.birth_minute,
            k.birth_city,
            k.birth_nation,
            ayanamsha=ayanamsha,
            node_type=node_type,
        )
    except LocationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except (ValueError, OverflowError) as e:
        raise HTTPException(status_code=422, detail=f"Invalid birth details: {e}")


def _validate_timezone(tz_str: Optional[str], fallback: str) -> str:
    if not tz_str:
        return fallback
    try:
        ZoneInfo(tz_str)
    except Exception:
        raise HTTPException(status_code=400, detail="timezone must be a valid IANA timezone")
    return tz_str


@router.get("/{kundli_id}/daily")
def daily(
    kundli_id: str,
    user: CurrentUser,
    db: Session = Depends(get_db),
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    as_of: Optional[datetime] = None,
    timezone: Optional[str] = Query(None, description="Viewer or selected panchanga timezone"),
    city: Optional[str] = Query(None, description="Optional panchanga place override"),
    nation: Optional[str] = None,
):
    kundli = crud.get_kundli(db, kundli_id, user.id)
    if not kundli:
        raise HTTPException(status_code=404, detail="Kundli not found")
    chart = _chart_from_kundli(kundli, ayanamsha, node_type)
    display_tz = _validate_timezone(timezone, chart.moment.tz_str)
    viewer_city = city_for_timezone(display_tz) if timezone and not city else None
    loc_city = city or (viewer_city[0] if viewer_city else None)
    loc_nation = nation or (viewer_city[1] if viewer_city else None)
    loc_kwargs = {}
    if loc_city:
        geo = lookup_city(loc_city, loc_nation or kundli.birth_nation)
        if not geo:
            raise HTTPException(status_code=422, detail=f"City {loc_city!r} not in offline database.")
        lat, lng, tz_str = geo
        loc_kwargs = {
            "city": loc_city,
            "nation": loc_nation or kundli.birth_nation,
            "lat": lat,
            "lng": lng,
            "tz_str": tz_str,
        }
    if as_of and as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=ZoneInfo(loc_kwargs.get("tz_str", display_tz)))
    try:
        return daily_guidance(chart, relation=kundli.relation, as_of=as_of, **loc_kwargs)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/{kundli_id}")
def context_bundle(
    kundli_id: str,
    body: ContextRequest,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    kundli = crud.get_kundli(db, kundli_id, user.id)
    if not kundli:
        raise HTTPException(status_code=404, detail="Kundli not found")

    if body.domains:
        unknown = sorted(set(body.domains) - set(domain_ids()))
        if unknown:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown context domains: {unknown}. Options: {domain_ids()}",
            )
        domains = body.domains
        routing = {"method": "explicit", "primary": domains[0], "secondary": domains[1:]}
    elif body.question:
        decision = KeywordRouter().route(body.question)
        domains = decision.domains
        routing = {
            "method": decision.method,
            "primary": decision.primary,
            "secondary": list(decision.secondary),
            "confidence": decision.confidence,
            "matched_terms": list(decision.matched_terms),
        }
    else:
        raise HTTPException(status_code=400, detail="Provide either question or domains.")

    chart = _chart_from_kundli(kundli, body.ayanamsha, body.node_type)
    as_of = body.as_of
    if as_of and as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=ZoneInfo(chart.moment.tz_str))

    return {
        "routing": routing,
        "bundle": assemble(
            chart,
            domains,
            question=body.question,
            include_gochara=body.include_gochara,
            as_of=as_of,
        ),
    }
