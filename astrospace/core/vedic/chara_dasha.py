"""Jaimini Chara Dasha — the sign-based (rashi) mahadasha system.

Unlike Vimshottari (planet-based periods from the Moon's nakshatra), Chara
Dasha assigns time periods to the twelve rashis themselves, starting from
the Lagna sign. Sources cross-checked for this implementation (see
docs/backend_astro_depth_checklist_2026-08-06.md T1.2):

- Savya ("direct-footed") signs: Aries, Taurus, Gemini, Libra, Scorpio,
  Sagittarius. Apasavya ("reverse-footed"): Cancer, Leo, Virgo, Capricorn,
  Aquarius, Pisces.
- Direction: judged from the sign 9th from Lagna. Savya there -> the whole
  dasha sequence runs direct (zodiacal: Aries, Taurus, Gemini, ...).
  Apasavya there -> reverse (anti-zodiacal: Aries, Pisces, Aquarius, ...).
  This one direction governs both which sign follows which, and which way
  each sign's own duration is counted.
- Duration of a sign's mahadasha: count inclusively from the sign to the
  sign occupied by its own lord, in the chart's direction, then subtract
  one. If the lord sits in its own sign (count = 1), the sign gets the
  full 12 years instead of 1-1=0. This gives each sign 1-12 years, so the
  full 12-sign cycle length varies by chart (unlike Vimshottari's fixed
  120-year cycle) — usually somewhere in the 60-100 year range.
- Worked example cross-checked in this implementation's tests: an Aries
  dasha (direct) with Mars in the 5th house from Aries counts to 5, so the
  duration is 5-1 = 4 years; a Leo dasha (indirect) with its own lord Sun
  in Leo gets the full 12 years.

Scorpio and Aquarius use AstroSpace's existing primary-lord convention
(Mars, Saturn — see constants.SIGN_LORDS and
docs/jaimini_validation_2026-08-06.md's dual-lordship section), not a
stronger-lord variant.

Antardashas (bhukti): this implementation divides each mahadasha's years
into twelve equal parts across all twelve signs in the same chart-wide
direction, starting from the mahadasha's own sign. Classical sources are
not unanimous that Chara Dasha bhuktis are equal divisions rather than
their own count-to-lord sub-periods; this is a deliberate, documented
convention (the most common software default), not a claim that it is the
only classical method — hence ``source_status: convention_dependent``.

Narayana Dasha (the Lagna/7th-anchored sibling system) is deliberately NOT
implemented here: published secondary sources disagree on its
starting-sign-strength rule and its fixed/dual stepping pattern in ways
this pass could not resolve against a primary source. Shipping a guessed
algorithm for a dasha system is worse than not shipping it — see the
checklist for what a future pass needs before adding it.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from .constants import SIGN_LORDS
from .positions import sign_index, sign_name

DAYS_PER_YEAR = 365.25

# Savya (direct-footed): Aries, Taurus, Gemini, Libra, Scorpio, Sagittarius.
SAVYA_SIGNS = {0, 1, 2, 6, 7, 8}
# Apasavya (reverse-footed): Cancer, Leo, Virgo, Capricorn, Aquarius, Pisces.
APASAVYA_SIGNS = {3, 4, 5, 9, 10, 11}


def _add_years(dt: datetime, years: float) -> datetime:
    return dt + timedelta(days=years * DAYS_PER_YEAR)


def chart_direction(lagna_sign: int) -> str:
    """"direct" or "reverse", from the savya/apasavya class of the 9th from Lagna."""
    ninth = (lagna_sign + 8) % 12
    return "direct" if ninth in SAVYA_SIGNS else "reverse"


def _count_to_lord(dasha_sign: int, lord_sign: int, direction: str) -> int:
    """Inclusive sign-count from dasha_sign to lord_sign, in the given direction."""
    if direction == "direct":
        return (lord_sign - dasha_sign) % 12 + 1
    return (dasha_sign - lord_sign) % 12 + 1


def sign_duration_years(sign: int, positions: dict, direction: str) -> int:
    """Years for one sign's Chara mahadasha: count-to-lord minus one, or 12
    if the lord occupies its own sign (count == 1)."""
    lord = SIGN_LORDS[sign]
    lord_sign = sign_index(positions[lord]["lon"])
    count = _count_to_lord(sign, lord_sign, direction)
    return 12 if count == 1 else count - 1


def _sign_sequence(start_sign: int, direction: str) -> list[int]:
    step = 1 if direction == "direct" else -1
    return [(start_sign + step * i) % 12 for i in range(12)]


def _antardashas(mahadasha_sign: int, start: datetime, years: float,
                 direction: str, as_of: datetime | None) -> list[dict]:
    out = []
    cursor = start
    per_sign = years / 12.0
    for sign in _sign_sequence(mahadasha_sign, direction):
        end = _add_years(cursor, per_sign)
        out.append({
            "sign": sign,
            "sign_name": sign_name(sign),
            "lord": SIGN_LORDS[sign],
            "start": cursor.isoformat(),
            "end": end.isoformat(),
            "years": round(per_sign, 6),
            "active": bool(as_of and cursor <= as_of < end),
        })
        cursor = end
    return out


def chara_dasha(lagna_sign: int, positions: dict, birth_dt: datetime,
                as_of: datetime | None = None) -> dict:
    """Jaimini Chara Dasha mahadasha sequence starting from Lagna.

    Returns ``{"direction", "ninth_from_lagna", "mahadashas": [...],
    "current": {"mahadasha", "antardasha"}, "total_years", "source_status",
    "notes"}``. Each mahadasha has ``sign``, ``sign_name``, ``lord``,
    ``start``, ``end``, ``years``, ``active``, and ``antardashas``.
    """
    direction = chart_direction(lagna_sign)
    sequence = _sign_sequence(lagna_sign, direction)

    mahadashas = []
    cursor = birth_dt
    for sign in sequence:
        years = sign_duration_years(sign, positions, direction)
        end = _add_years(cursor, years)
        mahadashas.append({
            "sign": sign,
            "sign_name": sign_name(sign),
            "lord": SIGN_LORDS[sign],
            "start": cursor.isoformat(),
            "end": end.isoformat(),
            "years": years,
            "active": bool(as_of and cursor <= as_of < end),
            "antardashas": _antardashas(sign, cursor, years, direction, as_of),
        })
        cursor = end

    current_md = next((m for m in mahadashas if m["active"]), None)
    current_ad = None
    if current_md:
        current_ad = next((a for a in current_md["antardashas"] if a["active"]), None)

    return {
        "direction": direction,
        "ninth_from_lagna": sign_name((lagna_sign + 8) % 12),
        "mahadashas": mahadashas,
        "current": {"mahadasha": current_md, "antardasha": current_ad},
        "total_years": round(sum(m["years"] for m in mahadashas), 6),
        "source_status": "convention_dependent",
        "notes": [
            "Direction from the 9th-from-Lagna savya/apasavya rule; duration "
            "per sign from the count-to-lord rule (own-sign lord = 12 years).",
            "Antardashas are equal 12-way divisions of the mahadasha, in the "
            "same chart direction, starting from the mahadasha's own sign — "
            "a documented convention, not the only method in circulation.",
            "Scorpio/Aquarius use AstroSpace's primary-lord convention (Mars, "
            "Saturn) — see docs/jaimini_validation_2026-08-06.md.",
            "Total cycle length varies by chart (each sign gets 1-12 years); "
            "there is no fixed total the way Vimshottari sums to 120 years.",
        ],
    }
