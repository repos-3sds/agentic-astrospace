"""Today's Subhashita.

Thin wrapper over :mod:`astrospace.core.subhashita`. Open without sign-in:
the corpus is static and a lookup costs nothing.

The reader's own calendar date decides the verse, so the app sends it.
Without one, India's date is used (most readers), not the server's UTC date,
which would hand India the previous day's verse until 05:30.
"""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query

from ..core import subhashita

router = APIRouter(prefix="/api/v1/subhashita", tags=["subhashita"])

MAX_DAYS = 31
EARLIEST, LATEST = date(1900, 1, 1), date(2100, 12, 31)


def _day(value: date | None) -> date:
    day = value or datetime.now(ZoneInfo("Asia/Kolkata")).date()
    if not EARLIEST <= day <= LATEST:
        raise HTTPException(status_code=400, detail="date must be between 1900 and 2100")
    return day


@router.get("/today")
def today(day: date | None = Query(None, alias="date")) -> dict:
    return {**subhashita.for_day(_day(day)), "title": subhashita.TITLE}


@router.get("")
def upcoming(
    start: date | None = None,
    days: int = Query(14, ge=1, le=MAX_DAYS),
) -> dict:
    """A run of days, for the home-screen widget to keep without the network."""
    first = _day(start)
    return {
        "title": subhashita.TITLE,
        "items": [subhashita.for_day(first + timedelta(days=n)) for n in range(days)],
    }
