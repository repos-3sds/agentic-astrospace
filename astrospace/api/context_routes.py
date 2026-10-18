import copy
from datetime import date, datetime, timezone as dt_timezone
from functools import lru_cache
from typing import Literal, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import ratelimit
from ..agents.daily_brief_agent import daily_brief_enabled
from ..context.daily_brief_store import ensure_brief
from ..context import KeywordRouter, assemble, daily_guidance, domain_ids
from .timing_place import resolve_timing_place
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



# "Now" for the daily guidance is rounded down to this many minutes. The
# cache key below includes `as_of`, and with the raw clock (microseconds) it
# never hit twice. Why not the hour or the date: the Vedic day turns at
# sunrise and the Moon moves about half a degree an hour, so a coarse bucket
# would keep serving yesterday's day for up to an hour after sunrise. Fifteen
# minutes bounds that lag while letting every open of the app in the same
# quarter hour share one computation. An explicit `as_of` is left exact.
DAILY_GUIDANCE_BUCKET_MINUTES = 15


def _bucketed_now(tz: ZoneInfo) -> datetime:
    now = datetime.now(tz)
    return now.replace(minute=now.minute - now.minute % DAILY_GUIDANCE_BUCKET_MINUTES,
                       second=0, microsecond=0)


@lru_cache(maxsize=2048)
def _cached_daily_guidance(
    kundli_id: str,
    date_str: str,
    name: str, year: int, month: int, day: int, hour: int, minute: int,
    b_city: str, b_nation: str,
    ayanamsha: str, node_type: str,
    relation: str, as_of_iso: str,
    loc_city: str, loc_nation: str, loc_lat: float, loc_lng: float, loc_tz: str
):
    chart = VedicChart(
        name, year, month, day, hour, minute, b_city, b_nation,
        ayanamsha=ayanamsha, node_type=node_type
    )
    as_of = datetime.fromisoformat(as_of_iso)
    loc_kwargs = {}
    if loc_city:
        loc_kwargs = {"city": loc_city, "nation": loc_nation, "lat": loc_lat, "lng": loc_lng, "tz_str": loc_tz}
    return daily_guidance(chart, relation=relation, as_of=as_of, **loc_kwargs)



def _daily_payload(kundli, ayanamsha: str, node_type: str, as_of: Optional[datetime],
                   timezone: Optional[str], city: Optional[str], nation: Optional[str]) -> dict:
    _chart_from_kundli(kundli, ayanamsha, node_type)  # validates the birth details
    # One rule for "where" shared with Calendar Day, personal panchanga and
    # muhurta (api/timing_place.py); the viewer timezone only decides today.
    place = resolve_timing_place(kundli, timezone, city, nation)
    if as_of and as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=ZoneInfo(place.tz_str))
    if not as_of:
        as_of = _bucketed_now(ZoneInfo(place.today_tz))

    try:
        cached = _cached_daily_guidance(
            kundli.id,
            as_of.strftime("%Y-%m-%d"),
            kundli.name, kundli.birth_year, kundli.birth_month, kundli.birth_day,
            kundli.birth_hour, kundli.birth_minute, kundli.birth_city, kundli.birth_nation,
            ayanamsha, node_type,
            kundli.relation or "", as_of.isoformat(),
            place.city, place.nation, place.lat, place.lng, place.tz_str,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    # A deep copy: callers annotate and reshape the payload, and a change to
    # a nested value would otherwise reach every later reader of the cached
    # dict (audit I17).
    payload = copy.deepcopy(cached)
    payload["provenance"]["place"].update(place.as_payload())
    return payload


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
    return _daily_payload(kundli, ayanamsha, node_type, as_of, timezone, city, nation)


def _utc_today() -> date:
    return datetime.now(dt_timezone.utc).date()


def _may_write_brief(user_id: str, payload: dict) -> bool:
    """On open, only today's brief (yesterday or tomorrow allowed for zones
    either side of UTC) is worth a model call, and only within the account's
    ceiling. Every query parameter feeds the brief's cache key, so without
    this a loop over `as_of` dates or cities was one paid call per request.
    Other days get the templated brief, which the apps already show."""
    try:
        day = date.fromisoformat(payload["date"])
    except (KeyError, TypeError, ValueError):
        return False
    if abs((day - _utc_today()).days) > 1:
        return False
    return ratelimit.take(user_id, "brief")


@router.get("/{kundli_id}/daily/brief")
def daily_brief(
    kundli_id: str,
    user: CurrentUser,
    db: Session = Depends(get_db),
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    as_of: Optional[datetime] = None,
    timezone: Optional[str] = Query(None, description="Viewer or selected panchanga timezone"),
    city: Optional[str] = Query(None, description="Optional panchanga place override"),
    nation: Optional[str] = None,
    tone: Literal["gentle", "direct"] = "gentle",
    mode: Literal["guided", "balanced", "practitioner"] = "balanced",
):
    """Today's brief in the agent's words, over the same signals as /daily.

    Normally already written by the notification worker and read from the
    store (context/daily_brief_store.py). Answers 200 with `brief: null` when
    the agent is off or could not write a safe brief: the app already shows
    the templated brief and keeps it.
    """
    kundli = crud.get_kundli(db, kundli_id, user.id)
    if not kundli:
        raise HTTPException(status_code=404, detail="Kundli not found")
    payload = _daily_payload(kundli, ayanamsha, node_type, as_of, timezone, city, nation)
    base = {"date": payload["date"], "valid_until": payload.get("valid_until")}
    if not daily_brief_enabled():
        return {**base, "source": "template", "brief": None}
    value, written_now = ensure_brief(db, kundli, payload, tone=tone, mode=mode,
                                      ayanamsha=ayanamsha, node_type=node_type, trigger="on_open",
                                      may_write=lambda: _may_write_brief(user.id, payload))
    if not value:
        return {**base, "source": "template", "brief": None}
    return {**base, **value, "cached": not written_now}


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
