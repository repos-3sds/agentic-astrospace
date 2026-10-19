"""Remedy recommendations for a saved kundli.

A thin layer over :mod:`astrospace.core.vedic.remedies`. The one thing this
router must not do is flatten the engine's framing: every remedy carries
``is_convention_dependent`` and a ``tradition_source``, and every dosha
trigger carries "This is a flag, not a verdict." Those fields are the
product's safety contract (design_principles.md §4 and §6), so they are
passed through verbatim rather than summarised into a score.

``include_manglik`` defaults to false: Manglik is a marriage-compatibility
flag, not a general graha-shanti trigger, so it must not surface as a
generic remedy card. Callers building a compatibility or dosha-detail screen
should pass ``include_manglik=true`` explicitly.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..core.vedic import remedies, remedy_plan
from ..db import crud, get_db
from ..entitlements import plan_lock
from .auth import CurrentUser
from .vedic_routes import _chart_from_kundli

router = APIRouter(prefix="/api/v1/remedies", tags=["remedies"])


@router.get("/catalog")
def remedy_catalog():
    """The full graha-remedy catalog, shaped for the ``remedies`` table."""
    return {"remedies": remedies.catalog()}


@router.get("/{kundli_id}")
def remedies_for_kundli(
    kundli_id: str,
    user: CurrentUser,
    include_costly: bool = Query(
        True, description="Set false to omit gemstones, which carry a real cost."
    ),
    include_manglik: bool = Query(
        False,
        description=(
            "Set true only for compatibility/dosha-detail screens. Manglik is "
            "a marriage-matching flag, not a generic remedy trigger, so the "
            "default feed never includes it."
        ),
    ),
    limit: int | None = Query(None, ge=1, le=20),
    db: Session = Depends(get_db),
):
    kundli = crud.get_kundli(db, kundli_id, user.id)
    if not kundli:
        raise HTTPException(status_code=404, detail="Kundli not found")

    chart = _chart_from_kundli(kundli)
    return remedies.recommend(
        chart.positions,
        chart.lagna_lon,
        # The active mahadasha/antardasha lords rank first — a remedy is most
        # relevant while its planet is actually running.
        dasha=chart.dashas(),
        include_costly=include_costly,
        include_manglik=include_manglik,
        limit=limit,
    )


@router.get("/{kundli_id}/plan")
def remedy_plan_for_kundli(
    kundli_id: str,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Two or three remedies for this profile: its running period, its main
    life area, and one flag only when the chart actually has one."""
    kundli = crud.get_kundli(db, kundli_id, user.id)
    if not kundli:
        raise HTTPException(status_code=404, detail="Kundli not found")

    chart = _chart_from_kundli(kundli)
    plan = remedy_plan.remedy_plan(chart.positions, chart.lagna_lon, chart.dashas())
    if plan_lock(db, user.id, "remedies.full") is not None:
        plan = _free_plan(plan)
    return plan


def _free_plan(plan: dict) -> dict:
    """Free keeps the first remedy and any dosha's, one practice each.

    Mirrors `shownGroups` in ui/src/app/features/mobile/remedies/remedies.component.ts.
    A flagged dosha's practice is never behind a plan, so that a remedy never
    reads as paying to remove a dosha; `locked_practices` counts the rest.
    """
    groups = plan.get("groups") or []
    total = sum(len(group.get("practices") or []) for group in groups)
    kept = [
        {**group, "practices": (group.get("practices") or [])[:1]}
        for index, group in enumerate(groups)
        if index == 0 or (group.get("trigger") or {}).get("kind") == "dosha"
    ]
    shown = sum(len(group["practices"]) for group in kept)
    return {**plan, "groups": kept, "count": len(kept), "locked_practices": total - shown}
