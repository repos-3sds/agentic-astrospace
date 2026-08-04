"""Vedic transit and gochara analysis.

The functions here intentionally calculate signals only. Interpretation can
sit on top, but the app should always be able to show the rule trigger.
"""
from datetime import datetime, timedelta, timezone

import swisseph as swe

from .gocharam import (
    gochara_rules as generated_gochara_rules,
    gocharam_profile as generated_gocharam_profile,
)
from .nakshatra import nakshatra_of
from .positions import (
    degree_in_sign,
    house_from_lagna,
    sidereal_positions,
    sign_index,
    sign_name,
    to_dms,
)

TRANSIT_PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
NATAL_TARGETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]

ASPECTS = [
    {"name": "Conjunction", "angle": 0, "tone": "neutral", "orb": 6.0},
    {"name": "Opposition", "angle": 180, "tone": "hard", "orb": 6.0},
    {"name": "Trine", "angle": 120, "tone": "supportive", "orb": 5.0},
    {"name": "Square", "angle": 90, "tone": "challenging", "orb": 5.0},
]

SLOW_PLANETS = {"Jupiter", "Saturn", "Rahu", "Ketu"}


def _jd_from_dt(dt: datetime) -> float:
    dt_utc = dt.astimezone(timezone.utc)
    hour = dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, hour)


def angle_delta(a: float, b: float) -> float:
    """Smallest absolute separation between two longitudes."""
    return abs((a - b + 180.0) % 360.0 - 180.0)


def _aspect_orb(transit_lon: float, natal_lon: float, aspect_angle: float) -> float:
    separation = angle_delta(transit_lon, natal_lon)
    return min(abs(separation - aspect_angle), abs(separation - (360 - aspect_angle)))


def transit_aspects(natal_positions: dict, transit_positions: dict, limit: int | None = None) -> list[dict]:
    rows = []
    for transit_planet in TRANSIT_PLANETS:
        if transit_planet not in transit_positions:
            continue
        transit_lon = transit_positions[transit_planet]["lon"]
        for natal_planet in NATAL_TARGETS:
            if natal_planet not in natal_positions:
                continue
            natal_lon = natal_positions[natal_planet]["lon"]
            for aspect in ASPECTS:
                orb = _aspect_orb(transit_lon, natal_lon, aspect["angle"])
                if orb <= aspect["orb"]:
                    strength = round((1.0 - orb / aspect["orb"]) * 100)
                    rows.append({
                        "transit_planet": transit_planet,
                        "natal_planet": natal_planet,
                        "aspect": aspect["name"],
                        "exact_angle": aspect["angle"],
                        "orb": round(orb, 2),
                        "strength": max(0, min(100, strength)),
                        "tone": aspect["tone"],
                        "transit_sign": sign_name(sign_index(transit_lon)),
                        "natal_sign": sign_name(sign_index(natal_lon)),
                    })
                    break
    rows.sort(key=lambda row: (-row["strength"], row["orb"], row["transit_planet"], row["natal_planet"]))
    return rows[:limit] if limit else rows


def gochara_rules(transit_positions: dict, natal_positions: dict, natal_lagna_sign: int, natal_moon_sign: int) -> dict:
    """Compatibility entry point backed by the canonical Gocharam engine."""
    return generated_gochara_rules(transit_positions, natal_positions, natal_lagna_sign, natal_moon_sign)


def transit_timeline(
    natal_positions: dict,
    natal_lagna_sign: int,
    natal_moon_sign: int,
    start_dt: datetime,
    ayanamsha: str,
    node_type: str,
    days: int = 30,
) -> dict:
    events: list[dict] = []
    previous_positions = sidereal_positions(_jd_from_dt(start_dt), ayanamsha, node_type)

    for offset in range(1, days + 1):
        day_dt = start_dt + timedelta(days=offset)
        positions = sidereal_positions(_jd_from_dt(day_dt), ayanamsha, node_type)
        day_label = day_dt.date().isoformat()

        for planet in TRANSIT_PLANETS:
            prev_sign = sign_index(previous_positions[planet]["lon"])
            curr_sign = sign_index(positions[planet]["lon"])
            if curr_sign != prev_sign:
                events.append({
                    "date": day_label,
                    "type": "sign_change",
                    "planet": planet,
                    "title": f"{planet} enters {sign_name(curr_sign)}",
                    "detail": f"Transit {planet} moves from {sign_name(prev_sign)} to {sign_name(curr_sign)}.",
                    "tone": "neutral",
                    "strength": 70 if planet in SLOW_PLANETS else 45,
                })

        for aspect in transit_aspects(natal_positions, positions):
            if aspect["strength"] >= 84:
                events.append({
                    "date": day_label,
                    "type": "aspect",
                    "planet": aspect["transit_planet"],
                    "title": (
                        f"{aspect['transit_planet']} {aspect['aspect'].lower()} "
                        f"natal {aspect['natal_planet']}"
                    ),
                    "detail": f"Orb {aspect['orb']} deg in {aspect['transit_sign']}.",
                    "tone": aspect["tone"],
                    "strength": aspect["strength"],
                    "aspect": aspect,
                })

        gochara = generated_gochara_rules(positions, natal_positions, natal_lagna_sign, natal_moon_sign)
        for rule in gochara["active_rules"]:
            if rule["planet"] in SLOW_PLANETS and offset in {1, 7, 15, 30}:
                events.append({
                    "date": day_label,
                    "type": "gochara_rule",
                    "planet": rule["planet"],
                    "title": rule["name"],
                    "detail": rule["trigger"],
                    "tone": "supportive" if rule["severity"] == "supportive" else "challenging",
                    "strength": 75,
                })

        previous_positions = positions

    events.sort(key=lambda event: (event["date"], -event["strength"], event["title"]))
    return {
        "next_7_days": [event for event in events if event["date"] <= (start_dt + timedelta(days=7)).date().isoformat()][:18],
        "next_30_days": events[:60],
    }


def transit_analysis(
    natal_positions: dict,
    natal_lagna_lon: float,
    as_of: datetime,
    ayanamsha: str = "lahiri",
    node_type: str = "mean",
    dasha_context: dict | None = None,
) -> dict:
    natal_lagna_sign = sign_index(natal_lagna_lon)
    natal_moon_sign = sign_index(natal_positions["Moon"]["lon"])
    transit_positions = sidereal_positions(_jd_from_dt(as_of), ayanamsha, node_type)
    gocharam = generated_gocharam_profile(
        natal_positions,
        natal_lagna_lon,
        as_of,
        ayanamsha,
        node_type,
        dasha_context=dasha_context,
    )
    gochara = gocharam["gochara"]

    # Ashtakavarga transit support (BAV/SAV/kakshya, per-rule av_context and
    # effective_severity) is already computed exactly once inside
    # generated_gocharam_profile and applied to gochara["rules"] there —
    # reuse it rather than recomputing a second, drift-prone copy here. This
    # is also what keeps /gocharam and /transits reporting identical
    # av_context (including kakshya) for the same rule.
    ashtakavarga_transit = gocharam["ashtakavarga_transit"]

    aspects = transit_aspects(natal_positions, transit_positions, limit=36)
    active_aspects = [row for row in aspects if row["strength"] >= 45]
    timeline = transit_timeline(
        natal_positions,
        natal_lagna_sign,
        natal_moon_sign,
        as_of,
        ayanamsha,
        node_type,
    )

    return {
        "system": "Vedic Gochara / Sidereal Transits",
        "as_of": as_of.isoformat(),
        "ayanamsha": ayanamsha,
        "node_type": node_type,
        "natal": {
            "lagna_sign": sign_name(natal_lagna_sign),
            "moon_sign": sign_name(natal_moon_sign),
        },
        "gochara": gochara,
        "gocharam_periods": gocharam["periods"],
        "gocharam_coverage": gocharam["coverage"],
        "ashtakavarga_transit": ashtakavarga_transit,
        "aspects": aspects,
        "active_aspects": active_aspects,
        "strongest_aspect": active_aspects[0] if active_aspects else None,
        "timeline": timeline,
        "notes": [
            "Transit aspects use sidereal longitudes and orb strength.",
            "Gochara rules are deterministic triggers; interpretation should explain them, not recalculate them.",
        ],
    }
