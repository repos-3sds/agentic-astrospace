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
from math import cos, radians

from .constants import (
    EXALTATION, MOOLATRIKONA, OWN_SIGNS, NATURAL_RELATIONS, SIGN_LORDS,
)
from .positions import degree_in_sign, house_from_lagna, sign_index

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
    relation = panchadha_relation(planet, sign, dispositor, disp_sign)
    return {"dignity": relation, "score": DIGNITY_SCORES[relation],
            "dispositor": dispositor}


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


def shadbala(positions: dict, lagna_lon: float) -> dict:
    """Return six-source Shadbala v1 for the seven visible grahas.

    Scores are normalized to 0-100. The payload is intentionally explicit
    about implementation status so the UI can distinguish audited formulas
    from convention-dependent approximations.
    """
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
        total = _bounded(base_total + modifier)
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
                "Shadbala v1 is normalized 0-100 for comparison, not classical virupa totals.",
                "Kala, Cheshta, and Drik Bala are approximation-labelled until golden-chart validation.",
                "Total score includes condition modifiers for combustion, avastha, retrograde strength, and planetary war.",
            ],
        }

    ranking = sorted(
        [{"planet": planet, "score": row["total_score"], "band": row["rank_band"]} for planet, row in rows.items()],
        key=lambda row: row["score"],
        reverse=True,
    )
    return {
        "system": "Shadbala v1",
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
