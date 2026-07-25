"""Goal-based muhurta finder — ranks auspicious windows for a stated intent.

`kala.py` already computes the raw named windows for a day (Abhijit, Amrit
Kalam, Brahma Muhurta, Rahu Kalam, Yamaganda, Gulika, Durmuhurta, Varjya,
Bhadra). This module answers the question a user actually asks: *"when is a
good time to sign this contract?"* — by scoring those windows against the day's
panchanga and the person's own tarabala/chandrabala, then ranking them.

Design constraints (design_principles.md §4):

* **No health, legal or financial goals.** A "good time to start treatment" or
  "win a case" is a refer-out, not a muhurta. `GOALS` deliberately omits them
  and :func:`find` raises for excluded intents.
* **Timing supports intent; it does not guarantee outcome.** Every result
  carries its contributing factors so the reasoning is inspectable, and the
  payload states plainly that the decision remains the user's.
* **Honest emptiness.** If no window clears the bar the finder says so rather
  than inventing a "best available" slot.
"""
from __future__ import annotations

from datetime import date as date_cls, datetime, timedelta

from .constants import NAKSHATRAS
from .panchanga_day import daily_panchanga, personal_panchanga

# ── Goals ────────────────────────────────────────────────────────────────────
# Slugs match the goal-picker screen. Preferences are classical and regionally
# variable, hence the convention_dependent flag on every result.
#
#   prefer_vara      — weekday names that traditionally suit the activity
#   prefer_nakshatra — nakshatras favoured for it
#   avoid_tithi      — tithi numbers (1-15) traditionally avoided
#
# Rikta tithis (4, 9, 14) are avoided for most new undertakings; Amavasya (30 /
# tithi 15 of krishna paksha) likewise.

RIKTA_TITHIS = {4, 9, 14}

GOALS: dict[str, dict] = {
    "buy_property_gold": {
        "label": "Buy property or gold",
        "prefer_vara": ["Thursday", "Friday"],
        "prefer_nakshatra": ["Rohini", "Pushya", "Uttara Phalguni", "Uttara Ashadha",
                             "Uttara Bhadrapada", "Anuradha", "Revati"],
        "avoid_tithi": RIKTA_TITHIS,
    },
    "sign_contract": {
        "label": "Sign a contract",
        "prefer_vara": ["Wednesday", "Thursday"],
        "prefer_nakshatra": ["Hasta", "Chitra", "Anuradha", "Uttara Phalguni",
                             "Uttara Ashadha", "Shravana"],
        "avoid_tithi": RIKTA_TITHIS,
    },
    "start_journey": {
        "label": "Start a journey",
        "prefer_vara": ["Monday", "Wednesday", "Thursday", "Friday"],
        "prefer_nakshatra": ["Ashwini", "Mrigashira", "Punarvasu", "Pushya",
                             "Hasta", "Anuradha", "Shravana", "Dhanishta", "Revati"],
        "avoid_tithi": RIKTA_TITHIS,
    },
    "start_venture": {
        "label": "Start a new venture",
        "prefer_vara": ["Wednesday", "Thursday", "Friday"],
        "prefer_nakshatra": ["Ashwini", "Rohini", "Pushya", "Hasta", "Chitra",
                             "Anuradha", "Uttara Phalguni", "Shravana"],
        "avoid_tithi": RIKTA_TITHIS,
    },
    "marriage_related": {
        "label": "Marriage-related",
        "prefer_vara": ["Monday", "Wednesday", "Thursday", "Friday"],
        "prefer_nakshatra": ["Rohini", "Mrigashira", "Magha", "Uttara Phalguni",
                             "Hasta", "Swati", "Anuradha", "Moola",
                             "Uttara Ashadha", "Uttara Bhadrapada", "Revati"],
        "avoid_tithi": RIKTA_TITHIS,
    },
    "general": {
        "label": "Something else",
        "prefer_vara": [],
        "prefer_nakshatra": [],
        "avoid_tithi": RIKTA_TITHIS,
    },
}

# Intents that must never be answered with a muhurta — these refer out instead.
EXCLUDED_INTENTS = {
    "medical": "health",
    "treatment": "health",
    "surgery": "health",
    "litigation": "legal",
    "court": "legal",
    "lawsuit": "legal",
    "investment": "financial",
    "trading": "financial",
}


class ExcludedGoalError(ValueError):
    """Raised for intents the product refers out rather than timing."""

    def __init__(self, domain: str):
        self.domain = domain
        super().__init__(
            f"{domain} decisions are not answered with muhurta timing; "
            "refer the user to a qualified professional."
        )


# Base quality of each auspicious window, before day/personal adjustment.
_WINDOW_BASE = {
    "Abhijit Muhurta": 34,
    "Amrit Kalam": 32,
    "Brahma Muhurta": 26,
    "Godhuli": 20,
}

_MIN_SCORE = 45          # below this a window is not offered at all
_BEST_SCORE = 72         # at or above this a window is labelled "best"
_GOOD_SCORE = 58


# Windows carry a qualifier in the name (e.g. "Amrit Kalam (Uttara Ashadha)"),
# so the base lookup matches on prefix rather than equality.
_MIN_USABLE_MINUTES = 20


def _base_for(name: str) -> int:
    for prefix, base in _WINDOW_BASE.items():
        if name.startswith(prefix):
            return base
    return 18


def _overlaps(a_start: str, a_end: str, b_start: str, b_end: str) -> bool:
    """True when two ISO local-time ranges intersect."""
    return a_start < b_end and b_start < a_end


def _clear_span(window: dict, inauspicious: list[dict]) -> tuple[datetime, datetime] | None:
    """Largest part of ``window`` not covered by any inauspicious window.

    A muhurta that merely clips the edge of Rahu Kalam is still usable for the
    minutes that fall outside it, so trim rather than discard.
    """
    start = datetime.fromisoformat(window["start_iso"])
    end = datetime.fromisoformat(window["end_iso"])

    blocks = sorted(
        (datetime.fromisoformat(b["start_iso"]), datetime.fromisoformat(b["end_iso"]))
        for b in inauspicious
        if _overlaps(window["start_iso"], window["end_iso"], b["start_iso"], b["end_iso"])
    )

    free: list[tuple[datetime, datetime]] = []
    cursor = start
    for b_start, b_end in blocks:
        if b_start > cursor:
            free.append((cursor, min(b_start, end)))
        cursor = max(cursor, b_end)
        if cursor >= end:
            break
    if cursor < end:
        free.append((cursor, end))

    if not free:
        return None
    best = max(free, key=lambda f: f[1] - f[0])
    if (best[1] - best[0]) < timedelta(minutes=_MIN_USABLE_MINUTES):
        return None
    return best


def _score_day(day: dict, personal: dict, goal: dict) -> tuple[int, list[str], list[str]]:
    """Score the day itself. Returns (delta, positive_factors, negative_factors)."""
    plus: list[str] = []
    minus: list[str] = []
    delta = 0

    vara = (day.get("vara") or {}).get("name")
    nak = ((day.get("elements") or {}).get("nakshatra") or [{}])[0].get("name")
    tithi_entry = ((day.get("elements") or {}).get("tithi") or [{}])[0]
    tithi_number = (tithi_entry.get("index", 0) % 15) + 1

    if goal["prefer_vara"] and vara in goal["prefer_vara"]:
        delta += 10
        plus.append(f"{vara} suits this")
    if goal["prefer_nakshatra"] and nak in goal["prefer_nakshatra"]:
        delta += 12
        plus.append(f"{nak} is favourable for it")
    if tithi_number in goal["avoid_tithi"]:
        delta -= 14
        minus.append(f"Rikta tithi ({tithi_number}) — traditionally avoided")

    tarabala = personal.get("tarabala") or {}
    if tarabala.get("favourable"):
        delta += 10
        plus.append(f"Tarabala favourable ({tarabala.get('tara')})")
    else:
        delta -= 10
        minus.append(f"Tarabala unfavourable ({tarabala.get('tara')})")
    if tarabala.get("tara") == "Janma":
        delta -= 8
        minus.append("Janma tara — avoid major beginnings")

    chandrabala = personal.get("chandrabala") or {}
    if chandrabala.get("chandrashtama"):
        delta -= 20
        minus.append("Chandrashtama — the Moon is in the 8th from your sign")
    elif chandrabala.get("favourable"):
        delta += 8
        plus.append("Chandrabala strong")

    matched_ghatak = [a for a in (personal.get("ghatak_alerts") or []) if a.get("matched")]
    if matched_ghatak:
        delta -= 6
        minus.append(f"Ghatak match ({', '.join(a['type'] for a in matched_ghatak)})")

    return delta, plus, minus


def find(goal_slug: str, date_from: date_cls, date_to: date_cls, *,
         janma_nakshatra_index: int, janma_rashi_index: int,
         ghatak_moon_sign: int | None = None,
         city: str | None = None, nation: str = "IN",
         lat: float | None = None, lng: float | None = None,
         tz_str: str | None = None,
         limit: int = 5, max_days: int = 62) -> dict:
    """Find and rank auspicious windows for a goal over a date range.

    Args:
        goal_slug: a key of :data:`GOALS`.
        date_from / date_to: inclusive search range.
        janma_nakshatra_index / janma_rashi_index: from the person's kundli;
            drive tarabala and chandrabala.
        ghatak_moon_sign: optional, enables ghatak-chakra penalties.
        city/nation or lat/lng/tz_str: where the timings apply — pass the
            user's *current* location for the diaspora case.
        limit: how many windows to return.
        max_days: guard against unbounded ranges.

    Raises:
        ExcludedGoalError: for health/legal/financial intents.
        ValueError: for an unknown goal or an inverted/oversized range.
    """
    lowered = (goal_slug or "").lower()
    for token, domain in EXCLUDED_INTENTS.items():
        if token in lowered:
            raise ExcludedGoalError(domain)

    goal = GOALS.get(goal_slug)
    if goal is None:
        raise ValueError(f"Unknown goal '{goal_slug}'. Known: {sorted(GOALS)}")
    if date_to < date_from:
        raise ValueError("date_to must not be before date_from")
    span = (date_to - date_from).days + 1
    if span > max_days:
        raise ValueError(f"Range too large ({span} days); max is {max_days}")

    candidates: list[dict] = []
    days_scanned = 0
    skipped: list[dict] = []

    for offset in range(span):
        day_date = date_from + timedelta(days=offset)
        try:
            day = daily_panchanga(
                day_date.year, day_date.month, day_date.day,
                city=city, nation=nation, lat=lat, lng=lng, tz_str=tz_str,
            )
        except ValueError as exc:  # circumpolar / undefined sunrise
            skipped.append({"date": day_date.isoformat(), "reason": str(exc)})
            continue

        days_scanned += 1
        personal = personal_panchanga(
            day, janma_nakshatra_index, janma_rashi_index, ghatak_moon_sign
        )
        day_delta, day_plus, day_minus = _score_day(day, personal, goal)

        windows = day.get("windows") or {}
        inauspicious = windows.get("inauspicious") or []

        for window in windows.get("auspicious") or []:
            score = _base_for(window["name"]) + day_delta
            plus = list(day_plus)
            minus = list(day_minus)

            clashes = sorted({
                bad["name"] for bad in inauspicious
                if _overlaps(window["start_iso"], window["end_iso"],
                             bad["start_iso"], bad["end_iso"])
            })

            # Trim to the clash-free part rather than discarding the window;
            # a muhurta clipping the edge of Rahu Kalam is still usable for
            # the minutes outside it.
            span = _clear_span(window, inauspicious)
            if span is None:
                continue
            clear_start, clear_end = span
            trimmed = (
                clear_start != datetime.fromisoformat(window["start_iso"])
                or clear_end != datetime.fromisoformat(window["end_iso"])
            )

            if trimmed:
                score -= 8
                minus.append(f"Trimmed to avoid {', '.join(clashes)}")
            else:
                plus.append("Clear of Rahu Kalam and other avoid-windows")

            # Abhijit is traditionally not observed on Wednesday; kala.py
            # already notes this, so honour its note rather than re-deriving.
            if window.get("note"):
                score -= 10
                minus.append(window["note"])

            score = max(0, min(100, score))
            if score < _MIN_SCORE:
                continue

            candidates.append({
                "date": day_date.isoformat(),
                "window": window["name"],
                "start": clear_start.strftime("%H:%M"),
                "end": clear_end.strftime("%H:%M"),
                "start_iso": clear_start.isoformat(),
                "end_iso": clear_end.isoformat(),
                "trimmed": trimmed,
                "duration_minutes": int((clear_end - clear_start).total_seconds() // 60),
                "score": score,
                "quality": ("best" if score >= _BEST_SCORE
                            else "good" if score >= _GOOD_SCORE else "workable"),
                "why": {"supports": plus, "against": minus},
                "vara": (day.get("vara") or {}).get("name"),
                "nakshatra": ((day.get("elements") or {}).get("nakshatra") or [{}])[0].get("name"),
            })

    candidates.sort(key=lambda c: (-c["score"], c["start_iso"]))
    results = candidates[:limit]

    return {
        "goal": goal_slug,
        "goal_label": goal["label"],
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "days_scanned": days_scanned,
        "skipped_days": skipped,
        "results": results,
        "count": len(results),
        "note": (
            None if results else
            "No window in this range clears the bar. Widening the dates usually "
            "helps more than settling for a weak slot."
        ),
        "is_convention_dependent": True,
        "disclaimer": (
            "Timing supports your intent — the decision and the diligence are "
            "still yours. Muhurta is not offered for health, legal or financial "
            "matters; please consult a qualified professional for those."
        ),
    }


def goal_catalog() -> list[dict]:
    """Goals in a shape that maps onto the ``muhurta_goals`` table."""
    return [
        {
            "slug": slug,
            "label": spec["label"],
            "description": None,
            "rules": {
                "prefer_vara": spec["prefer_vara"],
                "prefer_nakshatra": spec["prefer_nakshatra"],
                "avoid_tithi": sorted(spec["avoid_tithi"]),
            },
            "is_active": True,
        }
        for slug, spec in GOALS.items()
    ]
