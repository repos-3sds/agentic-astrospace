"""Today's Subhashita.

Thin wrapper over :mod:`astrospace.core.subhashita`. Open to everyone: the
corpus is static, a lookup costs nothing, and a verse shared to a status may
be opened by someone without an account.

The reader's own calendar date decides the verse, so the app sends it; the
server's UTC date would hand India the previous day's verse until 05:30.
"""
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Query

from ..core import subhashita

router = APIRouter(prefix="/api/v1/subhashita", tags=["subhashita"])

MAX_DAYS = 31


@router.get("/today")
def today(day: date | None = Query(None, alias="date")) -> dict:
    return {**subhashita.for_day(day or datetime.now(timezone.utc).date()), "title": subhashita.TITLE}


@router.get("")
def upcoming(
    start: date | None = None,
    days: int = Query(14, ge=1, le=MAX_DAYS),
) -> dict:
    """A run of days, for the home-screen widget to keep without the network."""
    first = start or datetime.now(timezone.utc).date()
    return {
        "title": subhashita.TITLE,
        "items": [subhashita.for_day(first + timedelta(days=n)) for n in range(days)],
    }
