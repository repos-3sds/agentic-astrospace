"""Jaimini chara karakas and arudha padas.

Sources:
- Chara karakas: BPHS ch. 32 / Jaimini Upadesa Sutras 1.1.10-18. Planets
  are ranked by advancement within their sign (degree in sign, highest
  first). In the eight-karaka scheme Rahu participates with a reversed
  degree (30 - degree_in_sign) because the nodes move backwards.
- Arudha padas: BPHS ch. 29 (Padas). The arudha of a house is as far
  removed from the house lord as the lord is from the house. If the count
  lands in the house itself or the 7th from it, the 10th therefrom is
  taken instead (the classical exception).

All functions are pure: they take a positions dict
{planet: {"lon": float, ...}} with sidereal longitudes and a lagna sign
index; nothing is computed from ephemerides here.
"""
from __future__ import annotations

from .constants import SIGN_LORDS
from .positions import degree_in_sign, sign_index, sign_name

# Karaka order, most advanced planet first (BPHS eight-karaka scheme).
KARAKA_ORDER_EIGHT = [
    ("AK", "Atmakaraka"),
    ("AmK", "Amatyakaraka"),
    ("BK", "Bhratrikaraka"),
    ("MK", "Matrikaraka"),
    ("PK", "Putrakaraka"),
    ("PiK", "Pitrikaraka"),
    ("GK", "Gnatikaraka"),
    ("DK", "Darakaraka"),
]

# Seven-karaka scheme: Sun..Saturn only (no Rahu) and no Pitrikaraka.
KARAKA_ORDER_SEVEN = [
    ("AK", "Atmakaraka"),
    ("AmK", "Amatyakaraka"),
    ("BK", "Bhratrikaraka"),
    ("MK", "Matrikaraka"),
    ("PK", "Putrakaraka"),
    ("GK", "Gnatikaraka"),
    ("DK", "Darakaraka"),
]

_SEVEN_PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
_EIGHT_PLANETS = _SEVEN_PLANETS + ["Rahu"]


def _karaka_entries(positions: dict, planets: list[str]) -> list[dict]:
    entries = []
    for planet in planets:
        lon = positions[planet]["lon"] % 360.0
        deg = degree_in_sign(lon)
        effective = 30.0 - deg if planet == "Rahu" else deg
        entries.append({
            "planet": planet,
            "longitude": lon,
            "degree_in_sign": deg,
            "effective_degree": effective,
        })
    return entries


def chara_karakas(positions: dict, scheme: str = "eight") -> dict:
    """Jaimini chara karakas from sidereal positions.

    scheme="eight" (default, standard Jaimini per BPHS): Sun..Saturn plus
    Rahu, with Rahu counted in reverse (effective degree = 30 - degree in
    sign); the eight karakas include Pitrikaraka. scheme="seven": the
    seven classical planets only, without Rahu and without Pitrikaraka.

    Returns {"scheme", "karakas": {code: {planet, karaka, degree_in_sign,
    effective_degree, longitude}}, "ordered": [...], "notes": [...]}.
    Ties identical to the arc-second are noted; ranking still resolves by
    the full float degree comparison.
    """
    if scheme == "eight":
        planets, order = _EIGHT_PLANETS, KARAKA_ORDER_EIGHT
    elif scheme == "seven":
        planets, order = _SEVEN_PLANETS, KARAKA_ORDER_SEVEN
    else:
        raise ValueError(f"Unknown chara karaka scheme {scheme!r}; options: 'eight', 'seven'")

    entries = _karaka_entries(positions, planets)
    ranked = sorted(entries, key=lambda e: e["effective_degree"], reverse=True)

    notes = [
        "Eight-karaka scheme (BPHS): Sun..Saturn + Rahu; Rahu's degree counts in "
        "reverse (30 - degree in sign)."
        if scheme == "eight" else
        "Seven-karaka scheme: Sun..Saturn only; no Rahu and no Pitrikaraka (PiK).",
        "Planets ranked by degree within sign, highest first; ties resolved by "
        "minutes then seconds (full float comparison).",
    ]
    for a, b in zip(ranked, ranked[1:]):
        if round(a["effective_degree"] * 3600) == round(b["effective_degree"] * 3600):
            notes.append(
                f"Tie to the arc-second between {a['planet']} and {b['planet']}; "
                "resolved by exact degree comparison."
            )

    karakas = {}
    ordered = []
    for (code, karaka_name), entry in zip(order, ranked):
        row = {
            "planet": entry["planet"],
            "karaka": karaka_name,
            "degree_in_sign": entry["degree_in_sign"],
            "effective_degree": entry["effective_degree"],
            "longitude": entry["longitude"],
        }
        karakas[code] = row
        ordered.append({"code": code, **row})

    return {"scheme": scheme, "karakas": karakas, "ordered": ordered, "notes": notes}


# ── Arudha padas ─────────────────────────────────────────────────────────────

def arudha_pada_detail(house_number: int, lagna_sign: int, positions: dict) -> dict:
    """Arudha pada of a whole-sign house with the working shown.

    house sign L = (lagna_sign + house - 1) % 12; lord's sign S; inclusive
    count n = (S - L) % 12; raw arudha = (S + n) % 12 (as far from the lord
    as the lord is from the house). Exception (BPHS): if the raw arudha is
    the house itself or the 7th from it, take the 10th therefrom
    (arudha = (raw + 9) % 12).

    For Scorpio and Aquarius the primary lords Mars and Saturn are used
    (dual-lordship with Ketu/Rahu; the stronger-lord variant is pending).

    Returns {"house", "house_sign", "lord", "lord_sign", "count",
             "raw_sign", "exception_applied", "sign", "sign_name"}.
    """
    if not 1 <= house_number <= 12:
        raise ValueError(f"house_number must be 1..12, got {house_number}")
    house_sign = (lagna_sign + house_number - 1) % 12
    lord = SIGN_LORDS[house_sign]
    lord_sign = sign_index(positions[lord]["lon"])
    count = (lord_sign - house_sign) % 12
    raw = (lord_sign + count) % 12
    exception = raw == house_sign or raw == (house_sign + 6) % 12
    final = (raw + 9) % 12 if exception else raw
    return {
        "house": house_number,
        "house_sign": house_sign,
        "house_sign_name": sign_name(house_sign),
        "lord": lord,
        "lord_sign": lord_sign,
        "lord_sign_name": sign_name(lord_sign),
        "count": count,
        "raw_sign": raw,
        "raw_sign_name": sign_name(raw),
        "exception_applied": exception,
        "sign": final,
        "sign_name": sign_name(final),
    }


def arudha_pada(house_number: int, lagna_sign: int, positions: dict) -> int:
    """Arudha pada sign index (0..11) of a whole-sign house."""
    return arudha_pada_detail(house_number, lagna_sign, positions)["sign"]


def arudha_lagna(lagna_sign: int, positions: dict) -> dict:
    """Arudha Lagna (A1): arudha of the 1st house."""
    return arudha_pada_detail(1, lagna_sign, positions)


def upapada(lagna_sign: int, positions: dict) -> dict:
    """Upapada Lagna (UL, A12): arudha of the 12th house."""
    return arudha_pada_detail(12, lagna_sign, positions)


def arudha_padas(lagna_sign: int, positions: dict) -> dict:
    """All twelve arudha padas A1..A12 plus AL/UL aliases and conventions."""
    padas = {f"A{h}": arudha_pada_detail(h, lagna_sign, positions) for h in range(1, 13)}
    return {
        "padas": padas,
        "arudha_lagna": padas["A1"],
        "upapada": padas["A12"],
        "notes": [
            "Whole-sign houses from the lagna sign.",
            "Exception (BPHS ch.29): an arudha falling in its own house or the 7th "
            "from it is moved to the 10th therefrom.",
            "Scorpio and Aquarius use their primary lords Mars and Saturn "
            "(dual-lordship with Ketu/Rahu; stronger-lord variant pending).",
        ],
    }
