from datetime import date as date_cls, datetime, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from ..db import get_db
from ..db import crud
from ..core.cities import lookup_city, search_cities
from .timing_place import resolve_timing_place, validate_timezone
from ..core.vedic import LocationError
from ..core.vedic import festivals
from ..core.vedic.panchanga_day import DAY_QUALITY_NOTE, daily_panchanga, day_quality, personal_panchanga
from ..core.vedic.chart import VedicChart
from ..core.vedic.constants import NAKSHATRAS
from ..core.vedic.nakshatra import nakshatra_of
from ..core.vedic.positions import sign_index
from .auth import CurrentUser

router = APIRouter(prefix="/api/v1/panchanga", tags=["panchanga"])


def _parse_date(date_str: Optional[str], tz_str: str) -> tuple[int, int, int]:
    if date_str:
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
        return d.year, d.month, d.day
    now = datetime.now(ZoneInfo(tz_str))
    return now.year, now.month, now.day


def _validate_timezone(tz_str: Optional[str], fallback: str) -> str:
    # Same rule as the personal routes (timing_place.validate_timezone): an
    # unreadable zone from the phone falls back to the city's own clock.
    return validate_timezone(tz_str, fallback)


@router.get("/cities")
def panchanga_cities(q: str = "", limit: int = Query(200, ge=1, le=300)):
    return search_cities(q, limit)


@router.get("/today")
def panchanga_today(
    city: str = Query(..., description="City name, e.g. Rajahmundry"),
    nation: str = "IN",
    date: Optional[str] = Query(None, description="YYYY-MM-DD; default: today in the viewer timezone"),
    timezone: Optional[str] = Query(None, description="Viewer IANA timezone, e.g. Asia/Singapore"),
):
    geo = lookup_city(city, nation)
    if not geo:
        raise HTTPException(status_code=422, detail=f"City {city!r} not in offline database.")
    lat, lng, tz_str = geo
    display_tz = _validate_timezone(timezone, tz_str)
    y, m, d = _parse_date(date, display_tz)
    try:
        return daily_panchanga(y, m, d, city, nation, lat, lng, tz_str, display_tz)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/{kundli_id}/today")
def personal_panchanga_today(
    kundli_id: str,
    user: CurrentUser,
    date: Optional[str] = None,
    city: Optional[str] = Query(None, description="Override location; default kundli birth city"),
    nation: Optional[str] = None,
    timezone: Optional[str] = Query(None, description="Viewer IANA timezone, e.g. Asia/Singapore"),
    db: Session = Depends(get_db),
):
    k = crud.get_kundli(db, kundli_id, user.id)
    if not k:
        raise HTTPException(status_code=404, detail="Kundli not found")

    place = resolve_timing_place(k, timezone, city, nation)
    y, m, d = _parse_date(date, place.today_tz)

    try:
        payload = daily_panchanga(y, m, d, place.city, place.nation, place.lat, place.lng,
                                  place.tz_str)
        payload["place"] = {**payload["place"], **place.as_payload()}
        ayanamsha, node_type = crud.chart_convention(db, user.id)
        chart = VedicChart(k.name, k.birth_year, k.birth_month, k.birth_day,
                           k.birth_hour, k.birth_minute, k.birth_city, k.birth_nation,
                           ayanamsha=ayanamsha, node_type=node_type)
    except (LocationError, ValueError, OverflowError) as e:
        raise HTTPException(status_code=422, detail=str(e))

    moon_lon = chart.positions["Moon"]["lon"]
    payload["personal"] = personal_panchanga(
        payload,
        janma_nakshatra_index=nakshatra_of(moon_lon)["index"],
        janma_rashi_index=sign_index(moon_lon),
        ghatak_moon_sign=sign_index(moon_lon),
    )
    payload["personal"]["janma"] = {
        "nakshatra": nakshatra_of(moon_lon)["name"],
        "rashi": chart.avkahada()["rashi"],
    }
    return payload


@lru_cache(maxsize=32)
def _moon_at_sunrise(year: int, city: str, nation: str) -> dict:
    return festivals.moon_signs(year, city=city, nation=nation)


@router.get("/{kundli_id}/month")
def personal_month(
    kundli_id: str,
    user: CurrentUser,
    from_date: str = Query(..., description="YYYY-MM-DD, usually the 1st of the month"),
    days: int = Query(31, ge=1, le=42),
    city: Optional[str] = Query(None, description="Override location; default as /today"),
    nation: Optional[str] = None,
    timezone: Optional[str] = Query(None, description="Viewer IANA timezone, e.g. Asia/Singapore"),
    db: Session = Depends(get_db),
):
    """Good / mixed / take-care for each day, for tinting the month grid (U7)."""
    k = crud.get_kundli(db, kundli_id, user.id)
    if not k:
        raise HTTPException(status_code=404, detail="Kundli not found")
    try:
        start = datetime.strptime(from_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="from_date must be YYYY-MM-DD")
    end = start + timedelta(days=days - 1)
    if not (1900 <= start.year and end.year <= 2100):
        raise HTTPException(status_code=400, detail="from_date out of range")

    place = resolve_timing_place(k, timezone, city, nation)
    try:
        ayanamsha, node_type = crud.chart_convention(db, user.id)
        chart = VedicChart(k.name, k.birth_year, k.birth_month, k.birth_day,
                           k.birth_hour, k.birth_minute, k.birth_city, k.birth_nation,
                           ayanamsha=ayanamsha, node_type=node_type)
        sunrise: dict = {}
        for year in sorted({start.year, end.year}):
            sunrise.update(_moon_at_sunrise(year, place.city, place.nation))
    except (LocationError, ValueError, OverflowError) as e:
        raise HTTPException(status_code=422, detail=str(e))

    moon_lon = chart.positions["Moon"]["lon"]
    janma_nak, janma_rashi = nakshatra_of(moon_lon)["index"], sign_index(moon_lon)
    out = []
    day = start
    while day <= end:
        moon = sunrise.get(day)
        if moon is not None:
            out.append({"date": day.isoformat(), **day_quality(moon[0], moon[1], janma_nak, janma_rashi)})
        day += timedelta(days=1)
    return {
        "from_date": start.isoformat(),
        "to_date": end.isoformat(),
        "place": place.as_payload(),
        "note": DAY_QUALITY_NOTE,
        "days": out,
    }
