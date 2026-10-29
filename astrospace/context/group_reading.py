"""Two or more charts for one purpose, for Ask.

A couple buying a flat, friends starting a venture, brothers marrying on one
day, a family moving house: when the question names more than one saved
profile (context/people.py), code reads every chart before the model writes
anything, the same way `muhurta_search` hands Ask the Muhurta screen's slots:

* `good_months` (core/vedic/group_timing.py): the months that suit all of
  them for the purpose, and whose period is the stronger;
* when the question asks for a time, the Muhurta finder run for all of them
  together (core/vedic/muhurta.py, `others`), with each person's standing on
  every slot.

The model may only report what this section says about the other people. It
never sees their birth details, only names, relationships and results.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from ..core.vedic import group_timing, muhurta
from ..core.vedic.nakshatra import nakshatra_of
from ..core.vedic.positions import sign_index
from .muhurta_search import SEARCH_DAYS, is_muhurta_question

MONTHS_AHEAD = 12

_PURPOSE_WORDS = [
    ("marriage", r"wedding|marriage|marry|engagement|nischitartham"),
    ("vehicle", r"\bcar\b|cars|bike|vehicle|scooter|two.wheeler|suv"),
    ("home", r"house|flat|apartment|home|plot|land|property|villa|griha|gruha|move in"),
    ("venture", r"business|venture|startup|start.up|shop|partnership|company|firm|catering"),
    ("travel", r"abroad|travel|trip|journey|visa|relocat|pilgrimage|yatra"),
    ("event", r"ceremony|ceremonies|puja|pooja|function|upanayan|thread ceremony|naming|"
              r"annaprashan|mundan|seemantham|vratam|homam"),
]


_PEOPLE_NOTE = (
    "Only this profile's chart was read. For `not_saved`, say in one plain line that "
    "you have not read that person's chart because they are not saved, and that "
    "adding them in Profiles lets Siddha read it; anything about them here comes from "
    "this chart alone. For `ambiguous`, ask which of the named profiles they meant."
)


def purpose_of(question: str | None) -> str:
    text = (question or "").lower()
    for purpose, pattern in _PURPOSE_WORDS:
        if re.search(pattern, text):
            return purpose
    return "general"


def _moon(chart) -> dict:
    lon = chart.positions["Moon"]["lon"]
    return {"nak": nakshatra_of(lon)["index"], "rashi": sign_index(lon)}


def group_section(people: list[dict], question: str | None, *,
                  not_saved: list[str] | None = None,
                  ambiguous: dict[str, list[str]] | None = None,
                  today=None) -> dict | None:
    """The bundle's `group_reading` section. ``people``: ``[{"name",
    "relation", "chart", "time_known"}]``, the person Ask is open on first.
    None for fewer than two people."""
    if len(people) < 2:
        if not (not_saved or ambiguous):
            return None
        # One chart, but the question named someone it cannot read.
        return {"people": [{"name": people[0]["name"], "relation": people[0].get("relation")}]
                if people else [],
                "not_saved": list(not_saved or []), "ambiguous": dict(ambiguous or {}),
                "how_to_use": _PEOPLE_NOTE}
    purpose = purpose_of(question)
    anchor = people[0]["chart"]
    tz = anchor.moment.tz_str
    start = today or datetime.now(ZoneInfo(tz)).date()

    months = group_timing.good_months(
        [{"name": p["name"], "chart": p["chart"], "time_known": p.get("time_known", True)}
         for p in people],
        purpose, start, MONTHS_AHEAD)

    section = {
        "people": [{"name": p["name"], "relation": p.get("relation") or "profile",
                    "birth_time": "known" if p.get("time_known", True) else "not known"}
                   for p in people],
        "purpose": months["purpose_label"],
        "months": [
            {"month": m["label"], "together": m["together"],
             "slow_for": m["slow_for"],
             "each": [{"name": e["name"], "standing": e["standing"],
                       "why": e["reasons"][:2], "flags": e["flags"]} for e in m["people"]]}
            for m in months["months"]
        ],
        "good_months": months["good_months"],
        "stronger_phase": months["stronger_phase"],
        "houses_from_moon_for": months["time_unknown_for"],
        "rules": months["rules"],
        "observance_note": months["observance_note"],
        "not_saved": list(not_saved or []),
        "ambiguous": dict(ambiguous or {}),
    }

    if is_muhurta_question(question) or re.search(r"\b(date|dates|day|days)\b", (question or "").lower()):
        me, *rest = [_moon(p["chart"]) | {"name": p["name"]} for p in people]
        partner = rest[0] if len(rest) == 1 else None
        try:
            out = muhurta.find(
                "general", start, start + timedelta(days=SEARCH_DAYS - 1),
                janma_nakshatra_index=me["nak"], janma_rashi_index=me["rashi"],
                ghatak_moon_sign=me["rashi"], intent=question,
                partner=partner, others=rest if partner is None else None,
                lat=anchor.moment.lat, lng=anchor.moment.lng, tz_str=tz, limit=5,
            )
        except (muhurta.ExcludedGoalError, ValueError):
            out = None
        if out:
            first = people[0]["name"]
            section["muhurta"] = {
                "purpose": out["rules_label"],
                "place": f"{anchor.city or 'birth place'} (birth place of {first}), times in {tz}",
                "searched": f"{out['date_from']} to {out['date_to']}",
                "slots": [
                    {"date": r["date"], "weekday": r["vara"], "from": r["start"], "to": r["end"],
                     "standing": r["label"],
                     "each": [{"name": first if row["name"] == "you" else row["name"],
                               "standing": row["standing"]} for row in r.get("people") or []],
                     "why": r["why"]["supports"][:2]}
                    for r in out["results"]
                ],
                "notes": out["notes"],
                "observance_note": out["observance_note"],
            }

    section["how_to_use"] = (
        "Code has read every listed person's chart for this purpose. Name each person; "
        "say which months in `good_months` suit all of them, and who is slow in the other "
        "months. Offer the `muhurta` slots exactly as given, best first, saying who is "
        "weak on a slot. Use `stronger_phase` only to say whose period is stronger for "
        "this purpose; the legal, tax or money side of whose name to use is for a "
        "lawyer or CA. For anyone in `houses_from_moon_for`, say their birth time is not "
        "known so their reading is from the Moon sign. For `not_saved`, say that "
        "person's chart was not read and they can be added in Profiles. For "
        "`ambiguous`, ask which of the named profiles they meant. Never claim anything "
        "about another person that this section does not say. Cite `group_reading`."
    )
    return section
