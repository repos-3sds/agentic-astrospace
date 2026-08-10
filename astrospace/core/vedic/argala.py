"""Argala and Argala-Bhanga (Virodhargala) — Jaimini's planetary-intervention
technique: which houses' occupants support ("argala") a given house's
significations, and which houses' occupants obstruct that support.

Cross-checked 2026-08-10 against two independent secondary sources that
agree on the same house positions and the same strength rule (the Jaimini
Sutramritam blog's "Argala - The Linchpin", and Asheville Vedic Astrology's
"Argala in Jaimini Upadesa Sutras", the latter itself citing Ernst
Wilhelm). No primary BPHS/Jaimini-sutra verse was located in this pass, so
this stays flagged source_status: convention_dependent, same convention
used for Indu Lagna in special_lagnas.py.

Rule, counted from the target house (whole-sign, 1..12 inclusive):
  - Primary Argala:   2nd house from the target
  - Secondary Argala: 4th house from the target
  - Tertiary Argala:  11th house from the target
  - Obstruction (Virodhargala) of each, respectively, comes from the 12th,
    10th and 3rd houses from the target.
  - Both sources state an obstruction only succeeds when its house has
    more planets than the argala house it opposes ("do not obstruct when
    small in number or weaker"); a house with fewer planets fails to
    obstruct. Neither source gives an unambiguous rule for the tied-count
    case beyond "ascertain relative strength" — this module does not
    attempt a strength tiebreak (that needs Shadbala, out of scope here)
    and instead reports a tie as "contested" rather than asserting a
    winner, to avoid overclaiming.
  - Visesha Argala: more than two malefic planets (Sun, Mars, Saturn,
    Rahu, Ketu) in the 3rd-from-target house form an argala that can
    never be obstructed, regardless of what sits in the 3rd's own
    opposer (the 9th).
  - Both sources note the 5th/9th (also trine houses) are disputed as
    additional argala positions — one source says some authors include
    them, the other doesn't resolve it — so this module does not include
    them.

This reports raw occupancy/counts and the resulting outcome only, no
interpretation of what the argala *means* for the house's significations —
consistent with this project's "raw KB, guardrails at the agent layer"
convention.
"""
from .constants import PLANETS
from .positions import house_from_lagna, sign_index

MALEFICS = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}

# Offset (0-indexed houses forward from the target) for each argala leg,
# and for the house that obstructs it (12th/10th/3rd from target respectively).
_ARGALA_OFFSET = {"2nd": 1, "4th": 3, "11th": 10}
_OBSTRUCTION_OFFSET = {"2nd": 11, "4th": 9, "11th": 2}


def _house_n_from(house: int, offset: int) -> int:
    return (house - 1 + offset) % 12 + 1


def _planets_in_house(house: int, lagna_sign: int, positions: dict) -> list[str]:
    return [
        p for p in PLANETS
        if p in positions
        and house_from_lagna(sign_index(positions[p]["lon"]), lagna_sign) == house
    ]


def _leg_outcome(argala_count: int, obstruction_count: int) -> str:
    if argala_count == 0:
        return "none"
    if obstruction_count > argala_count:
        return "obstructed"
    if obstruction_count == argala_count:
        return "contested"
    return "argala"


def argala_of_house(house: int, lagna_sign: int, positions: dict) -> dict:
    """Argala/Argala-Bhanga acting on one whole-sign house (1..12)."""
    legs = {}
    for label, offset in _ARGALA_OFFSET.items():
        argala_house = _house_n_from(house, offset)
        obstruction_house = _house_n_from(house, _OBSTRUCTION_OFFSET[label])
        argala_planets = _planets_in_house(argala_house, lagna_sign, positions)
        obstruction_planets = _planets_in_house(obstruction_house, lagna_sign, positions)
        legs[label] = {
            "argala_house": argala_house,
            "argala_planets": argala_planets,
            "obstruction_house": obstruction_house,
            "obstruction_planets": obstruction_planets,
            "outcome": _leg_outcome(len(argala_planets), len(obstruction_planets)),
        }

    third_house = _house_n_from(house, 2)
    third_malefics = [p for p in _planets_in_house(third_house, lagna_sign, positions) if p in MALEFICS]
    legs["visesha_3rd"] = {
        "house": third_house,
        "malefic_planets": third_malefics,
        "outcome": "argala" if len(third_malefics) > 2 else "none",
        "note": "More than two malefics in the 3rd from this house form an "
                "argala that is never obstructed.",
    }

    return {
        "house": house,
        "legs": legs,
        "source_status": "convention_dependent",
        "rule": (
            "Argala from the 2nd/4th/11th houses (counted from this house); "
            "obstructed by the 12th/10th/3rd respectively when the "
            "obstructing house has strictly more planets than the argala "
            "house; equal counts are reported as contested, not resolved. "
            "3+ malefics in the 3rd form an unobstructable Visesha Argala."
        ),
    }


def all_argala(lagna_sign: int, positions: dict) -> dict:
    """Argala/Argala-Bhanga for all 12 whole-sign houses."""
    return {house: argala_of_house(house, lagna_sign, positions) for house in range(1, 13)}
