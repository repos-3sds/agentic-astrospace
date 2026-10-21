"""Today's guidance payload for one profile, shared by the API and the worker.

The /daily and /daily/brief routes and the notification worker's daily
briefs all need the same payload, and the worker used to import a private
function out of api/context_routes.py to get it (audit I8). It lives here
now, free of FastAPI: a bad birth record or an unknown city raises
DailyGuidanceError, and the router maps that to a 422.
"""
import copy
from datetime import datetime
from functools import lru_cache
from typing import Optional
from zoneinfo import ZoneInfo

from ..core.vedic import LocationError, VedicChart
from .daily import daily_guidance
from .timing_place import PlaceNotFound, resolve_timing_place


class DailyGuidanceError(ValueError):
    """The profile's birth details or the chosen place cannot be computed."""


# "Now" for the daily guidance is rounded down to this many minutes. The
# cache key below includes `as_of`, and with the raw clock (microseconds) it
# never hit twice. Why not the hour or the date: the Vedic day turns at
# sunrise and the Moon moves about half a degree an hour, so a coarse bucket
# would keep serving yesterday's day for up to an hour after sunrise. Fifteen
# minutes bounds that lag while letting every open of the app in the same
# quarter hour share one computation. An explicit `as_of` is left exact.
DAILY_GUIDANCE_BUCKET_MINUTES = 15


def bucketed_now(tz: ZoneInfo) -> datetime:
    now = datetime.now(tz)
    return now.replace(minute=now.minute - now.minute % DAILY_GUIDANCE_BUCKET_MINUTES,
                       second=0, microsecond=0)


@lru_cache(maxsize=2048)
def cached_daily_guidance(
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


def _check_birth_details(kundli, ayanamsha: str, node_type: str) -> None:
    try:
        VedicChart(
            kundli.name, kundli.birth_year, kundli.birth_month, kundli.birth_day,
            kundli.birth_hour, kundli.birth_minute, kundli.birth_city, kundli.birth_nation,
            ayanamsha=ayanamsha, node_type=node_type,
        )
    except LocationError as e:
        raise DailyGuidanceError(str(e)) from e
    except (ValueError, OverflowError) as e:
        raise DailyGuidanceError(f"Invalid birth details: {e}") from e


def daily_payload(kundli, ayanamsha: str, node_type: str, as_of: Optional[datetime],
                  timezone: Optional[str], city: Optional[str], nation: Optional[str]) -> dict:
    _check_birth_details(kundli, ayanamsha, node_type)
    # One rule for "where" shared with Calendar Day, personal panchanga and
    # muhurta (context/timing_place.py); the viewer timezone only decides today.
    try:
        place = resolve_timing_place(kundli, timezone, city, nation)
    except PlaceNotFound as e:
        raise DailyGuidanceError(str(e)) from e
    if as_of and as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=ZoneInfo(place.tz_str))
    if not as_of:
        as_of = bucketed_now(ZoneInfo(place.today_tz))

    try:
        cached = cached_daily_guidance(
            kundli.id,
            as_of.strftime("%Y-%m-%d"),
            kundli.name, kundli.birth_year, kundli.birth_month, kundli.birth_day,
            kundli.birth_hour, kundli.birth_minute, kundli.birth_city, kundli.birth_nation,
            ayanamsha, node_type,
            kundli.relation or "", as_of.isoformat(),
            place.city, place.nation, place.lat, place.lng, place.tz_str,
        )
    except ValueError as e:
        raise DailyGuidanceError(str(e)) from e
    # A deep copy: callers annotate and reshape the payload, and a change to
    # a nested value would otherwise reach every later reader of the cached
    # dict (audit I17).
    payload = copy.deepcopy(cached)
    payload["provenance"]["place"].update(place.as_payload())
    return payload
