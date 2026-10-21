"""The routers' side of context/timing_place.py: the same rule, a 422 on a
city the offline table lacks. Workers import the context module directly."""
from fastapi import HTTPException

from ..context.timing_place import (  # noqa: F401 (re-exported for the routers)
    SOURCE_BIRTH_CITY,
    SOURCE_SELECTED,
    SOURCE_VIEWER_TIMEZONE,
    PlaceNotFound,
    TimingPlace,
    validate_timezone,
)
from ..context.timing_place import resolve_timing_place as _resolve


def resolve_timing_place(kundli, timezone: str | None = None,
                         city: str | None = None, nation: str | None = None) -> TimingPlace:
    try:
        return _resolve(kundli, timezone, city, nation)
    except PlaceNotFound as e:
        raise HTTPException(status_code=422, detail=str(e))
