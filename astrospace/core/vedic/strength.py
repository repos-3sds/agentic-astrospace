"""
Planet dignity and Shadbala v1 strength scoring.

Dignity ladder (BPHS): exalted > moolatrikona > own sign > panchadha
maitri relation with the dispositor (great friend .. great enemy) >
debilitated. The panchadha (five-fold) relation combines the permanent
natural friendship with the temporal one: the dispositor is a temporal
friend when placed 2,3,4,10,11,12 signs from the planet.

Shadbala v1 exposes the six classical strength families with a 0-100
normalization for product use. Some sub-components are exact enough for
software use (dignity-derived Sthana Bala, Dig Bala by house, Naisargika
Bala), while Kala/Cheshta/Drik are clearly marked as approximation until
reference-chart calibration is added.
"""
from datetime import timedelta
from math import asin, cos, degrees, radians, sin

from .constants import (
    EXALTATION, MOOLATRIKONA, OWN_SIGNS, NATURAL_RELATIONS, SIGN_LORDS,
    VARA_LORDS,
)
from .positions import day_span, degree_in_sign, house_from_lagna, sign_index
from .vargas import VARGA_FUNCTIONS

CLASSICAL_SHADBALA_PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]

NAISARGIKA_BALA = {
    # Traditional relative order, normalized to the strongest visible graha.
    "Sun": 60.0,
    "Moon": 51.43,
    "Venus": 42.86,
    "Jupiter": 34.29,
    "Mercury": 25.71,
    "Mars": 17.14,
    "Saturn": 8.57,
}

DIG_BALA_HOUSES = {
    "Sun": 10,
    "Mars": 10,
    "Moon": 4,
    "Venus": 4,
    "Jupiter": 1,
    "Mercury": 1,
    "Saturn": 7,
}

ASPECTS = {
    "Sun": [7],
    "Moon": [7],
    "Mars": [4, 7, 8],
    "Mercury": [7],
    "Jupiter": [5, 7, 9],
    "Venus": [7],
    "Saturn": [3, 7, 10],
}

NATURAL_BENEFICS = {"Jupiter", "Venus", "Mercury"}
NATURAL_MALEFICS = {"Sun", "Mars", "Saturn"}
PLANETARY_WAR_PLANETS = {"Mars", "Mercury", "Jupiter", "Venus", "Saturn"}

COMBUSTION_ORBS = {
    # Common whole-orb combustion thresholds in degrees from Sun.
    # Mercury/Venus retrograde-specific refinements are deferred to golden validation.
    "Moon": 12.0,
    "Mars": 17.0,
    "Mercury": 14.0,
    "Jupiter": 11.0,
    "Venus": 10.0,
    "Saturn": 15.0,
}

AVASTHA_MODIFIERS = {
    "Bala": -3.0,
    "Kumara": 3.0,
    "Yuva": 8.0,
    "Vriddha": -6.0,
    "Mrita": -12.0,
}

DIGNITY_SCORES = {
    "Exalted": 100, "Moolatrikona": 90, "Own": 85,
    "Great Friend": 75, "Friend": 65, "Neutral": 50,
    "Enemy": 35, "Great Enemy": 25, "Debilitated": 10,
}

_TEMPORAL_FRIEND_HOUSES = {2, 3, 4, 10, 11, 12}


def natural_relation(planet: str, other: str) -> str:
    rel = NATURAL_RELATIONS[planet]
    if other in rel["friends"]:
        return "friend"
    if other in rel["enemies"]:
        return "enemy"
    return "neutral"


def temporal_relation(planet_sign: int, other_sign: int) -> str:
    dist = (other_sign - planet_sign) % 12 + 1
    return "friend" if dist in _TEMPORAL_FRIEND_HOUSES else "enemy"


def panchadha_relation(planet: str, planet_sign: int,
                       dispositor: str, dispositor_sign: int) -> str:
    nat = natural_relation(planet, dispositor)
    temp = temporal_relation(planet_sign, dispositor_sign)
    if nat == "friend":
        return "Great Friend" if temp == "friend" else "Neutral"
    if nat == "enemy":
        return "Neutral" if temp == "friend" else "Great Enemy"
    return "Friend" if temp == "friend" else "Enemy"


def dignity_of(planet: str, lon: float, positions: dict) -> dict:
    """
    Dignity of a planet at sidereal longitude lon.

    positions: {planet: {"lon": ...}} for the whole chart — needed to
    locate the dispositor for the maitri relation. Rahu/Ketu have no
    classical dignity here and return Neutral with a note.
    """
    sign = int(lon % 360.0 // 30)
    deg = lon % 30.0

    if planet in ("Rahu", "Ketu"):
        return {
            "dignity": "Neutral", "score": 50,
            "note": "Nodal dignity conventions vary; treated as neutral pending reference validation.",
        }

    exalt_sign, _deep = EXALTATION[planet]
    if sign == exalt_sign:
        return {"dignity": "Exalted", "score": DIGNITY_SCORES["Exalted"]}
    if sign == (exalt_sign + 6) % 12:
        return {"dignity": "Debilitated", "score": DIGNITY_SCORES["Debilitated"]}

    mt_sign, mt_from, mt_to = MOOLATRIKONA[planet]
    if sign == mt_sign and mt_from <= deg < mt_to:
        return {"dignity": "Moolatrikona", "score": DIGNITY_SCORES["Moolatrikona"]}
    if sign in OWN_SIGNS[planet]:
        return {"dignity": "Own", "score": DIGNITY_SCORES["Own"]}

    dispositor = SIGN_LORDS[sign]
    disp_sign = int(positions[dispositor]["lon"] % 360.0 // 30)
    nat = natural_relation(planet, dispositor)
    temp = temporal_relation(sign, disp_sign)
    relation = panchadha_relation(planet, sign, dispositor, disp_sign)
    return {
        "dignity": relation, "score": DIGNITY_SCORES[relation],
        "dispositor": dispositor,
        # The reasoning chain behind `dignity`, not just its conclusion —
        # added so a domain agent can cite *why* a compound relationship
        # landed where it did (e.g. "natural friend, but temporarily
        # hostile from this house, giving Neutral") instead of only
        # asserting the label. Previously computed internally and
        # discarded; every value here is exact, not derived/approximated.
        "natural_relation": nat,
        "temporal_relation": temp,
    }


def all_dignities(positions: dict) -> dict:
    return {p: dignity_of(p, data["lon"], positions) for p, data in positions.items()}


def _bounded(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 1)


def _angular_distance(a: float, b: float) -> float:
    diff = abs((a - b + 180.0) % 360.0 - 180.0)
    return diff


def _linear_peak(distance: float, max_distance: float = 180.0) -> float:
    return _bounded((1.0 - min(distance, max_distance) / max_distance) * 100.0)


def combustion_status(planet: str, positions: dict) -> dict:
    if planet in {"Sun", "Rahu", "Ketu"}:
        return {
            "active": False,
            "severity": "none",
            "orb": None,
            "threshold": None,
            "modifier": 0.0,
            "status": "not_applicable",
            "rule": "Combustion is measured from the Sun for non-solar grahas.",
        }
    threshold = COMBUSTION_ORBS.get(planet)
    if threshold is None:
        return {
            "active": False,
            "severity": "none",
            "orb": None,
            "threshold": None,
            "modifier": 0.0,
            "status": "not_applicable",
            "rule": "No combustion convention configured.",
        }
    orb = round(_angular_distance(positions[planet]["lon"], positions["Sun"]["lon"]), 2)
    if orb > threshold:
        severity = "none"
        modifier = 0.0
    elif orb <= threshold * 0.25:
        severity = "severe"
        modifier = -20.0
    elif orb <= threshold * 0.55:
        severity = "moderate"
        modifier = -12.0
    else:
        severity = "mild"
        modifier = -6.0
    return {
        "active": severity != "none",
        "severity": severity,
        "orb": orb,
        "threshold": threshold,
        "modifier": modifier,
        "status": "implemented",
        "rule": f"Combust when within {threshold:g}° of the Sun; severity scales by closeness.",
    }


def avastha_of(lon: float) -> dict:
    sign = sign_index(lon)
    deg = degree_in_sign(lon)
    names = ["Bala", "Kumara", "Yuva", "Vriddha", "Mrita"]
    index = min(int(deg // 6.0), 4)
    # Odd signs use direct order; even signs reverse. Sign index is zero-based.
    name = names[index] if sign % 2 == 0 else list(reversed(names))[index]
    return {
        "name": name,
        "degree_in_sign": round(deg, 4),
        "modifier": AVASTHA_MODIFIERS[name],
        "status": "implemented",
        "rule": "Baladi avastha by 6° portions; order reverses in even signs.",
    }


def retrograde_modifier(planet: str, data: dict) -> dict:
    retro = bool(data.get("retrograde"))
    if planet in {"Sun", "Moon", "Rahu", "Ketu"}:
        modifier = 0.0
        status = "not_applicable"
        rule = "Luminaries and nodes are not modified by this retrograde-strength rule."
    elif retro:
        modifier = 8.0
        status = "implemented"
        rule = "Retrograde visible grahas receive extra apparent-strength modifier."
    else:
        modifier = 0.0
        status = "implemented"
        rule = "Direct motion receives no retrograde modifier."
    return {
        "active": retro and modifier != 0.0,
        "modifier": modifier,
        "status": status,
        "rule": rule,
        "speed": round(float(data.get("speed", 0.0)), 6),
    }


def planetary_war(positions: dict) -> dict:
    rows = {
        planet: {
            "active": False,
            "role": "none",
            "opponents": [],
            "modifier": 0.0,
            "status": "implemented",
            "rule": "Planetary war applies among Mars, Mercury, Jupiter, Venus, and Saturn in the same sign within 1° longitude.",
        }
        for planet in PLANETARY_WAR_PLANETS
    }
    planets = sorted(PLANETARY_WAR_PLANETS)
    for i, a in enumerate(planets):
        for b in planets[i + 1:]:
            if sign_index(positions[a]["lon"]) != sign_index(positions[b]["lon"]):
                continue
            orb = _angular_distance(positions[a]["lon"], positions[b]["lon"])
            if orb > 1.0:
                continue
            # Latitude is not currently in positions, so winner uses higher absolute apparent speed as a stable v1 proxy.
            a_speed = abs(float(positions[a].get("speed", 0.0)))
            b_speed = abs(float(positions[b].get("speed", 0.0)))
            winner, loser = (a, b) if a_speed >= b_speed else (b, a)
            rows[winner]["active"] = True
            rows[winner]["role"] = "winner"
            rows[winner]["modifier"] += 4.0
            rows[winner]["opponents"].append({"planet": loser, "orb": round(orb, 3), "result": "won"})
            rows[loser]["active"] = True
            rows[loser]["role"] = "loser"
            rows[loser]["modifier"] -= 12.0
            rows[loser]["opponents"].append({"planet": winner, "orb": round(orb, 3), "result": "lost"})
    return rows


def planetary_conditions(positions: dict) -> dict:
    war = planetary_war(positions)
    rows = {}
    for planet, data in positions.items():
        combust = combustion_status(planet, positions)
        avastha = avastha_of(data["lon"])
        retro = retrograde_modifier(planet, data)
        war_row = war.get(planet, {
            "active": False,
            "role": "not_applicable",
            "opponents": [],
            "modifier": 0.0,
            "status": "not_applicable",
            "rule": "Planetary war applies only to visible tara grahas.",
        })
        modifier = combust["modifier"] + avastha["modifier"] + retro["modifier"] + war_row["modifier"]
        rows[planet] = {
            "combustion": combust,
            "avastha": avastha,
            "retrograde": retro,
            "planetary_war": war_row,
            "net_modifier": round(modifier, 1),
            "provenance": [
                {"condition": "combustion", "status": combust["status"], "note": combust["rule"]},
                {"condition": "avastha", "status": avastha["status"], "note": avastha["rule"]},
                {"condition": "retrograde", "status": retro["status"], "note": retro["rule"]},
                {"condition": "planetary_war", "status": war_row["status"], "note": war_row["rule"]},
            ],
        }
    return {
        "system": "Planetary Conditions v1",
        "rows": rows,
        "notes": [
            "Combustion, Baladi avasthas, and retrograde modifiers are implemented with common software conventions.",
            "Planetary war winner uses apparent-speed proxy until planetary latitude is added to the ephemeris payload.",
        ],
    }


def _sthana_bala(planet: str, lon: float, dignities: dict) -> dict:
    dignity = dignities[planet]
    base = float(dignity["score"])
    if planet in EXALTATION:
        exalt_sign, deep_degree = EXALTATION[planet]
        exalt_lon = exalt_sign * 30.0 + deep_degree
        distance = _angular_distance(lon, exalt_lon)
        uccha = _linear_peak(distance)
        score = (base * 0.65) + (uccha * 0.35)
        note = "Dignity score blended with distance from deep exaltation."
    else:
        score = base
        note = "Dignity score only."
    return {
        "score": _bounded(score),
        "status": "implemented",
        "rule": note,
        "dignity": dignity["dignity"],
    }


def _dig_bala(planet: str, lon: float, lagna_lon: float) -> dict:
    planet_house = house_from_lagna(sign_index(lon), sign_index(lagna_lon))
    strongest = DIG_BALA_HOUSES[planet]
    distance = abs((planet_house - strongest + 6) % 12 - 6)
    score = _bounded((1.0 - distance / 6.0) * 100.0)
    return {
        "score": score,
        "status": "implemented",
        "rule": f"Directional strength peaks in house {strongest}; current house H{planet_house}.",
        "ideal_house": strongest,
        "house": planet_house,
    }


def _kala_bala(planet: str, lon: float, sun_lon: float, moon_lon: float) -> dict:
    elongation = _angular_distance(moon_lon, sun_lon)
    lunar_brightness = _bounded((elongation / 180.0) * 100.0)
    diurnal = 50.0 + 50.0 * cos(radians(_angular_distance(lon, sun_lon)))
    if planet in {"Moon", "Venus", "Saturn"}:
        score = (lunar_brightness * 0.65) + ((100.0 - diurnal) * 0.35)
    elif planet in {"Sun", "Jupiter"}:
        score = ((100.0 - lunar_brightness) * 0.35) + (diurnal * 0.65)
    else:
        score = (lunar_brightness * 0.35) + (diurnal * 0.65)
    return {
        "score": _bounded(score),
        "status": "approximation",
        "rule": "Approximates Kala Bala from lunar phase and solar relation; full hora/ayana/tribhaga calibration pending.",
        "lunar_brightness": lunar_brightness,
    }


def _cheshta_bala(planet: str, data: dict) -> dict:
    if planet in {"Sun", "Moon"}:
        score = 55.0
        rule = "Luminaries do not use retrograde Cheshta in this v1 normalization."
    elif data.get("retrograde"):
        score = 92.0
        rule = "Retrograde grahas receive high Cheshta Bala in classical convention."
    else:
        speed = abs(float(data.get("speed", 0.0)))
        typical = {
            "Mars": 0.55,
            "Mercury": 1.2,
            "Jupiter": 0.08,
            "Venus": 1.0,
            "Saturn": 0.04,
        }.get(planet, 1.0)
        score = 35.0 + min(speed / typical, 1.4) * 35.0
        rule = "Direct-motion score normalized from apparent daily speed; retrograde phase table pending."
    return {
        "score": _bounded(score),
        "status": "approximation",
        "rule": rule,
        "retrograde": bool(data.get("retrograde")),
        "speed": round(float(data.get("speed", 0.0)), 6),
    }


def _naisargika_bala(planet: str) -> dict:
    return {
        "score": _bounded(NAISARGIKA_BALA[planet] / 60.0 * 100.0),
        "status": "implemented",
        "rule": "Traditional natural strength order normalized to Sun = 100.",
    }


def _aspect_influence(source: str, source_sign: int, target_sign: int) -> float:
    house = (target_sign - source_sign) % 12 + 1
    if house in ASPECTS[source]:
        return 1.0
    return 0.0


def _drik_bala(planet: str, positions: dict) -> dict:
    target_sign = sign_index(positions[planet]["lon"])
    benefic_hits = []
    malefic_hits = []
    for source in CLASSICAL_SHADBALA_PLANETS:
        if source == planet:
            continue
        influence = _aspect_influence(source, sign_index(positions[source]["lon"]), target_sign)
        if influence <= 0:
            continue
        if source in NATURAL_BENEFICS:
            benefic_hits.append(source)
        elif source in NATURAL_MALEFICS:
            malefic_hits.append(source)

    score = 50.0 + len(benefic_hits) * 14.0 - len(malefic_hits) * 12.0
    return {
        "score": _bounded(score),
        "status": "approximation",
        "rule": "Whole-sign benefic/malefic aspects; orb and partial-aspect virupas pending.",
        "benefic_aspects": benefic_hits,
        "malefic_aspects": malefic_hits,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Classical Shadbala (BPHS) — all values in virupas; 60 virupas = 1 rupa.
#
# Sources: Brihat Parashara Hora Shastra ch. 27-28 (Shadbala adhyaya) as
# published in the Santhanam translation, cross-checked against the common
# software conventions (JHora/Maitreya family). Items whose published values
# differ across sources are marked "convention_dependent" in the notes.
# ═══════════════════════════════════════════════════════════════════════════

SAPTAVARGA_VARGAS = ["D1", "D2", "D3", "D7", "D9", "D12", "D30"]

SAPTAVARGA_VIRUPAS = {
    "Moolatrikona": 45.0,
    "Own": 30.0,
    "Great Friend": 22.5,
    "Friend": 15.0,
    "Neutral": 7.5,
    "Enemy": 3.75,
    "Great Enemy": 1.875,
}

# Equal-house cusp (house number) where each graha has full directional strength.
DIG_STRONG_CUSP = {
    "Jupiter": 1, "Mercury": 1,   # lagna (east)
    "Sun": 10, "Mars": 10,        # midheaven (south)
    "Saturn": 7,                  # descendant (west)
    "Moon": 4, "Venus": 4,        # IC (north)
}

# Chaldean hora sequence: each successive hora lord, starting from the vara lord.
HORA_SEQUENCE = ["Sun", "Venus", "Mercury", "Moon", "Saturn", "Jupiter", "Mars"]

# Kali epoch: JD 588465.5 (18 Feb 3102 BCE Julian, midnight; a Friday).
KALI_EPOCH_JD = 588465.5

MEAN_OBLIQUITY = 23.4333  # degrees; fixed value used in the Ayana bala normalization

# Mean daily motions (degrees/day) for the cheshta avastha classification.
# Convention: geocentric long-term averages of apparent motion as used by
# common Shadbala software; Mercury and Venus values are the apparent
# (not synodic) means. convention_dependent.
MEAN_DAILY_MOTION = {
    "Mars": 0.524,
    "Mercury": 1.383,
    "Jupiter": 0.083,
    "Venus": 1.2,
    "Saturn": 0.033,
}

# Chesta avastha -> virupas. Published tables disagree on Sama/Chara/Atichara;
# this mapping is convention_dependent (see notes in the payload).
CHESHTA_AVASTHA_VIRUPAS = {
    "Vakra": 60.0,      # retrograde
    "Anuvakra": 30.0,   # slow retrograde (re-approaching direct)
    "Vikala": 15.0,     # stationary (|speed| < 5% of mean)
    "Manda": 30.0,      # slow direct (50-90% of mean)
    "Mandatara": 15.0,  # very slow direct (< 50% of mean)
    "Sama": 7.5,        # near mean (90-110%)
    "Chara": 45.0,      # fast (110-150%)
    "Atichara": 30.0,   # very fast (> 150%)
}

REQUIRED_RUPAS = {
    "Sun": 6.5, "Moon": 6.0, "Mars": 5.0, "Mercury": 7.0,
    "Jupiter": 6.5, "Venus": 5.5, "Saturn": 5.0,
}

_MALE_PLANETS = {"Sun", "Mars", "Jupiter"}
_FEMALE_PLANETS = {"Moon", "Venus"}

_NORTH_STRONG = {"Sun", "Mars", "Jupiter", "Venus"}  # +declination strong
_SOUTH_STRONG = {"Moon", "Saturn"}                   # -declination strong

_DAY_TRIBHAGA_LORDS = ["Mercury", "Sun", "Saturn"]
_NIGHT_TRIBHAGA_LORDS = ["Moon", "Venus", "Mars"]

_NOON_STRONG = {"Sun", "Jupiter", "Venus"}
_MIDNIGHT_STRONG = {"Moon", "Mars", "Saturn"}


def _deep_debilitation_lon(planet: str) -> float:
    exalt_sign, deep_degree = EXALTATION[planet]
    return (exalt_sign * 30.0 + deep_degree + 180.0) % 360.0


def uccha_bala(planet: str, lon: float) -> float:
    """Exaltation strength: distance from deep debilitation / 3 (max 60)."""
    return _angular_distance(lon, _deep_debilitation_lon(planet)) / 3.0


def saptavargaja_bala(planet: str, lon: float, positions: dict) -> dict:
    """Dignity virupas summed over D1, D2, D3, D7, D9, D12, D30.

    Moolatrikona uses the degree range in D1; in the other vargas MT is
    judged by sign index alone (convention_dependent). The panchadha
    relation combines natural friendship with the temporal relation taken
    from the D1 (rashi) chart placements.
    """
    planet_d1_sign = sign_index(lon)
    mt_sign, mt_from, mt_to = MOOLATRIKONA[planet]
    breakdown = {}
    total = 0.0
    for varga in SAPTAVARGA_VARGAS:
        vs = VARGA_FUNCTIONS[varga](lon)
        if varga == "D1" and vs == mt_sign and mt_from <= degree_in_sign(lon) < mt_to:
            dignity = "Moolatrikona"
        elif varga != "D1" and vs == mt_sign:
            dignity = "Moolatrikona"
        elif vs in OWN_SIGNS[planet]:
            dignity = "Own"
        else:
            dispositor = SIGN_LORDS[vs]
            disp_d1_sign = sign_index(positions[dispositor]["lon"])
            dignity = panchadha_relation(planet, planet_d1_sign, dispositor, disp_d1_sign)
        value = SAPTAVARGA_VIRUPAS[dignity]
        breakdown[varga] = {"sign_index": vs, "dignity": dignity, "virupas": value}
        total += value
    return {"virupas": round(total, 3), "vargas": breakdown}


def ojayugma_bala(planet: str, lon: float) -> float:
    """15 virupas each for rashi and navamsha of the preferred parity (max 30)."""
    rashi_even = sign_index(lon) % 2 == 1          # Taurus (idx 1) is the 2nd = even sign
    navamsha_even = VARGA_FUNCTIONS["D9"](lon) % 2 == 1
    prefers_even = planet in {"Moon", "Venus"}
    value = 0.0
    if rashi_even == prefers_even:
        value += 15.0
    if navamsha_even == prefers_even:
        value += 15.0
    return value


def kendradi_bala(lon: float, lagna_lon: float) -> float:
    """Kendra 60 / panaphara 30 / apoklima 15 (whole-sign houses from lagna)."""
    house = house_from_lagna(sign_index(lon), sign_index(lagna_lon))
    if house in (1, 4, 7, 10):
        return 60.0
    if house in (2, 5, 8, 11):
        return 30.0
    return 15.0


def drekkana_bala(planet: str, lon: float) -> float:
    """15 virupas when the planet occupies the drekkana of its gender."""
    part = min(int(degree_in_sign(lon) // 10.0), 2)
    if planet in _MALE_PLANETS:
        return 15.0 if part == 0 else 0.0
    if planet in _FEMALE_PLANETS:
        return 15.0 if part == 1 else 0.0
    return 15.0 if part == 2 else 0.0  # Mercury, Saturn


def dig_bala_virupa(planet: str, lon: float, lagna_lon: float) -> float:
    """Directional strength via equal-house cusps from the lagna degree.

    Strongest point: Jupiter/Mercury 1st cusp, Sun/Mars 10th, Saturn 7th,
    Moon/Venus 4th. Value = angular distance from the weakest point / 3.
    """
    strong_house = DIG_STRONG_CUSP[planet]
    strong_cusp = (lagna_lon + (strong_house - 1) * 30.0) % 360.0
    weakest = (strong_cusp + 180.0) % 360.0
    return _angular_distance(lon, weakest) / 3.0


def sputa_drishti(aspecting: str, separation: float) -> float:
    """BPHS graded aspect (virupas) for forward zodiacal separation s.

    Continuous piecewise curve anchored at the classical fractions:
    0 at 30°, 15 at 60° (quarter), 45 at 90° (three-quarter), 30 at 120°
    (half), 0 at 150°, 60 at 180° (full), decaying to 0 at 300°.
    Mars/Jupiter/Saturn special aspects override to 60 in their bands.
    """
    s = separation % 360.0
    if 30.0 <= s < 60.0:
        base = (s - 30.0) / 2.0
    elif 60.0 <= s < 90.0:
        base = (s - 60.0) + 15.0
    elif 90.0 <= s < 120.0:
        base = 45.0 - (s - 90.0) / 2.0
    elif 120.0 <= s < 150.0:
        base = 150.0 - s
    elif 150.0 <= s < 180.0:
        base = (s - 150.0) * 2.0
    elif 180.0 <= s < 300.0:
        base = (300.0 - s) / 2.0
    else:
        base = 0.0

    if aspecting == "Mars" and (90.0 <= s < 120.0 or 210.0 <= s < 240.0):
        base = max(base, 60.0)   # 4th & 8th full aspects
    elif aspecting == "Jupiter" and (120.0 <= s < 150.0 or 240.0 <= s < 270.0):
        base = max(base, 60.0)   # 5th & 9th full aspects
    elif aspecting == "Saturn" and (60.0 <= s < 90.0 or 270.0 <= s < 300.0):
        base = max(base, 60.0)   # 3rd & 10th full aspects
    return base


def drik_bala_virupa(planet: str, positions: dict) -> dict:
    """(sum of benefic sputa drishti - sum of malefic) / 4; may be negative.

    Benefics: Jupiter, Venus, Mercury (unconditionally, convention), and
    the Moon when bright (elongation from Sun > 90°). Malefics: Sun, Mars,
    Saturn, and the waning/dark Moon.
    """
    elongation = _angular_distance(positions["Moon"]["lon"], positions["Sun"]["lon"])
    moon_benefic = elongation > 90.0
    target_lon = positions[planet]["lon"]
    benefic_sum = 0.0
    malefic_sum = 0.0
    detail = {}
    for source in CLASSICAL_SHADBALA_PLANETS:
        if source == planet:
            continue
        s = (target_lon - positions[source]["lon"]) % 360.0
        value = sputa_drishti(source, s)
        if value <= 0.0:
            continue
        is_benefic = source in {"Jupiter", "Venus", "Mercury"} or (source == "Moon" and moon_benefic)
        if is_benefic:
            benefic_sum += value
        else:
            malefic_sum += value
        detail[source] = {"separation": round(s, 3), "drishti": round(value, 3),
                          "nature": "benefic" if is_benefic else "malefic"}
    virupas = (benefic_sum - malefic_sum) / 4.0
    return {"virupas": round(virupas, 3), "aspects": detail,
            "moon_treated_benefic": moon_benefic}


def cheshta_avastha(planet: str, speed: float) -> dict:
    """Classify the motional avastha of Mars..Saturn from apparent speed."""
    mean = MEAN_DAILY_MOTION[planet]
    ratio = abs(speed) / mean
    if ratio < 0.05:
        name = "Vikala"
    elif speed < 0:
        name = "Anuvakra" if ratio < 0.5 else "Vakra"
    elif ratio < 0.5:
        name = "Mandatara"
    elif ratio < 0.9:
        name = "Manda"
    elif ratio <= 1.1:
        name = "Sama"
    elif ratio <= 1.5:
        name = "Chara"
    else:
        name = "Atichara"
    return {"avastha": name, "virupas": CHESHTA_AVASTHA_VIRUPAS[name],
            "speed": round(speed, 6), "mean_daily_motion": mean,
            "speed_ratio": round(ratio, 4)}


def _declination(tropical_lon: float) -> float:
    """Declination (degrees) from tropical longitude, mean obliquity, zero latitude."""
    return degrees(asin(sin(radians(MEAN_OBLIQUITY)) * sin(radians(tropical_lon))))


def ayana_bala(planet: str, sidereal_lon: float, ayanamsha_val: float) -> float:
    """Ayana bala in virupas; Sun's value is doubled (max 120)."""
    tropical_lon = (sidereal_lon + ayanamsha_val) % 360.0
    decl = _declination(tropical_lon)
    if planet == "Mercury":
        signed = abs(decl)
    elif planet in _SOUTH_STRONG:
        signed = -decl
    else:
        signed = decl
    value = 60.0 * (MEAN_OBLIQUITY + signed) / (2.0 * MEAN_OBLIQUITY)
    value = max(0.0, min(60.0, value))
    if planet == "Sun":
        value *= 2.0
    return value


def _weekday_index_of_jd(jd: float) -> int:
    """Weekday index (0=Sunday..6=Saturday) of a julian day number."""
    return int(jd + 1.5) % 7


def _vedic_day_context(moment) -> dict | None:
    """Sunrise-bounded Vedic day containing the birth instant.

    Returns {rise, set, next_rise (JD UT), is_day, vara_date} or None when
    the Sun is circumpolar.
    """
    date = moment.dt_local.date()
    span = day_span(date.year, date.month, date.day, moment.lat, moment.lng, moment.tz_str)
    if span is None:
        return None
    rise, sets, next_rise = span
    if moment.jd_ut < rise:
        prev = date - timedelta(days=1)
        span = day_span(prev.year, prev.month, prev.day, moment.lat, moment.lng, moment.tz_str)
        if span is None:
            return None
        rise, sets, next_rise = span
        date = prev
    return {
        "rise": rise, "set": sets, "next_rise": next_rise,
        "is_day": rise <= moment.jd_ut < sets,
        "vara_date": date,
    }


def _nathonnata_bala(planet: str, moment) -> float:
    """Natonnata bala from civil hours past local midnight (linear, max 60).

    Method note: uses the civil clock time (dt_local) as a stand-in for
    local apparent solar time; the difference (equation of time + zone
    offset from the meridian) is at most a few virupas.
    """
    if planet == "Mercury":
        return 60.0
    dt = moment.dt_local
    hours = dt.hour + dt.minute / 60.0 + dt.second / 3600.0
    from_midnight = min(hours, 24.0 - hours)        # 0 at midnight .. 12 at noon
    diurnal = from_midnight * 5.0                   # 60 at noon
    return diurnal if planet in _NOON_STRONG else 60.0 - diurnal


def _paksha_bala(planet: str, elongation: float) -> float:
    """Paksha bala; Moon treated as benefic regardless of phase, and doubled."""
    if planet in {"Moon", "Mercury", "Jupiter", "Venus"}:
        value = elongation / 3.0
    else:
        value = 60.0 - elongation / 3.0
    if planet == "Moon":
        value *= 2.0
    return value


def _tribhaga_bala(planet: str, jd_ut: float, day_ctx: dict) -> float:
    """60 virupas to the lord of the day/night third; Jupiter always 60."""
    if planet == "Jupiter":
        return 60.0
    if day_ctx["is_day"]:
        start, end, lords = day_ctx["rise"], day_ctx["set"], _DAY_TRIBHAGA_LORDS
    else:
        start, end, lords = day_ctx["set"], day_ctx["next_rise"], _NIGHT_TRIBHAGA_LORDS
    third = (end - start) / 3.0
    part = min(int((jd_ut - start) / third), 2) if third > 0 else 0
    return 60.0 if lords[part] == planet else 0.0


def _abda_masa_lords(jd_ut: float) -> dict:
    """Year (abda) and month (masa) lords via the Ahargana from the Kali epoch.

    Civil variant: ahargana = floor(JD_UT - 588465.5); the year lord is the
    weekday lord of the day opening the current 360-day year, the month lord
    that of the current 30-day month. convention_dependent — classical texts
    compute the Ahargana from local sunrise at the reference meridian.
    """
    ahargana = int(jd_ut - KALI_EPOCH_JD)
    year_start_jd = KALI_EPOCH_JD + (ahargana - ahargana % 360)
    month_start_jd = KALI_EPOCH_JD + (ahargana - ahargana % 30)
    return {
        "ahargana": ahargana,
        "abda_lord": VARA_LORDS[_weekday_index_of_jd(year_start_jd)],
        "masa_lord": VARA_LORDS[_weekday_index_of_jd(month_start_jd)],
    }


def _vara_hora_lords(jd_ut: float, day_ctx: dict) -> dict:
    """Vara lord of the sunrise-bounded Vedic day and the Chaldean hora lord.

    Horas are equal 1-hour periods counted from sunrise; the first hora lord
    is the vara lord and successive lords follow the Chaldean sequence.
    """
    vara_idx = (day_ctx["vara_date"].weekday() + 1) % 7  # python Mon=0 -> Sunday=0
    vara_lord = VARA_LORDS[vara_idx]
    hora_index = int((jd_ut - day_ctx["rise"]) * 24.0) % 24
    start = HORA_SEQUENCE.index(vara_lord)
    hora_lord = HORA_SEQUENCE[(start + hora_index) % 7]
    return {"vara_lord": vara_lord, "hora_lord": hora_lord, "hora_index": hora_index + 1}


def _classical_kala_bala(planet: str, positions: dict, moment, ayanamsha_val: float,
                         day_ctx: dict | None, calendar_lords: dict, war_rows: dict) -> dict:
    elongation = _angular_distance(positions["Moon"]["lon"], positions["Sun"]["lon"])
    sub = {
        "nathonnata": round(_nathonnata_bala(planet, moment), 3),
        "paksha": round(_paksha_bala(planet, elongation), 3),
        "tribhaga": round(_tribhaga_bala(planet, moment.jd_ut, day_ctx), 3) if day_ctx else 0.0,
        "abda": 15.0 if calendar_lords.get("abda_lord") == planet else 0.0,
        "masa": 30.0 if calendar_lords.get("masa_lord") == planet else 0.0,
        "vara": 45.0 if calendar_lords.get("vara_lord") == planet else 0.0,
        "hora": 60.0 if calendar_lords.get("hora_lord") == planet else 0.0,
        "ayana": round(ayana_bala(planet, positions[planet]["lon"], ayanamsha_val), 3),
    }
    war = war_rows.get(planet, {})
    if war.get("role") == "winner":
        yuddha = 15.0
    elif war.get("role") == "loser":
        yuddha = -15.0
    else:
        yuddha = 0.0
    sub["yuddha"] = yuddha
    return {"virupas": round(sum(sub.values()), 3), "sub": sub}


def _classical_cheshta(planet: str, positions: dict, kala_row: dict) -> dict:
    if planet == "Sun":
        # BPHS: the Sun's Ayana bala serves as its Cheshta bala. The undoubled
        # value (max 60) is used here so cheshta stays on the common scale.
        return {"virupas": round(kala_row["sub"]["ayana"] / 2.0, 3),
                "basis": "ayana_bala (undoubled)"}
    if planet == "Moon":
        # BPHS: the Moon's Paksha bala serves as her Cheshta bala (doubled
        # paksha value reused as computed in Kala bala).
        return {"virupas": round(kala_row["sub"]["paksha"], 3),
                "basis": "paksha_bala"}
    row = cheshta_avastha(planet, float(positions[planet].get("speed", 0.0)))
    return {"virupas": row["virupas"], "basis": "speed_avastha", **row}


def classical_shadbala(positions: dict, lagna_lon: float, moment,
                       ayanamsha_val: float) -> dict:
    """Classical BPHS Shadbala in virupas for the seven grahas."""
    war_rows = planetary_war(positions)
    day_ctx = _vedic_day_context(moment)
    calendar_lords = dict(_abda_masa_lords(moment.jd_ut))
    if day_ctx is not None:
        calendar_lords.update(_vara_hora_lords(moment.jd_ut, day_ctx))

    rows = {}
    for planet in CLASSICAL_SHADBALA_PLANETS:
        lon = positions[planet]["lon"]
        sapta = saptavargaja_bala(planet, lon, positions)
        sthana_sub = {
            "uccha": round(uccha_bala(planet, lon), 3),
            "saptavargaja": sapta["virupas"],
            "ojayugma": ojayugma_bala(planet, lon),
            "kendradi": kendradi_bala(lon, lagna_lon),
            "drekkana": drekkana_bala(planet, lon),
        }
        kala = _classical_kala_bala(planet, positions, moment, ayanamsha_val,
                                    day_ctx, calendar_lords, war_rows)
        cheshta = _classical_cheshta(planet, positions, kala)
        drik = drik_bala_virupa(planet, positions)
        components = {
            "sthana_bala": {"virupas": round(sum(sthana_sub.values()), 3),
                            "sub": sthana_sub, "saptavargaja_detail": sapta["vargas"]},
            "dig_bala": {"virupas": round(dig_bala_virupa(planet, lon, lagna_lon), 3)},
            "kala_bala": kala,
            "cheshta_bala": cheshta,
            "naisargika_bala": {"virupas": NAISARGIKA_BALA[planet]},
            "drik_bala": drik,
        }
        total = sum(c["virupas"] for c in components.values())
        required = REQUIRED_RUPAS[planet]
        ratio = total / (required * 60.0)
        rows[planet] = {
            "components": components,
            "total_virupas": round(total, 3),
            "rupas": round(total / 60.0, 3),
            "required_rupas": required,
            "ratio": round(ratio, 4),
            "sufficient": ratio >= 1.0,
        }

    ranking = sorted(
        [{"planet": p, "ratio": row["ratio"], "rupas": row["rupas"],
          "sufficient": row["sufficient"]} for p, row in rows.items()],
        key=lambda row: row["ratio"], reverse=True,
    )
    return {
        "system": "Shadbala (BPHS virupa)",
        "scale": "virupas (60 virupas = 1 rupa)",
        "available": True,
        "rows": rows,
        "ranking": ranking,
        "required_minima_rupas": dict(REQUIRED_RUPAS),
        "day_context": None if day_ctx is None else {
            "is_day_birth": day_ctx["is_day"],
            "vara_date": day_ctx["vara_date"].isoformat(),
            **{k: v for k, v in calendar_lords.items()},
        },
        "notes": [
            "Sthana, Dig, Naisargika, Ojayugma, Kendradi, Drekkana, Uccha, Paksha, Tribhaga, Vara, Hora, and the sputa-drishti Drik bala follow BPHS formulas directly.",
            "Saptavargaja: Moolatrikona uses the degree range in D1; in other vargas MT is judged by sign index alone (convention_dependent).",
            "Nathonnata uses civil clock time from local midnight as a proxy for local apparent solar time (method approximation, error of a few virupas).",
            "Paksha bala: the Moon is treated as benefic regardless of phase and her value doubled (convention).",
            "Abda/Masa lords use a civil Ahargana from the Kali epoch (JD 588465.5) with 360-day years and 30-day months; source_status: convention_dependent.",
            "Ayana bala uses a fixed mean obliquity of 23.4333 deg and zero planetary latitude; the Sun's value is doubled.",
            "Cheshta bala for Mars..Saturn is classified from apparent speed vs mean daily motion (avastha table convention_dependent); classical mean-longitude cheshta is approximated. Sun uses (undoubled) Ayana bala, Moon uses Paksha bala per BPHS.",
            "Yuddha (planetary war) applies a flat +/-15 virupa adjustment inside Kala bala (approximation; classical uses the disc-diameter difference).",
            "Drik bala: Mercury treated as unconditional benefic; Moon benefic when elongation > 90 deg (conventions). Result may be negative.",
            "Drishti curve is the continuous classical grading (0 at 30, 15 at 60, 45 at 90, 30 at 120, 0 at 150, 60 at 180, fading to 0 at 300), with Mars/Jupiter/Saturn special-aspect overrides to 60.",
        ],
    }


def shadbala(positions: dict, lagna_lon: float, moment=None,
             ayanamsha_val: float = None) -> dict:
    """Return six-source Shadbala for the seven visible grahas.

    The legacy sections keep the normalized 0-100 "v1" component scores for
    backward compatibility. When `moment` (a BirthMoment) and
    `ayanamsha_val` are supplied, a "classical" section computed per BPHS
    in virupas is added, and each row's total_score / rank_band plus the
    ranking are derived from the classical ratio (total virupas over the
    BPHS required minimum) via score = min(100, ratio * 60). Without birth
    data the v1 normalized totals are returned unchanged.
    """
    classical = None
    if moment is not None and ayanamsha_val is not None:
        classical = classical_shadbala(positions, lagna_lon, moment, ayanamsha_val)

    dignities = all_dignities(positions)
    conditions = planetary_conditions(positions)
    sun_lon = positions["Sun"]["lon"]
    moon_lon = positions["Moon"]["lon"]
    rows = {}
    for planet in CLASSICAL_SHADBALA_PLANETS:
        lon = positions[planet]["lon"]
        components = {
            "sthana_bala": _sthana_bala(planet, lon, dignities),
            "dig_bala": _dig_bala(planet, lon, lagna_lon),
            "kala_bala": _kala_bala(planet, lon, sun_lon, moon_lon),
            "cheshta_bala": _cheshta_bala(planet, positions[planet]),
            "naisargika_bala": _naisargika_bala(planet),
            "drik_bala": _drik_bala(planet, positions),
        }
        exact_weight = 0.54
        approx_weight = 0.46
        exact = (
            components["sthana_bala"]["score"] * 0.26 +
            components["dig_bala"]["score"] * 0.16 +
            components["naisargika_bala"]["score"] * 0.12
        ) / exact_weight
        approx = (
            components["kala_bala"]["score"] * 0.14 +
            components["cheshta_bala"]["score"] * 0.16 +
            components["drik_bala"]["score"] * 0.16
        ) / approx_weight
        base_total = (exact * exact_weight) + (approx * approx_weight)
        modifier = conditions["rows"][planet]["net_modifier"]
        if classical is not None:
            ratio = classical["rows"][planet]["ratio"]
            total = _bounded(ratio * 60.0)
            score_note = (
                "Total score and rank band derive from the classical BPHS ratio "
                "(total virupas / required minimum) via min(100, ratio * 60)."
            )
        else:
            total = _bounded(base_total + modifier)
            score_note = "Shadbala v1 is normalized 0-100 for comparison, not classical virupa totals."
        rows[planet] = {
            "base_score": _bounded(base_total),
            "condition_modifier": modifier,
            "total_score": total,
            "rank_band": (
                "strong" if total >= 70 else
                "moderate" if total >= 45 else
                "weak"
            ),
            "components": components,
            "conditions": conditions["rows"][planet],
            "notes": [
                score_note,
                "Component scores remain v1-normalized (0-100); classical virupa values live under the top-level 'classical' key when birth data is available.",
                "Kala, Cheshta, and Drik Bala v1 components are approximation-labelled until golden-chart validation.",
            ],
        }

    ranking = sorted(
        [{"planet": planet, "score": row["total_score"], "band": row["rank_band"]} for planet, row in rows.items()],
        key=lambda row: row["score"],
        reverse=True,
    )
    return {
        "system": "Shadbala v1",
        "classical": classical,
        "scale": "0-100 normalized",
        "planets": CLASSICAL_SHADBALA_PLANETS,
        "excluded": {
            "Rahu": "Classical Shadbala for nodes is convention-dependent; excluded in v1.",
            "Ketu": "Classical Shadbala for nodes is convention-dependent; excluded in v1.",
        },
        "components": [
            "sthana_bala",
            "dig_bala",
            "kala_bala",
            "cheshta_bala",
            "naisargika_bala",
            "drik_bala",
        ],
        "weights": {
            "sthana_bala": 0.26,
            "dig_bala": 0.16,
            "kala_bala": 0.14,
            "cheshta_bala": 0.16,
            "naisargika_bala": 0.12,
            "drik_bala": 0.16,
        },
        "rows": rows,
        "ranking": ranking,
        "conditions": conditions,
        "provenance": [
            {"component": "sthana_bala", "status": "implemented", "note": "Dignity plus distance from deep exaltation."},
            {"component": "dig_bala", "status": "implemented", "note": "Directional house strength."},
            {"component": "naisargika_bala", "status": "implemented", "note": "Traditional natural strength order."},
            {"component": "kala_bala", "status": "approximation", "note": "Phase/solar relation approximation."},
            {"component": "cheshta_bala", "status": "approximation", "note": "Retrograde and apparent-speed approximation."},
            {"component": "drik_bala", "status": "approximation", "note": "Whole-sign aspect approximation."},
            {"component": "condition_modifiers", "status": "implemented", "note": "Combustion, avastha, retrograde, and war modifiers applied to normalized score."},
        ],
    }
