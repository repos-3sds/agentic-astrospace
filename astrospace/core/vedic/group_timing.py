"""Months that suit several people for one shared purpose.

A couple buying a house, two friends starting a venture, a family moving:
each person's own chart has to support the purpose in the same stretch of
time. This reads every person month by month on three standard rules and
lines them up, so Ask can say which months suit all of them and who is in
the stronger phase (for "whose name should it be in").

The rules, each stated in the output so nothing is implied:

* **Dasha.** A period lord gives the results of the houses it rules and
  occupies (BPHS, the dasha chapters). The running antardasha lord touching a
  purpose house counts +2, the mahadasha lord +1. An antardasha lord that
  touches no purpose house and sits in the 6th, 8th or 12th counts -1.
* **Jupiter from the Moon.** Jupiter transiting the 2nd, 5th, 7th, 9th or
  11th from the birth Moon (Guru bala) counts +1.
* **Saturn from the Moon.** Sade Sati (12th, 1st, 2nd) and Ashtama Shani
  (8th) count -1 and are named as a flag, never as a verdict.

Houses are counted from the Lagna when the birth time is known, and from the
Moon sign when it is not (the Lagna moves every two hours; the Moon sign
rarely changes in a day), which the output says.

This is a timing aid for planning, not a verdict on the purchase, the
venture or the money: Ask still refers financial and legal decisions out.
"""
from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import swisseph as swe

from .constants import SIGN_LORDS
from .positions import sidereal_positions, sign_index

PURPOSES: dict[str, dict] = {
    "home":     {"label": "buying or moving into a home", "houses": (4,)},
    "vehicle":  {"label": "buying a vehicle", "houses": (4,)},
    "venture":  {"label": "starting a venture together", "houses": (7, 10, 11)},
    "marriage": {"label": "a wedding", "houses": (7,)},
    "travel":   {"label": "travel or a move abroad", "houses": (9, 12)},
    "event":    {"label": "a family event or ceremony", "houses": (1, 4, 9)},
    "general":  {"label": "a new start together", "houses": (1, 10, 11)},
}
MAX_PEOPLE = 5
MAX_MONTHS = 24

_GURU_BALA = {2, 5, 7, 9, 11}
_SADE_SATI = {12, 1, 2}
_DUSTHANA = {6, 8, 12}

RULES_NOTE = (
    "Rules used: the running period lords and the houses they rule or occupy "
    "(BPHS), Jupiter's transit from the birth Moon (Guru bala), and Saturn's "
    "Sade Sati and Ashtama Shani as flags. Houses from the Lagna when the birth "
    "time is known, from the Moon sign when it is not."
)


def _house(sign: int, anchor: int) -> int:
    return (sign - anchor) % 12 + 1


def _touched_houses(planet: str, positions: dict, anchor: int) -> set[int]:
    """Houses a planet rules and occupies, counted from ``anchor``."""
    houses = {_house(s, anchor) for s, lord in enumerate(SIGN_LORDS) if lord == planet}
    houses.add(_house(sign_index(positions[planet]["lon"]), anchor))
    return houses


def _running(dashas: dict, moment: datetime) -> tuple[str, str] | None:
    for maha in dashas["mahadashas"]:
        if datetime.fromisoformat(maha["start"]) <= moment < datetime.fromisoformat(maha["end"]):
            for antar in maha["antardashas"]:
                if datetime.fromisoformat(antar["start"]) <= moment < datetime.fromisoformat(antar["end"]):
                    return maha["lord"], antar["lord"]
            return maha["lord"], maha["lord"]
    return None


def _months(start: date, count: int) -> list[date]:
    out, y, m = [], start.year, start.month
    for _ in range(count):
        out.append(date(y, m, 15))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def _person_month(person: dict, dashas: dict, when: date, houses: tuple[int, ...],
                  transit: dict) -> dict:
    chart = person["chart"]
    natal = chart.positions
    moon = sign_index(natal["Moon"]["lon"])
    anchor = sign_index(chart.lagna_lon) if person.get("time_known", True) else moon
    tz = chart.moment.dt_local.tzinfo or ZoneInfo("Asia/Kolkata")
    moment = datetime.combine(when, time(12), tzinfo=tz)

    score, reasons, flags = 0, [], []
    lords = _running(dashas, moment)
    if lords:
        maha, antar = lords
        antar_touch = _touched_houses(antar, natal, anchor)
        if antar_touch & set(houses):
            score += 2
            reasons.append(f"{antar} sub-period touches the {_ordinals(antar_touch & set(houses))}")
        elif antar_touch & _DUSTHANA:
            score -= 1
            reasons.append(f"{antar} sub-period sits with the {_ordinals(antar_touch & _DUSTHANA)}")
        if maha != antar and _touched_houses(maha, natal, anchor) & set(houses):
            score += 1
            reasons.append(f"{maha} main period touches the purpose houses")
    jup = _house(sign_index(transit["Jupiter"]["lon"]), moon)
    if jup in _GURU_BALA:
        score += 1
        reasons.append(f"Jupiter {_ordinal(jup)} from the Moon (Guru bala)")
    sat = _house(sign_index(transit["Saturn"]["lon"]), moon)
    if sat in _SADE_SATI:
        score -= 1
        flags.append("Sade Sati")
    elif sat == 8:
        score -= 1
        flags.append("Ashtama Shani")
    standing = ("strong" if score >= 2 else "fair" if score >= 1
                else "quiet" if score == 0 else "slow")
    return {"name": person["name"], "standing": standing, "score": score,
            "period": f"{lords[0]}-{lords[1]}" if lords else None,
            "reasons": reasons, "flags": flags}


def _ordinal(n: int) -> str:
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def _ordinals(houses: set[int]) -> str:
    return ", ".join(_ordinal(h) for h in sorted(houses)) + (" house" if len(houses) == 1 else " houses")


def good_months(people: list[dict], purpose: str, start: date, months: int = 12) -> dict:
    """Month-by-month standing of each person for ``purpose``, and the months
    that suit all of them.

    ``people``: ``[{"name": str, "chart": VedicChart, "time_known": bool}]``,
    two to five people. ``purpose``: a key of :data:`PURPOSES`.
    """
    if purpose not in PURPOSES:
        raise ValueError(f"Unknown purpose '{purpose}'. Known: {sorted(PURPOSES)}")
    if not 1 <= len(people) <= MAX_PEOPLE:
        raise ValueError(f"Between 1 and {MAX_PEOPLE} people")
    months = max(1, min(months, MAX_MONTHS))
    houses = PURPOSES[purpose]["houses"]
    dashas = [p["chart"].dashas(None) for p in people]

    rows = []
    totals = {p["name"]: 0 for p in people}
    for when in _months(start, months):
        jd = swe.julday(when.year, when.month, when.day, 6.5)  # noon IST
        transit = sidereal_positions(jd, people[0]["chart"].ayanamsha)
        each = [_person_month(p, d, when, houses, transit) for p, d in zip(people, dashas)]
        for row in each:
            totals[row["name"]] += row["score"]
        slow = [r["name"] for r in each if r["standing"] == "slow"]
        strong = sum(r["standing"] == "strong" for r in each)
        together = ("mixed" if slow
                    else "good" if strong * 2 >= len(each)
                    else "fair")
        rows.append({"month": when.strftime("%Y-%m"), "label": when.strftime("%B %Y"),
                     "together": together, "slow_for": slow, "people": each})

    good = [r["label"] for r in rows if r["together"] == "good"]
    ranked = sorted(totals.items(), key=lambda kv: -kv[1])
    stronger = None
    if len(ranked) > 1 and ranked[0][1] - ranked[1][1] >= max(2, months // 3):
        stronger = ranked[0][0]
    return {
        "purpose": purpose,
        "purpose_label": PURPOSES[purpose]["label"],
        "houses": list(houses),
        "months": rows,
        "good_months": good,
        "stronger_phase": stronger,
        "time_unknown_for": [p["name"] for p in people if not p.get("time_known", True)],
        "rules": RULES_NOTE,
        "is_convention_dependent": True,
        "observance_note": (
            "Period and transit timing is one view among several; astrologers "
            "also weigh divisional charts and Ashtakavarga. Use these months to "
            "plan, not as a verdict on the purchase or the venture."
        ),
    }
