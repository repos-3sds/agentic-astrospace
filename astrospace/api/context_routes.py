from datetime import date, datetime, timezone as dt_timezone
from typing import Literal, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import ratelimit
from ..agents.daily_brief_agent import daily_brief_enabled
from ..context.daily_brief_store import ensure_brief
from ..context import KeywordRouter, assemble, domain_ids
from ..context.daily_service import DailyGuidanceError, daily_payload
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




def _daily_payload(kundli, ayanamsha: str, node_type: str, as_of: Optional[datetime],
                   timezone: Optional[str], city: Optional[str], nation: Optional[str]) -> dict:
    try:
        return daily_payload(kundli, ayanamsha, node_type, as_of, timezone, city, nation)
    except DailyGuidanceError as e:
        raise HTTPException(status_code=422, detail=str(e))


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
