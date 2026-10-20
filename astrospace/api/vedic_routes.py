import copy
from datetime import date, datetime, time
from functools import lru_cache
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Literal, Optional

from ..db import get_db
from ..db import crud
from .timing_place import resolve_timing_place
from ..core.vedic import VedicChart, LocationError
from ..core.vedic.compatibility import gun_milan
from ..agents.compat_insight_agent import compat_insight_enabled
from ..context import compat_insight_store
from ..core.vedic.vargas import VARGA_FUNCTIONS
from ..knowledge.vedic_rules import get_rule, rules_catalog
from .auth import CurrentUser
from ..entitlements import EntitlementDenied, plan_lock

router = APIRouter(prefix="/api/v1/vedic", tags=["vedic"])


class VedicBirthInfo(BaseModel):
    name: str
    year: int
    month: int
    day: int
    hour: int = 12
    minute: int = 0
    city: Optional[str] = None
    nation: str = "IN"
    lat: Optional[float] = None
    lng: Optional[float] = None
    tz_str: Optional[str] = None
    ayanamsha: str = "lahiri"
    node_type: str = "mean"


def _chart_from_kundli(k, ayanamsha: str = "lahiri", node_type: str = "mean") -> VedicChart:
    try:
        return VedicChart(
            k.name, k.birth_year, k.birth_month, k.birth_day,
            k.birth_hour, k.birth_minute, k.birth_city, k.birth_nation,
            ayanamsha=ayanamsha, node_type=node_type,
        )
    except LocationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except (ValueError, OverflowError) as e:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid birth details on this kundli "
                   f"({k.birth_year}-{k.birth_month}-{k.birth_day} "
                   f"{k.birth_hour}:{k.birth_minute}): {e}. "
                   "Edit the kundli to fix the date (DD/MM/YYYY order).",
        )


def _get_kundli(db: Session, kundli_id: str, user_id: str):
    k = crud.get_kundli(db, kundli_id, user_id)
    if not k:
        raise HTTPException(status_code=404, detail="Kundli not found")
    return k



def _reading_calendar_marker(r) -> dict:
    rating_labels = {
        1: "missed",
        2: "not applicable",
        3: "partly accurate",
        4: "mostly accurate",
        5: "accurate",
    }
    return {
        "id": r.id,
        "reading_type": r.reading_type or "reading",
        "period_label": r.period_label,
        "generated_local_date": r.generated_local_date,
        "version": r.version or 1,
        "deviation_score": r.deviation_score,
        "deviation_band": (r.deviation_summary or {}).get("band"),
        "user_rating": r.user_rating,
        "feedback_status": rating_labels.get(r.user_rating, "pending validation"),
        "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
        "generated_at": r.generated_at.isoformat() if r.generated_at else None,
    }


def _claim_calendar_marker(c) -> dict:
    return {
        "id": c.id,
        "reading_id": c.reading_id,
        "reading_type": c.reading_type or "reading",
        "period_label": c.period_label,
        "target_start_date": c.target_start_date,
        "target_end_date": c.target_end_date,
        "category": c.category or "general",
        "claim_text": c.claim_text or "",
        "confidence": c.confidence,
        "status": c.status or "pending",
        "reviewed_at": c.reviewed_at.isoformat() if c.reviewed_at else None,
    }


def _attach_readings_to_calendar(payload: dict, db: Session, kundli_id: str, user_id: str) -> dict:
    readings = crud.get_readings_for_calendar(
        db,
        kundli_id,
        user_id,
        payload["start_date"],
        payload["end_date"],
    )
    readings_by_date: dict[str, list[dict]] = {}
    reading_events = []
    for reading in readings:
        date = reading.generated_local_date
        if not date:
            continue
        marker = _reading_calendar_marker(reading)
        readings_by_date.setdefault(date, []).append(marker)
        reading_type = marker["reading_type"]
        event = {
            "date": date,
            "category": "reading",
            "title": f"{reading_type.title()} reading v{reading.version or 1}",
            "detail": (
                f"{reading.period_label or 'Generated AI prediction'} · "
                f"{marker['feedback_status']}"
            ),
            "tone": "neutral",
            "strength": 55,
            "meta": {
                "reading_id": reading.id,
                "version": reading.version or 1,
                "deviation_score": reading.deviation_score,
                "deviation_band": marker["deviation_band"],
                "user_rating": reading.user_rating,
            },
        }
        reading_events.append(event)
        payload.setdefault("by_date", {}).setdefault(date, []).append(event)

    payload["readings_by_date"] = readings_by_date
    payload.setdefault("current", {})["readings"] = readings_by_date.get(payload["start_date"], [])

    claims = crud.get_prediction_claims(
        db,
        kundli_id,
        user_id,
        start_date=payload["start_date"],
        end_date=payload["end_date"],
        limit=300,
    )
    claims_by_date: dict[str, list[dict]] = {}
    claim_events = []
    for claim in claims:
        date = claim.target_start_date or claim.generated_local_date
        if not date:
            continue
        marker = _claim_calendar_marker(claim)
        claims_by_date.setdefault(date, []).append(marker)
        category = marker["category"]
        status = marker["status"]
        event = {
            "date": date,
            "category": "prediction",
            "title": f"{category.title()} claim · {status.replace('_', ' ')}",
            "detail": marker["claim_text"][:140],
            "tone": "neutral",
            "strength": int((claim.confidence or 0.5) * 100),
            "meta": {
                "claim_id": claim.id,
                "reading_id": claim.reading_id,
                "status": claim.status,
                "target_end_date": claim.target_end_date,
            },
        }
        claim_events.append(event)
        payload.setdefault("by_date", {}).setdefault(date, []).append(event)

    payload["prediction_claims_by_date"] = claims_by_date
    payload.setdefault("current", {})["prediction_claims"] = claims_by_date.get(payload["start_date"], [])
    payload.setdefault("events", []).extend(reading_events)
    payload.setdefault("events", []).extend(claim_events)
    payload["events"].sort(key=lambda event: (event["date"], -event.get("strength", 0), event["category"]))
    return payload


@router.post("/chart")
def compute_chart(b: VedicBirthInfo):
    """Full Vedic chart from raw birth details (no DB record needed)."""
    try:
        chart = VedicChart(b.name, b.year, b.month, b.day, b.hour, b.minute,
                           b.city, b.nation, b.lat, b.lng, b.tz_str,
                           b.ayanamsha, b.node_type)
    except LocationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return chart.to_dict()


@router.get("/rules")
def vedic_rules(kind: str | None = Query(None, description="Filter to 'yoga' or 'dosha'.")):
    """The full yoga/dosha knowledge base — reference data, not chart-specific.

    Backs a Practitioner "browse all yogas/doshas" reference screen and any
    "Learn this Yoga" sheet that wants the full catalog rather than a single
    rule. Per-chart results (``/{kundli_id}/yogas``, ``/{kundli_id}/doshas``)
    already carry the same explanatory fields inline via
    ``enrich_rule_result`` — this endpoint exists for browsing, not as the
    only way to get them.
    """
    catalog = list(rules_catalog().values())
    if kind is not None:
        catalog = [rule for rule in catalog if rule["kind"] == kind]
    return {"rules": catalog, "count": len(catalog)}


@router.get("/rules/{rule_id}")
def vedic_rule_detail(rule_id: str):
    """A single yoga/dosha rule by id — same shape as one entry of ``/rules``."""
    return get_rule(rule_id)


# The two divisional charts every plan sees; the rest need `vargas.full`.
# Mirrors FREE_VARGAS in ui/src/app/core/plan-gate.service.ts.
FREE_VARGAS = frozenset({"D1", "D9"})


def _varga_decision(db: Session, user_id: str):
    """`vargas.full` for this reader, or None while plan locks are off."""
    return plan_lock(db, user_id, "vargas.full")


# Yogas every plan sees in full; the rest need `yogas.full`.
# Mirrors FREE_YOGAS in ui/src/app/features/mobile/chart/yogas-doshas.component.ts.
FREE_YOGAS = 2


def _without_locked_yogas(summary: dict, db: Session, user_id: str) -> dict:
    """Free keeps the first two active yogas and a count of the rest.

    Doshas are never trimmed: a dosha is a flag on every plan.
    """
    active = summary.get("active")
    if not isinstance(active, list) or plan_lock(db, user_id, "yogas.full") is None:
        return summary
    kept, locked = active[:FREE_YOGAS], active[FREE_YOGAS:]
    locked_ids = {id(yoga) for yoga in locked}
    summary["active"] = kept
    summary["all"] = [yoga for yoga in summary.get("all", []) if id(yoga) not in locked_ids]
    summary["locked_count"] = len(locked)
    return summary


def _without_locked_vargas(payload: dict, db: Session, user_id: str) -> dict:
    if not isinstance(payload.get("vargas"), dict) or _varga_decision(db, user_id) is None:
        return payload
    payload["vargas"] = {key: value for key, value in payload["vargas"].items() if key in FREE_VARGAS}
    return payload


@router.get("/{kundli_id}/all")
def full_vedic_chart(
    kundli_id: str,
    user: CurrentUser,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    payload = _chart_from_kundli(_get_kundli(db, kundli_id, user.id), ayanamsha, node_type).to_dict()
    if isinstance(payload.get("yogas"), dict):
        payload["yogas"] = _without_locked_yogas(payload["yogas"], db, user.id)
    return _without_locked_vargas(payload, db, user.id)


@router.get("/{kundli_id}/avkahada")
def avkahada(kundli_id: str, user: CurrentUser, db: Session = Depends(get_db)):
    chart = _chart_from_kundli(_get_kundli(db, kundli_id, user.id))
    return {
        "meta": chart.meta(),
        "avkahada": chart.avkahada(),
        "ghatak": chart.ghatak(),
        "favourable": chart.favourable(),
    }


@router.get("/{kundli_id}/panchanga")
def panchanga(kundli_id: str, user: CurrentUser, db: Session = Depends(get_db)):
    return _chart_from_kundli(_get_kundli(db, kundli_id, user.id)).panchanga


@router.get("/{kundli_id}/dashas")
def dashas(
    kundli_id: str,
    user: CurrentUser,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    return _chart_from_kundli(_get_kundli(db, kundli_id, user.id), ayanamsha, node_type).dashas()


@router.get("/{kundli_id}/ashtakavarga")
def ashtakavarga(
    kundli_id: str,
    user: CurrentUser,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    return _chart_from_kundli(_get_kundli(db, kundli_id, user.id), ayanamsha, node_type).ashtakavarga()


@router.get("/{kundli_id}/vimshopaka-bala")
def vimshopaka_bala_route(
    kundli_id: str,
    user: CurrentUser,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    scheme: str = Query("shodashavarga", description="shadvarga | saptavarga | dashavarga | shodashavarga"),
    db: Session = Depends(get_db),
):
    chart = _chart_from_kundli(_get_kundli(db, kundli_id, user.id), ayanamsha, node_type)
    try:
        return chart.vimshopaka_bala(scheme=scheme)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/{kundli_id}/shadbala")
def shadbala(
    kundli_id: str,
    user: CurrentUser,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    return _chart_from_kundli(_get_kundli(db, kundli_id, user.id), ayanamsha, node_type).shadbala()


@router.get("/{kundli_id}/planetary-conditions")
def planetary_conditions(
    kundli_id: str,
    user: CurrentUser,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    return _chart_from_kundli(_get_kundli(db, kundli_id, user.id), ayanamsha, node_type).planetary_conditions()


@router.get("/{kundli_id}/doshas")
def doshas(
    kundli_id: str,
    user: CurrentUser,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    return _chart_from_kundli(_get_kundli(db, kundli_id, user.id), ayanamsha, node_type).doshas()


@router.get("/{kundli_id}/yogas")
def yogas(
    kundli_id: str,
    user: CurrentUser,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    return _without_locked_yogas(
        _chart_from_kundli(_get_kundli(db, kundli_id, user.id), ayanamsha, node_type).yogas(), db, user.id,
    )


@router.get("/{kundli_id}/yogas-doshas")
def yogas_doshas(
    kundli_id: str,
    user: CurrentUser,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    chart = _chart_from_kundli(_get_kundli(db, kundli_id, user.id), ayanamsha, node_type)
    return {"yogas": _without_locked_yogas(chart.yogas(), db, user.id), "doshas": chart.doshas()}


@router.get("/{kundli_id}/jaimini")
def jaimini(
    kundli_id: str,
    user: CurrentUser,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    return _chart_from_kundli(_get_kundli(db, kundli_id, user.id), ayanamsha, node_type).jaimini()


@router.get("/{kundli_id}/chara-dasha")
def chara_dasha_route(
    kundli_id: str,
    user: CurrentUser,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    return _chart_from_kundli(_get_kundli(db, kundli_id, user.id), ayanamsha, node_type).chara_dasha()


@router.get("/{kundli_id}/bhava-chalit")
def bhava_chalit_route(
    kundli_id: str,
    user: CurrentUser,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    """Sripati house system — opt-in alternate to the default whole-sign
    houses everything else in this API uses."""
    return _chart_from_kundli(_get_kundli(db, kundli_id, user.id), ayanamsha, node_type).bhava_chalit()


@router.get("/{kundli_id}/special-lagnas")
def special_lagnas(
    kundli_id: str,
    user: CurrentUser,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    return _chart_from_kundli(_get_kundli(db, kundli_id, user.id), ayanamsha, node_type).special_lagnas()


@router.get("/{kundli_id}/masa")
def masa(
    kundli_id: str,
    user: CurrentUser,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    return _chart_from_kundli(_get_kundli(db, kundli_id, user.id), ayanamsha, node_type).masa()


@router.get("/{kundli_id}/yogini-dashas")
def yogini_dashas(
    kundli_id: str,
    user: CurrentUser,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    return _chart_from_kundli(_get_kundli(db, kundli_id, user.id), ayanamsha, node_type).yogini_dashas()


@router.get("/{kundli_id}/transit-context")
def transit_context(
    kundli_id: str,
    user: CurrentUser,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    return _chart_from_kundli(_get_kundli(db, kundli_id, user.id), ayanamsha, node_type).transit_context()


@router.get("/{kundli_id}/transits")
def transits(
    kundli_id: str,
    user: CurrentUser,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    return _chart_from_kundli(_get_kundli(db, kundli_id, user.id), ayanamsha, node_type).transits()


@router.get("/{kundli_id}/gocharam")
def gocharam(
    kundli_id: str,
    user: CurrentUser,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    scan_days: int = Query(90, ge=30, le=1095),
    as_of: Optional[date] = Query(None, description="Timeline snapshot date"),
    db: Session = Depends(get_db),
):
    chart = _chart_from_kundli(
        _get_kundli(db, kundli_id, user.id),
        ayanamsha,
        node_type,
    )
    snapshot = (
        datetime.combine(as_of, time(hour=12), tzinfo=chart.moment.dt_local.tzinfo)
        if as_of
        else None
    )
    return chart.gocharam(scan_days=scan_days, as_of=snapshot)


# A 45-day calendar is tens of seconds of CPU on a busy Cloud Run instance,
# and the app asks for the same window on every open, month swipe and retry.
# Keyed on the birth details themselves, so editing a profile misses the
# cache. "Now" is bucketed to 15 minutes, as for daily guidance
# (context_routes.py); an explicit as_of is exact.
CALENDAR_BUCKET_MINUTES = 15


def _bucketed_now(tz: ZoneInfo) -> datetime:
    now = datetime.now(tz)
    return now.replace(minute=now.minute - now.minute % CALENDAR_BUCKET_MINUTES,
                       second=0, microsecond=0)


@lru_cache(maxsize=128)
def _cached_calendar(name, year, month, day, hour, minute, b_city, b_nation,
                     ayanamsha, node_type, as_of_iso, city, nation, lat, lng,
                     tz_str, days, include_practitioner_detail) -> dict:
    chart = VedicChart(name, year, month, day, hour, minute, b_city, b_nation,
                       ayanamsha=ayanamsha, node_type=node_type)
    return chart.calendar_intelligence(
        as_of=datetime.fromisoformat(as_of_iso), city=city, nation=nation,
        lat=lat, lng=lng, tz_str=tz_str, display_tz_str=tz_str, days=days,
        include_practitioner_detail=include_practitioner_detail,
    )


@router.get("/{kundli_id}/calendar-intelligence")
def calendar_intelligence(
    kundli_id: str,
    user: CurrentUser,
    days: int = Query(30, ge=1, le=60),
    as_of: Optional[date] = Query(None, description="Calendar window start date in the viewer timezone"),
    include_practitioner_detail: bool = Query(False, description="Include full practitioner day payloads"),
    timezone: Optional[str] = Query(None, description="Viewer IANA timezone"),
    city: Optional[str] = Query(None, description="Optional panchanga place override"),
    nation: Optional[str] = None,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    k = _get_kundli(db, kundli_id, user.id)
    _chart_from_kundli(k, ayanamsha, node_type)  # validates the birth details
    place = resolve_timing_place(k, timezone, city, nation)
    calculation_time = (
        datetime.combine(as_of, time(hour=12), tzinfo=ZoneInfo(place.tz_str))
        if as_of
        else _bucketed_now(ZoneInfo(place.today_tz))
    )
    # Deep copy: the cached dict is shared, and the lines below add to it.
    payload = copy.deepcopy(_cached_calendar(
        k.name, k.birth_year, k.birth_month, k.birth_day, k.birth_hour,
        k.birth_minute, k.birth_city, k.birth_nation, ayanamsha, node_type,
        calculation_time.isoformat(), place.city, place.nation, place.lat,
        place.lng, place.tz_str, days, include_practitioner_detail,
    ))
    # Same resolution as /panchanga/{id}/today, /context/{id}/daily and
    # /muhurta/{id}; the screen needs `source` to say whose clock this is.
    payload["place"] = place.as_payload()
    payload["provenance"]["panchanga_place"] = place.as_payload()
    return _attach_readings_to_calendar(payload, db, kundli_id, user.id)


@router.get("/{kundli_id}/compatibility/{partner_id}")
def compatibility(
    kundli_id: str,
    partner_id: str,
    user: CurrentUser,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    chart_a = _chart_from_kundli(_get_kundli(db, kundli_id, user.id), ayanamsha, node_type)
    chart_b = _chart_from_kundli(_get_kundli(db, partner_id, user.id), ayanamsha, node_type)
    return gun_milan(chart_a, chart_b)


@router.get("/{kundli_id}/compatibility/{partner_id}/insight")
def compatibility_insight(
    kundli_id: str,
    partner_id: str,
    user: CurrentUser,
    stage: Literal["married", "planning"] = "married",
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    """The "About you two" section of the full report, in the agent's words.

    Written the first time a pair is opened and kept (context/
    compat_insight_store.py). Answers 200 with `insight: null` when the plan
    lacks the full report, the agent is off, or no safe section could be
    written: the app keeps the fixed guidance gun_milan() already returned.
    """
    kundli = _get_kundli(db, kundli_id, user.id)
    partner = _get_kundli(db, partner_id, user.id)
    if plan_lock(db, user.id, "compatibility.full") is not None:
        return {"source": "locked", "insight": None}
    if not compat_insight_enabled():
        return {"source": "template", "insight": None}
    chart_a = _chart_from_kundli(kundli, ayanamsha, node_type)
    chart_b = _chart_from_kundli(partner, ayanamsha, node_type)
    value, written_now = compat_insight_store.ensure_insight(
        db, user.id, kundli, partner, chart_a, chart_b, gun_milan(chart_a, chart_b),
        stage=stage, ayanamsha=ayanamsha, node_type=node_type,
    )
    if not value:
        return {"source": "template", "insight": None}
    return {**value, "cached": not written_now}


@router.get("/{kundli_id}/vargas")
def all_vargas(
    kundli_id: str,
    user: CurrentUser,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    chart = _chart_from_kundli(_get_kundli(db, kundli_id, user.id), ayanamsha, node_type)
    return _without_locked_vargas(
        {"lagna": chart.lagna_details(), "vargas": chart.all_varga_charts(), "dignities": chart.dignities()},
        db, user.id,
    )


@router.get("/{kundli_id}/d/{n}")
def varga_chart(
    kundli_id: str,
    n: int,
    user: CurrentUser,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    db: Session = Depends(get_db),
):
    varga = f"D{n}"
    if varga not in VARGA_FUNCTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown varga D{n}; available: {sorted(VARGA_FUNCTIONS)}",
        )
    if varga not in FREE_VARGAS:
        denied = _varga_decision(db, user.id)
        if denied is not None:
            raise EntitlementDenied(denied)
    return _chart_from_kundli(_get_kundli(db, kundli_id, user.id), ayanamsha, node_type).varga_chart(varga)
