"""Compatibility / Gun Milan calculations."""
from __future__ import annotations

from .constants import NAKSHATRAS, NATURAL_RELATIONS, SIGNS

VARNA_RANK = {"Shudra": 1, "Vaishya": 2, "Kshatriya": 3, "Brahmin": 4}
FAVOURABLE_TARA_REMAINDERS = {1, 3, 5, 7}
BHAKOOT_DOSHA_PAIRS = {(2, 12), (12, 2), (5, 9), (9, 5), (6, 8), (8, 6)}


def _av(chart, key: str) -> str:
    value = chart.avkahada().get(key)
    return "—" if value in (None, "") else str(value)


def _planet(chart, planet: str, key: str) -> str:
    value = chart.planet_details().get(planet, {}).get(key)
    return "—" if value in (None, "") else str(value)


def _yoni_animal(value: str) -> str:
    return (value.split("(")[0].strip() or "—")


def _planet_relation(a: str, b: str) -> float:
    if a == b:
        return 1.0
    relation = NATURAL_RELATIONS.get(a)
    if not relation:
        return 0.45
    if b in relation["friends"]:
        return 0.9
    if b in relation["neutrals"]:
        return 0.6
    return 0.25


def _row(label: str, points: float, max_points: int, note: str, verified: bool = True) -> dict:
    points = round(points, 1)
    return {
        "label": label,
        "points": points,
        "max": max_points,
        "note": note,
        "verified": verified,
    }


def _varna(chart_a, chart_b) -> dict:
    a = _av(chart_a, "varna")
    b = _av(chart_b, "varna")
    points = 1 if a == b else (0.5 if VARNA_RANK.get(a, 0) >= VARNA_RANK.get(b, 0) else 0)
    return _row("Varna", points, 1, f"{a} with {b}")


def _vashya(chart_a, chart_b) -> dict:
    a = _av(chart_a, "vashya")
    b = _av(chart_b, "vashya")
    points = 2 if a == b else (1 if "Manava" in (a, b) else 0.5)
    return _row("Vashya", points, 2, f"{a} with {b}", verified=False)


def _tara(chart_a, chart_b) -> dict:
    a_name = _planet(chart_a, "Moon", "nakshatra")
    b_name = _planet(chart_b, "Moon", "nakshatra")
    if a_name not in NAKSHATRAS or b_name not in NAKSHATRAS:
        return _row("Tara", 0, 3, "Moon nakshatra unavailable")
    ai = NAKSHATRAS.index(a_name)
    bi = NAKSHATRAS.index(b_name)
    a_to_b = ((bi - ai) % 27) % 9
    b_to_a = ((ai - bi) % 27) % 9
    points = (1.5 if a_to_b in FAVOURABLE_TARA_REMAINDERS else 0)
    points += 1.5 if b_to_a in FAVOURABLE_TARA_REMAINDERS else 0
    return _row("Tara", points, 3, f"{a_name} ↔ {b_name}")


def _yoni(chart_a, chart_b) -> dict:
    a = _yoni_animal(_av(chart_a, "yoni"))
    b = _yoni_animal(_av(chart_b, "yoni"))
    points = 4 if a == b else 2
    return _row("Yoni", points, 4, f"{a} with {b}")


def _graha_maitri(chart_a, chart_b) -> dict:
    a = _av(chart_a, "rashi_lord")
    b = _av(chart_b, "rashi_lord")
    ratio = (_planet_relation(a, b) + _planet_relation(b, a)) / 2
    return _row("Graha Maitri", ratio * 5, 5, f"{a} with {b}")


def _gana(chart_a, chart_b) -> dict:
    a = _av(chart_a, "gana")
    b = _av(chart_b, "gana")
    points = 1
    if a == b:
        points = 6
    elif {a, b} == {"Deva", "Manushya"}:
        points = 5
    elif {a, b} == {"Manushya", "Rakshasa"}:
        points = 3
    return _row("Gana", points, 6, f"{a} with {b}")


def _bhakoot(chart_a, chart_b) -> dict:
    a = _planet(chart_a, "Moon", "sign")
    b = _planet(chart_b, "Moon", "sign")
    if a not in SIGNS or b not in SIGNS:
        return _row("Bhakoot", 0, 7, "Moon rashi unavailable")
    ai = SIGNS.index(a)
    bi = SIGNS.index(b)
    a_to_b = ((bi - ai) % 12) + 1
    b_to_a = ((ai - bi) % 12) + 1
    points = 0 if (a_to_b, b_to_a) in BHAKOOT_DOSHA_PAIRS else 7
    return _row("Bhakoot", points, 7, f"{a} {a_to_b}/{b_to_a} {b}")


def _nadi(chart_a, chart_b) -> dict:
    a = _av(chart_a, "nadi")
    b = _av(chart_b, "nadi")
    return _row("Nadi", 0 if a == b else 8, 8, f"{a} with {b}")


def gun_milan(chart_a, chart_b) -> dict:
    """Return an Ashta Koota style 36-point compatibility breakdown."""
    rows = [
        _varna(chart_a, chart_b),
        _vashya(chart_a, chart_b),
        _tara(chart_a, chart_b),
        _yoni(chart_a, chart_b),
        _graha_maitri(chart_a, chart_b),
        _gana(chart_a, chart_b),
        _bhakoot(chart_a, chart_b),
        _nadi(chart_a, chart_b),
    ]
    total = round(sum(row["points"] for row in rows), 1)
    max_points = sum(row["max"] for row in rows)
    percent = round((total / max_points) * 100)
    verdict = (
        "Strong Gun Milan" if total >= 28 else
        "Promising match" if total >= 22 else
        "Borderline, inspect deeply" if total >= 18 else
        "Needs careful review"
    )
    return {
        "system": "Ashta Koota / Gun Milan",
        "total": total,
        "max": max_points,
        "percent": percent,
        "verdict": verdict,
        "rows": rows,
        "notes": [
            "This is deterministic compatibility scoring; AI interpretation should explain, not calculate it.",
            "Vashya and some exception rules are convention-dependent and marked with verified=false until golden-chart validation.",
        ],
        "profiles": {
            "person1": _compat_profile(chart_a),
            "person2": _compat_profile(chart_b),
        },
    }


def _compat_profile(chart) -> dict:
    av = chart.avkahada()
    planets = chart.planet_details()
    return {
        "name": chart.name,
        "lagna": av.get("lagna"),
        "rashi": av.get("rashi"),
        "rashi_lord": av.get("rashi_lord"),
        "moon_nakshatra": planets.get("Moon", {}).get("nakshatra"),
        "moon_nakshatra_pada": planets.get("Moon", {}).get("nakshatra_pada"),
        "varna": av.get("varna"),
        "vashya": av.get("vashya"),
        "yoni": av.get("yoni"),
        "gana": av.get("gana"),
        "nadi": av.get("nadi"),
    }
