from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from ..db import get_db
from ..db import crud
from ..core.cities import city_for_timezone, lookup_city, search_cities
from ..core.vedic import LocationError
from ..core.vedic.panchanga_day import daily_panchanga, personal_panchanga
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
    if not tz_str:
        return fallback
    try:
        ZoneInfo(tz_str)
    except Exception:
        raise HTTPException(status_code=400, detail="timezone must be a valid IANA timezone")
    return tz_str


@router.get("/cities")
def panchanga_cities(q: str = "", limit: int = Query(80, ge=1, le=200)):
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

    display_tz = _validate_timezone(timezone, "")
    viewer_city = city_for_timezone(display_tz) if timezone and not city else None
    loc_city = city or (viewer_city[0] if viewer_city else k.birth_city)
    loc_nation = nation or (viewer_city[1] if viewer_city else k.birth_nation)
    geo = lookup_city(loc_city, loc_nation)
    if not geo:
        raise HTTPException(status_code=422, detail=f"City {loc_city!r} not in offline database.")
    lat, lng, tz_str = geo
    display_tz = _validate_timezone(timezone, tz_str)
    y, m, d = _parse_date(date, display_tz)

    try:
        payload = daily_panchanga(y, m, d, loc_city, loc_nation, lat, lng, tz_str, display_tz)
        chart = VedicChart(k.name, k.birth_year, k.birth_month, k.birth_day,
                           k.birth_hour, k.birth_minute, k.birth_city, k.birth_nation)
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
