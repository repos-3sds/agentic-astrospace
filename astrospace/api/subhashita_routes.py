"""Today's Subhashita.

Thin wrapper over :mod:`astrospace.core.subhashita`. Open without sign-in:
the corpus is static and a lookup costs nothing. A signed-in reader gets
their own rotation; a missing or bad token gets the shared one, not a 401.

The reader's own calendar date decides the verse, so the app sends it.
Without one, India's date is used (most readers), not the server's UTC date,
which would hand India the previous day's verse until 05:30.
"""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from ..core import subhashita
from .auth import supabase_configured, verify_access_token

router = APIRouter(prefix="/api/v1/subhashita", tags=["subhashita"])

MAX_DAYS = 31
EARLIEST, LATEST = date(1900, 1, 1), date(2100, 12, 31)


def _day(value: date | None) -> date:
    day = value or datetime.now(ZoneInfo("Asia/Kolkata")).date()
    if not EARLIEST <= day <= LATEST:
        raise HTTPException(status_code=400, detail="date must be between 1900 and 2100")
    return day


def reader_id(authorization: Annotated[str | None, Header(alias="Authorization")] = None) -> str | None:
    """The signed-in account, if the request carries a valid token."""
    if not supabase_configured() or not authorization or not authorization.lower().startswith("bearer "):
        return None
    try:
        return verify_access_token(authorization.split(" ", 1)[1].strip()).id
    except Exception:  # an expired session still gets a verse
        return None


@router.get("/today")
def today(day: date | None = Query(None, alias="date"),
          reader: str | None = Depends(reader_id)) -> dict:
    return {**subhashita.for_day(_day(day), reader), "title": subhashita.TITLE}


@router.get("")
def upcoming(
    start: date | None = None,
    days: int = Query(14, ge=1, le=MAX_DAYS),
    reader: str | None = Depends(reader_id),
) -> dict:
    """A run of days, for the home-screen widget to keep without the network."""
    first = _day(start)
    return {
        "title": subhashita.TITLE,
        "items": [subhashita.for_day(first + timedelta(days=n), reader) for n in range(days)],
    }
