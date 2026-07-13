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
    PLANET_METALS, PLANET_DIRECTIONS, SIGN_LORDS, OWN_SIGNS,
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
