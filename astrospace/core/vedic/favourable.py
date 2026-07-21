"""
Favourable points — lucky numbers, days, planets, gem, metal, direction.

Derivations:
- Lucky/root number: digital root of the birth day-of-month; good/evil
  numbers from the numerology table (VERIFY — convention-dependent).
- Good years: calendar ages whose digital root equals the root number.
- Good/evil planets: functional benefics/malefics for the lagna
  (Parashari house-lordship principles, VERIFY).
- Lucky days: weekdays of the good planets.
- Gem/metal/direction/time: associations of the lagna lord.
"""
from .constants import (
    NUMEROLOGY, FUNCTIONAL_BY_LAGNA, PLANET_DAYS, PLANET_GEMS,
    PLANET_METALS, PLANET_DIRECTIONS, PLANET_NUMBER, SIGN_LORDS, OWN_SIGNS,
)
from .positions import sign_name


def digital_root(n: int) -> int:
    while n > 9:
        n = sum(int(c) for c in str(n))
    return n


def favourable_points(birth_day: int, lagna_sign: int) -> dict:
    root = digital_root(birth_day)
    num = NUMEROLOGY[root]
    functional = FUNCTIONAL_BY_LAGNA[lagna_sign % 12]
    good_planets = functional["benefics"]
    evil_planets = functional["malefics"]
    lagna_lord = SIGN_LORDS[lagna_sign % 12]

    good_years = [y for y in range(1, 100) if digital_root(y) == root][:8]
    lucky_days = [PLANET_DAYS[p] for p in good_planets if p in PLANET_DAYS]
    friendly_signs = sorted({
        sign_name(s) for p in good_planets for s in OWN_SIGNS.get(p, [])
    })

    return {
        "lucky_number": root,
        "ruling_planet": num["planet"],
        "good_numbers": num["good"],
        "evil_numbers": num["evil"],
        "good_years": good_years,
        "lucky_days": lucky_days,
        "good_planets": good_planets,
        "evil_planets": evil_planets,
        "yogakaraka": functional["yogakaraka"],
        "friendly_signs": friendly_signs,
        "lucky_metal": PLANET_METALS[lagna_lord],
        "lucky_stone": PLANET_GEMS[lagna_lord],
        "lucky_direction": PLANET_DIRECTIONS[lagna_lord],
        "lucky_time": f"Hora of {lagna_lord}" + (" (sunrise)" if lagna_lord == "Sun" else ""),
    }


def astrological_lucky_number(lagna_sign: int, moon_sign: int,
                              nakshatra_lord: str, atmakaraka: str) -> dict:
    """Chart-derived lucky number — distinct from the numerology moolank.

    This is the OTHER convention for a "lucky number": instead of reducing
    the birth date, several jyotisha traditions assign the number of the
    planet that rules a key chart point. The lagna lord (ascendant ruler) is
    the most commonly cited primary source, since it governs the native's
    overall identity and fortune; the rashi (Moon-sign) lord, the birth
    nakshatra's lord, and the Jaimini Atmakaraka (soul planet) are checked as
    supporting witnesses. When one or more agree with the lagna lord, the
    number is reported as more strongly confirmed by the chart.
    """
    lagna_lord = SIGN_LORDS[lagna_sign % 12]
    rashi_lord = SIGN_LORDS[moon_sign % 12]
    witnesses = [
        {"label": "Lagna lord", "planet": lagna_lord},
        {"label": "Rashi (Moon) lord", "planet": rashi_lord},
        {"label": "Nakshatra lord", "planet": nakshatra_lord},
        {"label": "Atmakaraka", "planet": atmakaraka},
    ]
    for w in witnesses:
        w["number"] = PLANET_NUMBER.get(w["planet"])

    primary_number = PLANET_NUMBER[lagna_lord]
    confirmed_by = [
        w["label"] for w in witnesses[1:] if w["number"] == primary_number
    ]
    return {
        "number": primary_number,
        "planet": lagna_lord,
        "source": "Lagna lord (ascendant ruler) — the chart's primary identity indicator",
        "witnesses": witnesses,
        "confirmed_by": confirmed_by,
        "confirmation_count": len(confirmed_by),
    }
