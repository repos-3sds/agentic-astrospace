"""Hindu festival calendar.

Wraps :mod:`astrospace.core.vedic.festivals`. Festival dates genuinely depend
on where the sunrise is taken, so ``city``/``nation`` is required rather than
defaulted to a hidden location — a silent default would produce dates that
look authoritative and are wrong by a day.

A full-year scan walks ~400 days of panchanga, so responses are cached per
(year, place, filters) for the process lifetime. The inputs are calendrical:
the same arguments give the same answer forever.
"""
from datetime import date as date_cls, datetime, timedelta
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Query

from ..core.cities import city_for_timezone
from ..core.vedic import LocationError, festivals
from .auth import current_user

# Signed-in only: an uncached festival year is 15-50 s of server CPU, and
# anyone could ask for any city (regression 2026-10-17, L5).
router = APIRouter(
    prefix="/api/v1/festivals", tags=["festivals"],
    dependencies=[Depends(current_user)],
)

_REGIONS = {festivals.NORTH, festivals.SOUTH, festivals.PAN}
_MIN_YEAR, _MAX_YEAR = 1900, 2100


@lru_cache(maxsize=256)
def _occurrences(year: int, city: str, nation: str,
                 regions: tuple[str, ...] | None,
                 slugs: tuple[str, ...] | None) -> tuple[dict, ...]:
    rows = festivals.occurrences(
        year, city=city, nation=nation,
        regions=list(regions) if regions else None,
        slugs=list(slugs) if slugs else None,
    )
    return tuple(rows)


def _serialise(row: dict) -> dict:
    """Dates go out as ISO strings; everything else passes through.

    ``observance_note`` and ``is_convention_dependent`` are part of the
    payload on purpose — several festivals have no single correct date, and
    the app is expected to say so rather than pick one silently.
    """
    return {**row, "occurs_on": row["occurs_on"].isoformat()}


def _validate(year: int, regions: list[str] | None) -> tuple[str, ...] | None:
    if not _MIN_YEAR <= year <= _MAX_YEAR:
        raise HTTPException(
            status_code=400,
            detail=f"year must be between {_MIN_YEAR} and {_MAX_YEAR}",
        )
    if regions is None:
        return None
    unknown = set(regions) - _REGIONS
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"unknown region(s) {sorted(unknown)}; "
                   f"expected any of {sorted(_REGIONS)}",
        )
    return tuple(sorted(set(regions)))


def _resolve(year, city, nation, regions, slugs):
    try:
        return _occurrences(year, city, nation, regions,
                            tuple(sorted(set(slugs))) if slugs else None)
    except LocationError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/catalog")
def festival_catalog():
    """Festival definitions, shaped for the ``festivals`` table."""
    return {"festivals": festivals.catalog()}


@router.get("/year/{year}")
def festivals_for_year(
    year: int,
    city: str = Query(..., description="Where sunrise is taken, e.g. Chennai"),
    nation: str = "IN",
    regions: list[str] | None = Query(
        None, description="Filter: north, south, pan-india"
    ),
    slugs: list[str] | None = Query(None, description="Restrict to these slugs"),
):
    checked = _validate(year, regions)
    rows = _resolve(year, city, nation, checked, slugs)
    return {
        "year": year,
        "place": {"city": city, "nation": nation},
        "count": len(rows),
        "festivals": [_serialise(r) for r in rows],
    }


@lru_cache(maxsize=64)
def _moon_days(year: int, city: str, nation: str) -> tuple[dict, ...]:
    return tuple(festivals.moon_days(year, city=city, nation=nation))


@router.get("/moon-days")
def moon_days(
    city: str = Query(..., description="Where sunrise is taken, e.g. Chennai"),
    nation: str = "IN",
    from_date: str | None = Query(None, description="YYYY-MM-DD; default today"),
    days: int = Query(60, ge=1, le=120),
):
    """Full and new moon days ahead, for the home-screen widgets.

    The rule is the tithi at sunrise, which not every calendar uses, so the
    note goes out with the dates rather than implying one right answer.
    """
    if from_date:
        try:
            start = datetime.strptime(from_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="from_date must be YYYY-MM-DD")
    else:
        start = date_cls.today()
    end = start + timedelta(days=days)
    _validate(start.year, None)
    _validate(end.year, None)
    rows: list[dict] = []
    try:
        for year in sorted({start.year, end.year}):
            rows += _moon_days(year, city, nation)
    except LocationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {
        "from_date": start.isoformat(),
        "to_date": end.isoformat(),
        "place": {"city": city, "nation": nation},
        "is_convention_dependent": True,
        "observance_note": festivals.MOON_DAY_NOTE,
        "moon_days": [
            {"date": r["date"].isoformat(), "moon": r["moon"]}
            for r in rows if start <= r["date"] <= end
        ],
    }


@router.get("/upcoming")
def upcoming_festivals(
    city: str = Query(..., description="Where sunrise is taken, e.g. Chennai"),
    nation: str = "IN",
    from_date: str | None = Query(None, description="YYYY-MM-DD; default today"),
    days: int = Query(60, ge=1, le=365),
    regions: list[str] | None = Query(None),
    timezone: str | None = Query(
        None, description="The viewer's timezone, used when city is only the birth-city fallback"),
    city_is_fallback: bool = Query(
        False, description="city is the birth city, sent because no timing city is chosen"),
):
    # The same order the day timings use (timing_place.resolve_timing_place):
    # a chosen city, else the city for the phone's timezone, else the birth
    # city. Festivals took the birth city while the timings beside them came
    # from the phone's timezone (regression 2026-10-17, M6).
    if city_is_fallback and timezone:
        viewer_city = city_for_timezone(timezone)
        if viewer_city:
            city, nation = viewer_city[0], viewer_city[1]
    if from_date:
        try:
            start = datetime.strptime(from_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="from_date must be YYYY-MM-DD")
    else:
        start = date_cls.today()

    end = start + timedelta(days=days)
    checked = _validate(start.year, regions)
    _validate(end.year, None)

    # A window can straddle a year boundary; both years are cached separately.
    rows = list(_resolve(start.year, city, nation, checked, None))
    if end.year != start.year:
        rows += _resolve(end.year, city, nation, checked, None)

    window = [r for r in rows if start <= r["occurs_on"] <= end]
    window.sort(key=lambda r: (r["occurs_on"], r["slug"]))
    return {
        "from_date": start.isoformat(),
        "to_date": end.isoformat(),
        "place": {"city": city, "nation": nation},
        "count": len(window),
        "festivals": [_serialise(r) for r in window],
    }
