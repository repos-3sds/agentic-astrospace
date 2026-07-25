"""Goal-based muhurta search.

Wraps :mod:`astrospace.core.vedic.muhurta`. Two things are deliberate here:

*Refer-out is a response, not a crash.* Health, legal and financial intents
raise :class:`~astrospace.core.vedic.muhurta.ExcludedGoalError`, which becomes
a 422 carrying a structured body the app renders as a refer-out card. The
client needs the domain to pick its wording, so it is sent as a field rather
than buried in a message string.

*Timings apply where the user is, not where they were born.* The location
defaults to the kundli's birth city but is overridable, because a muhurta is
useless if it is computed for the wrong sunrise.
"""
from datetime import date as date_cls, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..core.vedic import LocationError, muhurta
from ..core.vedic.constants import NAKSHATRAS
from ..core.vedic.nakshatra import nakshatra_of
from ..core.vedic.positions import sign_index
from ..db import crud, get_db
from .auth import CurrentUser
from .vedic_routes import _chart_from_kundli

router = APIRouter(prefix="/api/v1/muhurta", tags=["muhurta"])


def _parse_date(value: str | None, field: str, default: date_cls) -> date_cls:
    if not value:
        return default
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail=f"{field} must be YYYY-MM-DD")


@router.get("/goals")
def muhurta_goals():
    """The goal picker's options, shaped for the ``muhurta_goals`` table."""
    return {"goals": muhurta.goal_catalog()}


@router.get("/{kundli_id}")
def find_muhurta(
    kundli_id: str,
    user: CurrentUser,
    goal: str = Query(..., description="A slug from /goals"),
    date_from: str | None = Query(None, description="YYYY-MM-DD; default today"),
    date_to: str | None = Query(None, description="YYYY-MM-DD; default +14 days"),
    city: str | None = Query(
        None, description="Where the timings apply; defaults to the birth city"
    ),
    nation: str | None = None,
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    kundli = crud.get_kundli(db, kundli_id, user.id)
    if not kundli:
        raise HTTPException(status_code=404, detail="Kundli not found")

    today = date_cls.today()
    start = _parse_date(date_from, "date_from", today)
    end = _parse_date(date_to, "date_to", start + timedelta(days=14))

    chart = _chart_from_kundli(kundli)
    moon_lon = chart.positions["Moon"]["lon"]
    moon_sign = sign_index(moon_lon)

    try:
        return muhurta.find(
            goal, start, end,
            janma_nakshatra_index=NAKSHATRAS.index(nakshatra_of(moon_lon)["name"]),
            janma_rashi_index=moon_sign,
            ghatak_moon_sign=moon_sign,
            city=city or kundli.birth_city,
            nation=nation or kundli.birth_nation or "IN",
            limit=limit,
        )
    except muhurta.ExcludedGoalError as e:
        # Not a failure — the product declines to time these, by design.
        raise HTTPException(status_code=422, detail={
            "kind": "refer_out",
            "domain": e.domain,
            "message": str(e),
        })
    except LocationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
