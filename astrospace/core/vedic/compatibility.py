"""Compatibility / Gun Milan calculations."""
from __future__ import annotations

from .constants import NAKSHATRAS, NATURAL_RELATIONS, SIGNS, SIGN_LORDS

VARNA_RANK = {"Shudra": 1, "Vaishya": 2, "Kshatriya": 3, "Brahmin": 4}
# 0-based tara cycle. Classical Tara koota treats Vipat, Pratyari and
# Vadha as the primary unfavourable taras; Janma and Parama Mitra must not
# be dropped from scoring.
# Externally confirmed 2026-07-14 via
# https://jagannathhora.com/tara-koot-birth-star-compatibility/ — the malefic
# zero-point taras are Vipat (3rd), Pratyari (5th) and Vadha (7th) (inclusive
# count from birth nakshatra, divide by 9, remainder = tara number), with 1.5
# points awarded per auspicious direction. Our 0-based remainders {2, 4, 6}
# are exactly the 3rd/5th/7th taras of that 1-based convention.
UNFAVOURABLE_TARA_REMAINDERS = {2, 4, 6}
BHAKOOT_DOSHA_PAIRS = {(2, 12), (12, 2), (5, 9), (9, 5), (6, 8), (8, 6)}
YONI_ENEMY_PAIRS = {
    frozenset(pair)
    for pair in (
        ("Horse", "Buffalo"),
        ("Elephant", "Lion"),
        ("Sheep", "Monkey"),
        ("Serpent", "Mongoose"),
        ("Dog", "Deer"),
        ("Cat", "Rat"),
        ("Cow", "Tiger"),
    )
}

# ── Yoni: full 14×14 classical Melapak matrix ────────────────────────────────
# Points: 4 same, 3 friendly, 2 neutral, 1 hostile, 0 sworn enemy.
# Standard published matrix used by common Indian software (Horoscope
# Explorer / JHora family). Diagonal (4) and the 7 sworn-enemy pairs (0)
# are the universally agreed anchors; the intermediate 1/2/3 grades follow
# the common convention and remain verified=False pending golden-chart
# validation.
#
# External cross-check 2026-07-14 against the full 14×14 table published at
# https://saravali.github.io/astrology/koota_yoni.html (the Maitreya software
# convention): 193 of 196 cells match this matrix exactly, including all
# diagonal and sworn-enemy anchors. Three pairs DISAGREE and that source is
# internally asymmetric on two of them, so our values were kept unchanged:
#   Horse↔Cow    — ours 3/3, Saravali 1/1
#   Horse↔Deer   — ours 1/1, Saravali 3 (Horse→Deer) but 1 (Deer→Horse)
#   Lion↔Buffalo — ours 1/1, Saravali 2 (Lion→Buffalo) but 1 (Buffalo→Lion)
# The 7 sworn-enemy pairs and the 4/3/2/1/0 grading scheme were additionally
# confirmed at https://jagannathhora.com/yoni-koot-yoni-milan-explained/
# (accessed 2026-07-14). Because full-matrix confirmation failed on those
# three pairs and only one full published matrix was fetchable, the graded
# 1/2/3 cells stay verified=False (see _yoni below).
YONI_ORDER = [
    "Horse", "Elephant", "Sheep", "Serpent", "Dog", "Cat", "Rat",
    "Cow", "Buffalo", "Tiger", "Deer", "Monkey", "Mongoose", "Lion",
]
_YONI_ROWS = [
    #  Hor Ele She Ser Dog Cat Rat Cow Buf Tig Dee Mon Mng Lio
    [4, 2, 2, 3, 2, 2, 2, 3, 0, 1, 1, 3, 2, 1],  # Horse
    [2, 4, 3, 3, 2, 2, 2, 2, 3, 1, 2, 3, 2, 0],  # Elephant
    [2, 3, 4, 2, 1, 2, 1, 3, 3, 1, 2, 0, 3, 1],  # Sheep
    [3, 3, 2, 4, 2, 1, 1, 1, 1, 2, 2, 2, 0, 2],  # Serpent
    [2, 2, 1, 2, 4, 2, 1, 2, 2, 1, 0, 2, 1, 1],  # Dog
    [2, 2, 2, 1, 2, 4, 0, 2, 2, 1, 3, 3, 2, 1],  # Cat
    [2, 2, 1, 1, 1, 0, 4, 2, 2, 2, 2, 2, 1, 2],  # Rat
    [3, 2, 3, 1, 2, 2, 2, 4, 3, 0, 3, 2, 2, 1],  # Cow
    [0, 3, 3, 1, 2, 2, 2, 3, 4, 1, 2, 2, 2, 1],  # Buffalo
    [1, 1, 1, 2, 1, 1, 2, 0, 1, 4, 1, 1, 2, 1],  # Tiger
    [1, 2, 2, 2, 0, 3, 2, 3, 2, 1, 4, 2, 2, 1],  # Deer
    [3, 3, 0, 2, 2, 3, 2, 2, 2, 1, 2, 4, 3, 2],  # Monkey
    [2, 2, 3, 0, 1, 2, 1, 2, 2, 2, 2, 3, 4, 2],  # Mongoose
    [1, 0, 1, 2, 1, 1, 2, 1, 1, 1, 1, 2, 2, 4],  # Lion
]
YONI_MATRIX = {
    row_animal: {col_animal: _YONI_ROWS[i][j] for j, col_animal in enumerate(YONI_ORDER)}
    for i, row_animal in enumerate(YONI_ORDER)
}

# ── Vashya: 5-group classical matrix ─────────────────────────────────────────
# Directional: rows are the groom's (person1) Moon-sign vashya group,
# columns the bride's (person2). Symmetry is NOT a requirement of the koota —
# vashya expresses control of one group over the other — though most values
# in this common software convention happen to coincide across directions.
# Convention-dependent (verified=False) pending golden-chart validation.
#
# External cross-check 2026-07-14: the vashya points table published at
# https://www.anytimeastro.com/blog/astrology/vasya-koota/ (bride-row ×
# groom-column) DISAGREES with this matrix in several cells — it uses a
# 2/1.5/1/0 grading (e.g. Manava↔Jalachara 1.5, Chatushpada(bride)×
# Vanachara(groom) 1.5, Vanachara(bride) row all-0 against other groups)
# where this matrix uses the 2/1/0.5/0 convention. Published vashya tables
# also disagree with EACH OTHER (e.g.
# https://astrosight.ai/kundli/vashya-koota-importance describes 0.5-point
# neutral grades and Chatushpada–Vanachara = 0). Values kept unchanged and
# verified stays False until an authoritative table matching one convention
# is confirmed.
VASHYA_GROUPS = ["Chatushpada", "Manava", "Jalachara", "Vanachara", "Keeta"]
_VASHYA_ROWS = [
    #  Chat  Man   Jal   Van   Kee
    [2.0, 1.0, 1.0, 0.5, 1.0],  # Chatushpada (groom)
    [1.0, 2.0, 0.5, 0.0, 1.0],  # Manava (groom)
    [1.0, 0.5, 2.0, 1.0, 1.0],  # Jalachara (groom)
    [0.5, 0.0, 1.0, 2.0, 0.0],  # Vanachara (groom)
    [1.0, 1.0, 1.0, 0.0, 2.0],  # Keeta (groom)
]
VASHYA_MATRIX = {
    groom: {bride: _VASHYA_ROWS[i][j] for j, bride in enumerate(VASHYA_GROUPS)}
    for i, groom in enumerate(VASHYA_GROUPS)
}
GRAHA_MAITRI_POINTS = {
    ("friend", "friend"): 5,
    ("friend", "neutral"): 4,
    ("neutral", "friend"): 4,
    ("neutral", "neutral"): 3,
    ("friend", "enemy"): 1,
    ("enemy", "friend"): 1,
    ("neutral", "enemy"): 0.5,
    ("enemy", "neutral"): 0.5,
    ("enemy", "enemy"): 0,
}


def _av(chart, key: str) -> str:
    value = chart.avkahada().get(key)
    return "—" if value in (None, "") else str(value)


def _planet(chart, planet: str, key: str) -> str:
    value = chart.planet_details().get(planet, {}).get(key)
    return "—" if value in (None, "") else str(value)


def _yoni_animal(value: str) -> str:
    return (value.split("(")[0].strip() or "—")


def _planet_relation_class(a: str, b: str) -> str:
    if a == b:
        return "same"
    relation = NATURAL_RELATIONS.get(a)
    if not relation:
        return "neutral"
    if b in relation["friends"]:
        return "friend"
    if b in relation["neutrals"]:
        return "neutral"
    return "enemy"


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
    points = 1 if VARNA_RANK.get(a, 0) >= VARNA_RANK.get(b, 0) else 0
    return _row("Varna", points, 1, f"{a} with {b}; person1 treated as groom for Varna convention")


def _vashya(chart_a, chart_b) -> dict:
    a = _av(chart_a, "vashya")
    b = _av(chart_b, "vashya")
    if a not in VASHYA_MATRIX or b not in VASHYA_MATRIX:
        return _row("Vashya", 0, 2, f"{a} with {b}; vashya group unavailable", verified=False)
    points = VASHYA_MATRIX[a][b]
    note = f"{a} (person1/groom) with {b} (person2); directional group matrix"
    return _row("Vashya", points, 2, note, verified=False)


def _tara(chart_a, chart_b) -> dict:
    a_name = _planet(chart_a, "Moon", "nakshatra")
    b_name = _planet(chart_b, "Moon", "nakshatra")
    if a_name not in NAKSHATRAS or b_name not in NAKSHATRAS:
        return _row("Tara", 0, 3, "Moon nakshatra unavailable")
    ai = NAKSHATRAS.index(a_name)
    bi = NAKSHATRAS.index(b_name)
    a_to_b = ((bi - ai) % 27) % 9
    b_to_a = ((ai - bi) % 27) % 9
    points = (0 if a_to_b in UNFAVOURABLE_TARA_REMAINDERS else 1.5)
    points += 0 if b_to_a in UNFAVOURABLE_TARA_REMAINDERS else 1.5
    return _row("Tara", points, 3, f"{a_name} ↔ {b_name}")


def _yoni(chart_a, chart_b) -> dict:
    a = _yoni_animal(_av(chart_a, "yoni"))
    b = _yoni_animal(_av(chart_b, "yoni"))
    if a not in YONI_MATRIX or b not in YONI_MATRIX:
        return _row("Yoni", 0, 4, f"{a} with {b}; yoni animal unavailable", verified=False)
    points = YONI_MATRIX[a][b]
    grade = {4: "same yoni", 3: "friendly", 2: "neutral", 1: "hostile", 0: "sworn enemy"}[points]
    # Diagonal (same) and sworn-enemy anchors are the universally agreed
    # values; intermediate 1/2/3 grades follow the common software
    # convention pending golden-chart validation.
    anchored = a == b or frozenset((a, b)) in YONI_ENEMY_PAIRS
    return _row("Yoni", points, 4, f"{a} with {b}; {grade}", verified=anchored)


def _graha_maitri(chart_a, chart_b) -> dict:
    a = _av(chart_a, "rashi_lord")
    b = _av(chart_b, "rashi_lord")
    if a == b:
        points = 5
    else:
        rel = (_planet_relation_class(a, b), _planet_relation_class(b, a))
        points = GRAHA_MAITRI_POINTS.get(rel, 0)
    return _row("Graha Maitri", points, 5, f"{a} with {b}")


def _gana(chart_a, chart_b) -> dict:
    a = _av(chart_a, "gana")
    b = _av(chart_b, "gana")
    points = 1
    if a == b:
        points = 6
    elif {a, b} == {"Deva", "Manushya"}:
        points = 5
    elif {a, b} == {"Deva", "Rakshasa"}:
        points = 1
    elif {a, b} == {"Manushya", "Rakshasa"}:
        points = 0
    return _row("Gana", points, 6, f"{a} with {b}")


def _mutual_natural_friends(lord_a: str, lord_b: str) -> bool:
    """True when each planet lists the other among its natural friends."""
    rel_a = NATURAL_RELATIONS.get(lord_a)
    rel_b = NATURAL_RELATIONS.get(lord_b)
    if not rel_a or not rel_b:
        return False
    return lord_b in rel_a["friends"] and lord_a in rel_b["friends"]


def _bhakoot(chart_a, chart_b) -> dict:
    a = _planet(chart_a, "Moon", "sign")
    b = _planet(chart_b, "Moon", "sign")
    if a not in SIGNS or b not in SIGNS:
        return _row("Bhakoot", 0, 7, "Moon rashi unavailable")
    ai = SIGNS.index(a)
    bi = SIGNS.index(b)
    a_to_b = ((bi - ai) % 12) + 1
    b_to_a = ((ai - bi) % 12) + 1
    if (a_to_b, b_to_a) not in BHAKOOT_DOSHA_PAIRS:
        return _row("Bhakoot", 7, 7, f"{a} {a_to_b}/{b_to_a} {b}")

    # Bhakoot dosha (6/8, 5/9, 2/12): cancelled when the two Moon-sign lords
    # are the same planet or mutual natural friends. Convention-dependent.
    lord_a = SIGN_LORDS[ai]
    lord_b = SIGN_LORDS[bi]
    if lord_a == lord_b:
        reason = f"both rashi lords are {lord_a}"
    elif _mutual_natural_friends(lord_a, lord_b):
        reason = f"rashi lords {lord_a} and {lord_b} are mutual natural friends"
    else:
        reason = None
    if reason:
        return _row(
            "Bhakoot", 7, 7,
            f"{a} {a_to_b}/{b_to_a} {b}; bhakoot dosha cancelled: {reason}",
            verified=False,
        )
    return _row("Bhakoot", 0, 7, f"{a} {a_to_b}/{b_to_a} {b}; bhakoot dosha")


def _nadi(chart_a, chart_b) -> dict:
    a = _av(chart_a, "nadi")
    b = _av(chart_b, "nadi")
    if a != b:
        return _row("Nadi", 8, 8, f"{a} with {b}")

    # Nadi dosha (same nadi): standard cancellations, convention-dependent.
    sign_a = _planet(chart_a, "Moon", "sign")
    sign_b = _planet(chart_b, "Moon", "sign")
    nak_a = _planet(chart_a, "Moon", "nakshatra")
    nak_b = _planet(chart_b, "Moon", "nakshatra")
    pada_a = _planet(chart_a, "Moon", "nakshatra_pada")
    pada_b = _planet(chart_b, "Moon", "nakshatra_pada")

    reason = None
    if sign_a != "—" and sign_a == sign_b and nak_a != nak_b:
        reason = "same rashi, different nakshatras"
    elif nak_a != "—" and nak_a == nak_b and sign_a != sign_b:
        reason = "same nakshatra, different rashis"
    elif nak_a != "—" and nak_a == nak_b and pada_a != "—" and pada_a != pada_b:
        reason = "same nakshatra, different padas"

    if reason:
        return _row(
            "Nadi", 8, 8,
            f"{a} with {b}; nadi dosha cancelled: {reason}",
            verified=False,
        )
    return _row("Nadi", 0, 8, f"{a} with {b}; nadi dosha")


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
            "Vashya, intermediate Yoni grades, and Nadi/Bhakoot cancellation rules are convention-dependent and marked with verified=false until golden-chart validation.",
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
