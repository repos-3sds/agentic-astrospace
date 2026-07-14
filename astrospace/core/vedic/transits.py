"""Vedic transit and gochara analysis.

The functions here intentionally calculate signals only. Interpretation can
sit on top, but the app should always be able to show the rule trigger.
"""
from datetime import datetime, timedelta, timezone

import swisseph as swe

from .ashtakavarga import AV_PLANETS, ashtakavarga
from .gocharam import (
    classical_gochara_status,
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
GOCHARA_TIMELINE_RULE_DAYS = 365
GOCHARA_ACTIVE_WINDOW_DAYS = 3650

# Kakshya (Ashtakavarga micro-division): each sign splits into 8 segments of
# 3 deg 45 min, lorded in this fixed order.
KAKSHYA_LORDS = ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon", "Lagna"]
KAKSHYA_SPAN_DEG = 3.75


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


def _planet_snapshot(positions: dict, planet: str, natal_lagna_sign: int, natal_moon_sign: int) -> dict:
    data = positions[planet]
    lon = data["lon"]
    s = sign_index(lon)
    nak = nakshatra_of(lon)
    return {
        "planet": planet,
        "longitude": round(lon, 4),
        "sign": sign_name(s),
        "sign_index": s,
        "degree_in_sign": round(degree_in_sign(lon), 4),
        "dms": to_dms(degree_in_sign(lon)),
        "nakshatra": nak["name"],
        "nakshatra_pada": nak["pada"],
        "house_from_lagna": house_from_lagna(s, natal_lagna_sign),
        "house_from_moon": house_from_lagna(s, natal_moon_sign),
        "retrograde": data.get("retrograde", False),
        "speed": round(data.get("speed", 0.0), 6),
    }


def _rule_explanation(name: str, active: bool, trigger: str, house: int, anchor: str) -> str:
    active_text = "active" if active else "not active"
    if name == "Sade Sati":
        phase = {12: "opening", 1: "central", 2: "closing"}.get(house, "inactive")
        return (
            f"{trigger}, so the Sade Sati rule is {active_text} for this profile. "
            "This rule is judged from natal Moon because Gocharam treats the Moon as the lived emotional and mental anchor. "
            f"When active, this is the {phase} Saturn pressure zone and it usually asks for patience, duty, maturity, and slower decision-making. "
            "This is a deterministic transit flag only; the final weight should be read together with dasha, Saturn strength, Ashtakavarga support, and the houses Saturn owns in the natal chart."
        )
    if name == "Dhaiya / Kantaka Shani":
        return (
            f"{trigger}, so the Dhaiya or Kantaka Shani caution is {active_text}. "
            "This is a Moon-based Saturn transit check used to identify periods where domestic, emotional, health, or workload pressure may feel heavier than usual. "
            "If active, the app should treat Saturn as a slow background influence rather than a sudden event trigger. "
            "The result becomes more serious when the active dasha also involves Saturn, the Moon, the affected house lord, or weak natal support."
        )
    if name == "Jupiter support from Moon":
        return (
            f"{trigger}, so Jupiter's Moon-based support rule is {active_text}. "
            "Jupiter is read from the natal Moon to understand morale, protection, counsel, learning, family growth, and the user's subjective sense of opportunity. "
            "When this rule is active, it can soften pressure from other transits and make guidance, education, planning, and recovery easier to access. "
            "It should still be balanced against Jupiter's dignity, dasha relevance, Ashtakavarga bindus in the transit sign, and any hard transit aspects active at the same time."
        )
    if name == "Jupiter support from Lagna":
        return (
            f"{trigger}, so Jupiter's Lagna-based support rule is {active_text}. "
            "The Lagna view shows how the transit interacts with concrete life areas such as body, work, money, relationships, and visible outcomes. "
            "When active, it gives a practical support signal and can point to better timing for growth, advice, study, agreements, or recovery. "
            "This should be used as a cross-check with the Moon-based reading because a transit may feel supportive internally while producing mixed external results, or the reverse."
        )
    if name == "Rahu caution from Moon":
        return (
            f"{trigger}, so the Rahu Moon-based caution is {active_text}. "
            "Rahu transits are used as volatility markers because they can amplify desire, urgency, foreignness, experimentation, obsession, or sudden changes in perception. "
            "When active from sensitive Moon houses, the app should flag decisions that are emotionally charged, rushed, or driven by unclear information. "
            "The signal becomes stronger if Rahu connects to the active dasha lord, natal Moon, Lagna, or key career and relationship houses."
        )
    if name == "Ketu caution from Moon":
        return (
            f"{trigger}, so the Ketu Moon-based caution is {active_text}. "
            "Ketu transits often behave as separation, detachment, review, simplification, or dissatisfaction with ordinary outcomes. "
            "When active from sensitive Moon houses, the app should watch for withdrawal, uncertainty, spiritual focus, or loss of interest in matters represented by the affected house. "
            "This is not automatically negative; it becomes more challenging when the dasha and natal condition show weak support for the same themes."
        )
    return (
        f"{trigger}, so this Gocharam rule is {active_text}. "
        f"The rule is judged from {anchor} and is calculated directly from the transit rashi position. "
        "It is a deterministic signal, not an AI interpretation. "
        "Use it with dasha, chart strength, and other active transits before making a final judgement."
    )


def _window_text(active_windows: list[dict] | None) -> str:
    if not active_windows:
        return "No major Gocharam rule window is active today."
    parts = []
    for window in active_windows[:3]:
        start = window.get("start_date") or "before the scan window"
        end = window.get("end_date") or "beyond the scan window"
        parts.append(f"{window['rule']} runs from {start} to {end}")
    return "; ".join(parts) + "."


def _core_reading(
    rules: list[dict],
    saturn_from_moon: int,
    natal_moon_sign: int,
    natal_lagna_sign: int,
    active_windows: list[dict] | None = None,
) -> dict:
    active_rules = [rule for rule in rules if rule["active"]]
    challenging = [rule for rule in active_rules if rule["severity"] in {"high", "medium"}]
    supportive = [rule for rule in active_rules if rule["severity"] == "supportive"]
    if challenging and supportive:
        tone = "mixed"
        title = "Mixed Gocharam: pressure and protection are both active"
    elif challenging:
        tone = "challenging"
        title = "Caution Gocharam: slow-moving pressure is active"
    elif supportive:
        tone = "supportive"
        title = "Supportive Gocharam: growth signals are active"
    else:
        tone = "neutral"
        title = "Neutral Gocharam: no major classical trigger is active"

    active_names = ", ".join(rule["name"] for rule in active_rules[:3]) or "no major rule trigger"
    timing = _window_text(active_windows)
    rationale = (
        f"The current Gocharam is judged from natal Moon sign {sign_name(natal_moon_sign)} and natal Lagna sign "
        f"{sign_name(natal_lagna_sign)}. The rule engine found {active_names}, with Saturn currently "
        f"{saturn_from_moon} from the Moon. {timing} This is calculated from sidereal transit signs and rule "
        "windows, not from AI generation."
    )
    if challenging and supportive:
        reading = (
            "This is a mixed period: one part of life may feel slow, heavy, or demanding, while another part still has "
            "support for learning, planning, recovery, or guidance. Do not read this as simply good or bad. Move with "
            "patience where pressure is visible, but still use the supportive openings for practical progress."
        )
    elif challenging:
        reading = (
            "This period asks you to slow down, stay steady, and avoid rushed decisions. There may be more pressure, "
            "delay, responsibility, or emotional heaviness than usual, so simple routines and careful commitments matter. "
            "Use the end date as a timing marker: the tone can ease when this Gocharam window closes."
        )
    elif supportive:
        reading = (
            "This is a helpful Gocharam window for making plans, seeking guidance, learning, repairing things, and taking "
            "sensible next steps. It does not promise instant results, but it gives a better background climate for growth. "
            "Use this period while it is active rather than waiting for perfect conditions."
        )
    else:
        reading = (
            "There is no major classical Gocharam pressure or support trigger active right now. Treat this as a normal "
            "working period where daily choices, dasha, and shorter Moon movements may matter more than big transit rules. "
            "Check the upcoming timeline to see when the next stronger Gocharam window begins."
        )
    sentences = [
        (
            f"The current Gocharam is being judged from natal Moon sign {sign_name(natal_moon_sign)} "
            f"and natal Lagna sign {sign_name(natal_lagna_sign)}, with Saturn currently {saturn_from_moon} from the Moon."
        ),
        (
            f"The core rule engine found {active_names}; this is calculated from transit sign positions, not from AI text generation."
        ),
        (
            "Moon-based rules describe the user's felt experience, mental load, confidence, and timing pressure, while Lagna-based rules describe more visible life areas and practical outcomes."
        ),
        (
            "Use this as the first layer of judgement, then refine it with dasha, transit aspects, Ashtakavarga bindus, planetary dignity, and the profile's natal promise."
        ),
    ]
    return {
        "title": title,
        "tone": tone,
        "rationale": rationale,
        "reading": reading,
        "timing_summary": timing,
        "sentences": sentences,
        "active_rule_count": len(active_rules),
        "supportive_rule_count": len(supportive),
        "challenging_rule_count": len(challenging),
    }


def _timeline_core_reading(events: list[dict], mode: str, scan_days: int) -> dict:
    if mode == "next":
        if not events:
            return {
                "title": "No major Gocharam rule change is coming soon",
                "tone": "neutral",
                "rationale": (
                    f"The next-reading scan checked sign-based Gocharam rule transitions for the next {scan_days} days. "
                    "No Sade Sati, Dhaiya, Jupiter support, Rahu caution, or Ketu caution start/end transition was found in that window. "
                    "This means the large rule background is relatively stable, though shorter Moon movement and transit aspects can still change daily."
                ),
                "reading": (
                    "For now, do not expect a big Gocharam phase shift. Work with the current pattern instead of waiting for the sky to suddenly change. "
                    "Use the normal transit timeline for smaller daily or monthly movement, especially Moon, Sun, Mars, and exact aspects."
                ),
                "timing_summary": "No major rule transition in the scan window.",
            }
        first = events[0]
        names = ", ".join(f"{event['title']} on {event['date']}" for event in events[:3])
        return {
            "title": f"What next: {first['title']}",
            "tone": first["tone"],
            "rationale": (
                f"The next Gocharam reading is based on upcoming rule transitions over the next {scan_days} days. "
                f"The first detected change is {first['title']} on {first['date']}, and the nearest changes are {names}. "
                "These dates are calculated by scanning daily sidereal transit positions and checking when each classical rule changes active state."
            ),
            "reading": (
                f"The next important shift is around {first['date']}. Around that date, the background mood of the period can start changing, "
                "so it is a good marker for planning, reviewing pressure, or using a supportive opening. Do not treat the date as a single-day event only; "
                "slow-planet Gocharam changes usually describe a phase that builds before and settles after the transition."
            ),
            "timing_summary": f"Next change: {first['title']} on {first['date']}.",
        }

    if not events:
        return {
            "title": "No major Gocharam rule change was found recently",
            "tone": "neutral",
            "rationale": (
                f"The past-reading scan checked sign-based Gocharam rule transitions for the previous {scan_days} days. "
                "No major rule start/end transition was found among the current supported Gocharam rules. "
                "This suggests the present background has been stable, though smaller transits may still explain short-term experiences."
            ),
            "reading": (
                "There may not be a single big Gocharam turning point to validate in the recent past. Look instead at daily Moon movement, exact aspects, "
                "dashas, or personal events recorded in the calendar. The current Gocharam may be more of a steady background than a sudden before-after shift."
            ),
            "timing_summary": "No recent major rule transition in the scan window.",
        }
    first = events[0]
    names = ", ".join(f"{event['title']} on {event['date']}" for event in events[:3])
    return {
        "title": f"What happened before: {first['title']}",
        "tone": first["tone"],
        "rationale": (
            f"The past Gocharam reading is based on rule transitions detected over the previous {scan_days} days. "
            f"The most recent change was {first['title']} on {first['date']}, and the nearest prior changes are {names}. "
            "These are deterministic checkpoints where the transit sign position changed the active/inactive state of a supported Gocharam rule."
        ),
        "reading": (
            f"Look back around {first['date']} and see whether the mood, pressure, support, or decision pattern changed around that time. "
            "This is useful for validation: if the life pattern shifted near that date, the Gocharam rule is behaving visibly for this profile. "
            "If nothing meaningful changed, the rule may be weaker here and should be judged with dasha, Ashtakavarga, and natal strength."
        ),
        "timing_summary": f"Latest past change: {first['title']} on {first['date']}.",
    }


def transit_planet_details(transit_positions: dict, natal_lagna_sign: int, natal_moon_sign: int) -> dict:
    return {
        planet: _planet_snapshot(transit_positions, planet, natal_lagna_sign, natal_moon_sign)
        for planet in TRANSIT_PLANETS
        if planet in transit_positions
    }


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


def classical_gochara(transit_positions: dict, natal_moon_sign: int) -> dict:
    """Classical Moon-sign gochara with Vedha for every transit planet.

    Uses the standard favourable-house / vedha-sthana table (Phaladeepika
    convention). A planet transiting a favourable house from natal Moon is
    obstructed when a DIFFERENT planet simultaneously transits the paired
    vedha house, except for the classical Sun-Saturn and Moon-Mercury
    exemptions. Rahu/Ketu follow Saturn's convention and are flagged
    ``source_status: "convention_dependent"``.
    """
    houses_from_moon = {
        planet: house_from_lagna(sign_index(transit_positions[planet]["lon"]), natal_moon_sign)
        for planet in TRANSIT_PLANETS
        if planet in transit_positions
    }
    return classical_gochara_status(houses_from_moon)


def _bav_support(bindus: int) -> str:
    if bindus >= 5:
        return "strong"
    if bindus == 4:
        return "average"
    return "weak"


def _sav_support(sav: int) -> str:
    if sav >= 30:
        return "strong"
    if sav >= 25:
        return "average"
    return "weak"


def _kakshya_of(lon: float) -> tuple[int, str]:
    """Return (kakshya_index 1-8, kakshya_lord) for a longitude."""
    idx = min(int(degree_in_sign(lon) // KAKSHYA_SPAN_DEG), 7)
    return idx + 1, KAKSHYA_LORDS[idx]


def _effective_severity(severity: str, active: bool, bav_support: str | None) -> str:
    """Ashtakavarga-adjusted severity; never mutates the base severity.

    A challenging rule (high/medium) whose planet has strong natal BAV
    support in its transit sign is stepped down one level; a supportive rule
    with weak support is marked diluted.
    """
    if not active or bav_support is None:
        return severity
    if severity in {"high", "medium"} and bav_support == "strong":
        return {"high": "medium", "medium": "low"}[severity]
    if severity == "supportive" and bav_support == "weak":
        return "diluted"
    return severity


def ashtakavarga_transit_support(natal_av: dict, transit_positions: dict) -> dict:
    """Per-planet natal-Ashtakavarga weighting of the current transit.

    ``natal_av`` is the output of :func:`ashtakavarga` for the NATAL chart;
    it must be computed once by the caller, not per planet or per day.
    """
    rows: dict[str, dict] = {}
    for planet in AV_PLANETS:
        if planet not in transit_positions:
            continue
        lon = transit_positions[planet]["lon"]
        transit_sign = sign_index(lon)
        bindus = natal_av["bav"][planet][transit_sign]
        sav = natal_av["sav"][transit_sign]
        kakshya_index, kakshya_lord = _kakshya_of(lon)
        bindu_given = natal_av["source_breakdown"][planet][kakshya_lord][transit_sign] == 1
        rows[planet] = {
            "planet": planet,
            "transit_sign": sign_name(transit_sign),
            "transit_sign_index": transit_sign,
            "bindus": bindus,
            "bav_support": _bav_support(bindus),
            "sav": sav,
            "sav_support": _sav_support(sav),
            "kakshya": {
                "kakshya_index": kakshya_index,
                "kakshya_lord": kakshya_lord,
                "bindu_given": bindu_given,
            },
        }
    return {
        "planets": rows,
        "note": (
            "A transit gives better results when the planet's natal BAV bindus in the transited sign "
            "are 5 or more (weak at 3 or fewer) and when that sign's natal SAV is 30+ (weak below 25); "
            "the kakshya row shows the 3 deg 45 min segment the planet occupies and whether its lord "
            "contributed a bindu to that planet's BAV in this sign."
        ),
    }


def gochara_rules(transit_positions: dict, natal_lagna_sign: int, natal_moon_sign: int) -> dict:
    details = transit_planet_details(transit_positions, natal_lagna_sign, natal_moon_sign)
    saturn_from_moon = details["Saturn"]["house_from_moon"]
    jupiter_from_moon = details["Jupiter"]["house_from_moon"]
    jupiter_from_lagna = details["Jupiter"]["house_from_lagna"]
    rahu_caution = details["Rahu"]["house_from_moon"] in {1, 5, 7, 8, 9, 12}
    ketu_caution = details["Ketu"]["house_from_moon"] in {1, 5, 7, 8, 9, 12}

    rules = [
        {
            "name": "Sade Sati",
            "planet": "Saturn",
            "active": saturn_from_moon in {12, 1, 2},
            "severity": "high" if saturn_from_moon in {12, 1, 2} else "none",
            "trigger": f"Saturn is {saturn_from_moon} from natal Moon",
            "note": "Active when Saturn transits 12th, 1st, or 2nd from natal Moon.",
            "verified": True,
        },
        {
            "name": "Dhaiya / Kantaka Shani",
            "planet": "Saturn",
            "active": saturn_from_moon in {4, 8},
            "severity": "medium" if saturn_from_moon in {4, 8} else "none",
            "trigger": f"Saturn is {saturn_from_moon} from natal Moon",
            "note": "Common gochara caution when Saturn is 4th or 8th from Moon.",
            "verified": True,
        },
        {
            "name": "Jupiter support from Moon",
            "planet": "Jupiter",
            "active": jupiter_from_moon in {2, 5, 7, 9, 11},
            "severity": "supportive" if jupiter_from_moon in {2, 5, 7, 9, 11} else "neutral",
            "trigger": f"Jupiter is {jupiter_from_moon} from natal Moon",
            "note": "Jupiter is generally supportive in 2, 5, 7, 9, and 11 from Moon.",
            "verified": True,
        },
        {
            "name": "Jupiter support from Lagna",
            "planet": "Jupiter",
            "active": jupiter_from_lagna in {2, 5, 7, 9, 11},
            "severity": "supportive" if jupiter_from_lagna in {2, 5, 7, 9, 11} else "neutral",
            "trigger": f"Jupiter is {jupiter_from_lagna} from natal Lagna",
            "note": "A lagna-based cross-check for benefic transit support.",
            "verified": True,
        },
        {
            "name": "Rahu caution from Moon",
            "planet": "Rahu",
            "active": rahu_caution,
            "severity": "medium" if rahu_caution else "none",
            "trigger": f"Rahu is {details['Rahu']['house_from_moon']} from natal Moon",
            "note": "Nodes in sensitive Moon houses can increase volatility.",
            "verified": True,
        },
        {
            "name": "Ketu caution from Moon",
            "planet": "Ketu",
            "active": ketu_caution,
            "severity": "medium" if ketu_caution else "none",
            "trigger": f"Ketu is {details['Ketu']['house_from_moon']} from natal Moon",
            "note": "Nodes in sensitive Moon houses can increase detachment or uncertainty.",
            "verified": True,
        },
    ]
    for rule in rules:
        anchor = "natal Lagna" if "Lagna" in rule["name"] else "natal Moon"
        house = details[rule["planet"]]["house_from_lagna" if anchor == "natal Lagna" else "house_from_moon"]
        rule["explanation"] = _rule_explanation(
            rule["name"],
            rule["active"],
            rule["trigger"],
            house,
            anchor,
        )

    return {
        "planets": details,
        "rules": rules,
        "active_rules": [rule for rule in rules if rule["active"]],
        "classical_gochara": classical_gochara(transit_positions, natal_moon_sign),
        "core_reading": _core_reading(rules, saturn_from_moon, natal_moon_sign, natal_lagna_sign),
        "sade_sati": {
            "active": saturn_from_moon in {12, 1, 2},
            "phase": {12: "first", 1: "second", 2: "third"}.get(saturn_from_moon),
            "saturn_house_from_moon": saturn_from_moon,
        },
    }


def _gochara_rule_state(
    dt: datetime,
    natal_lagna_sign: int,
    natal_moon_sign: int,
    ayanamsha: str,
    node_type: str,
) -> dict[str, dict]:
    positions = sidereal_positions(_jd_from_dt(dt), ayanamsha, node_type)
    return {rule["name"]: rule for rule in gochara_rules(positions, natal_lagna_sign, natal_moon_sign)["rules"]}


def _is_rule_active(
    dt: datetime,
    rule_name: str,
    natal_lagna_sign: int,
    natal_moon_sign: int,
    ayanamsha: str,
    node_type: str,
) -> bool:
    return _gochara_rule_state(dt, natal_lagna_sign, natal_moon_sign, ayanamsha, node_type)[rule_name]["active"]


def _active_rule_start(
    as_of: datetime,
    rule_name: str,
    natal_lagna_sign: int,
    natal_moon_sign: int,
    ayanamsha: str,
    node_type: str,
) -> str | None:
    active_dt = as_of
    inactive_dt = None
    for days in range(7, GOCHARA_ACTIVE_WINDOW_DAYS + 1, 7):
        candidate = as_of - timedelta(days=days)
        if not _is_rule_active(candidate, rule_name, natal_lagna_sign, natal_moon_sign, ayanamsha, node_type):
            inactive_dt = candidate
            break
        active_dt = candidate
    if inactive_dt is None:
        return None
    cursor = inactive_dt + timedelta(days=1)
    while cursor <= active_dt + timedelta(days=7):
        if _is_rule_active(cursor, rule_name, natal_lagna_sign, natal_moon_sign, ayanamsha, node_type):
            return cursor.date().isoformat()
        cursor += timedelta(days=1)
    return active_dt.date().isoformat()


def _active_rule_end(
    as_of: datetime,
    rule_name: str,
    natal_lagna_sign: int,
    natal_moon_sign: int,
    ayanamsha: str,
    node_type: str,
) -> str | None:
    active_dt = as_of
    inactive_dt = None
    for days in range(7, GOCHARA_ACTIVE_WINDOW_DAYS + 1, 7):
        candidate = as_of + timedelta(days=days)
        if not _is_rule_active(candidate, rule_name, natal_lagna_sign, natal_moon_sign, ayanamsha, node_type):
            inactive_dt = candidate
            break
        active_dt = candidate
    if inactive_dt is None:
        return None
    cursor = active_dt
    last_active = active_dt
    while cursor <= inactive_dt:
        if _is_rule_active(cursor, rule_name, natal_lagna_sign, natal_moon_sign, ayanamsha, node_type):
            last_active = cursor
        else:
            break
        cursor += timedelta(days=1)
    return last_active.date().isoformat()


def _rule_tone(rule: dict, active: bool = True) -> str:
    if not active:
        return "neutral"
    return "supportive" if rule["severity"] == "supportive" else "challenging"


def gochara_rule_timeline(
    as_of: datetime,
    natal_lagna_sign: int,
    natal_moon_sign: int,
    ayanamsha: str,
    node_type: str,
    current_gochara: dict,
) -> dict:
    active_windows = []
    for rule in current_gochara["active_rules"]:
        start = _active_rule_start(as_of, rule["name"], natal_lagna_sign, natal_moon_sign, ayanamsha, node_type)
        end = _active_rule_end(as_of, rule["name"], natal_lagna_sign, natal_moon_sign, ayanamsha, node_type)
        active_windows.append({
            "rule": rule["name"],
            "planet": rule["planet"],
            "start_date": start,
            "end_date": end,
            "tone": _rule_tone(rule),
            "trigger": rule["trigger"],
            "summary": (
                f"{rule['name']} is active now. "
                f"It began {start or 'before the scan window'} and is estimated to remain active until {end or 'beyond the scan window'}."
            ),
        })

    previous_events = []
    next_events = []
    today_state = _gochara_rule_state(as_of, natal_lagna_sign, natal_moon_sign, ayanamsha, node_type)
    previous_state = today_state
    for offset in range(1, GOCHARA_TIMELINE_RULE_DAYS + 1):
        day = as_of - timedelta(days=offset)
        state = _gochara_rule_state(day, natal_lagna_sign, natal_moon_sign, ayanamsha, node_type)
        for name, rule in state.items():
            was_active = rule["active"]
            later_active = previous_state[name]["active"]
            if was_active != later_active:
                transition = "ended" if was_active and not later_active else "started"
                event_rule = rule if was_active else previous_state[name]
                previous_events.append({
                    "date": (day + timedelta(days=1)).date().isoformat(),
                    "type": "gochara_rule",
                    "planet": event_rule["planet"],
                    "title": f"{event_rule['name']} {transition}",
                    "detail": event_rule["trigger"],
                    "tone": _rule_tone(event_rule, True),
                    "strength": 78 if event_rule["severity"] == "high" else 70,
                    "rule": event_rule["name"],
                    "transition": transition,
                })
        previous_state = state

    previous_events.sort(key=lambda event: (event["date"], event["title"]), reverse=True)

    previous_state = today_state
    for offset in range(1, GOCHARA_TIMELINE_RULE_DAYS + 1):
        day = as_of + timedelta(days=offset)
        state = _gochara_rule_state(day, natal_lagna_sign, natal_moon_sign, ayanamsha, node_type)
        for name, rule in state.items():
            was_active = previous_state[name]["active"]
            is_active = rule["active"]
            if was_active != is_active:
                transition = "starts" if is_active else "ends"
                event_rule = rule if is_active else previous_state[name]
                next_events.append({
                    "date": day.date().isoformat(),
                    "type": "gochara_rule",
                    "planet": event_rule["planet"],
                    "title": f"{event_rule['name']} {transition}",
                    "detail": event_rule["trigger"],
                    "tone": _rule_tone(event_rule, True),
                    "strength": 78 if event_rule["severity"] == "high" else 70,
                    "rule": event_rule["name"],
                    "transition": transition,
                })
        previous_state = state

    next_events.sort(key=lambda event: (event["date"], -event["strength"], event["title"]))
    return {
        "active_windows": active_windows,
        "previous_365_days": previous_events[:24],
        "next_365_days": next_events[:36],
        "scan_days": GOCHARA_TIMELINE_RULE_DAYS,
    }


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

        gochara = generated_gochara_rules(positions, natal_lagna_sign, natal_moon_sign)
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
    )
    gochara = gocharam["gochara"]

    # Natal Ashtakavarga is computed exactly ONCE per transit_analysis call;
    # calendar code calls this in loops, so keep it out of per-planet work.
    natal_av = ashtakavarga(natal_positions, natal_lagna_lon)
    ashtakavarga_transit = ashtakavarga_transit_support(natal_av, transit_positions)
    av_rows = ashtakavarga_transit["planets"]
    for rule in gochara["rules"]:
        row = av_rows.get(rule["planet"])
        rule["av_context"] = (
            {
                "bindus": row["bindus"],
                "bav_support": row["bav_support"],
                "sav": row["sav"],
                "sav_support": row["sav_support"],
            }
            if row
            else None
        )
        effective = _effective_severity(
            rule["severity"], rule["active"], row["bav_support"] if row else None
        )
        rule["effective_severity"] = effective
        if effective != rule["severity"]:
            if effective == "diluted":
                rule["note"] += (
                    f" Ashtakavarga check: {rule['planet']} has only {row['bindus']} natal bindus "
                    "in its transit sign, so this supportive signal is diluted."
                )
            else:
                rule["note"] += (
                    f" Ashtakavarga check: {rule['planet']} carries {row['bindus']} natal bindus "
                    "in its transit sign, so this challenging signal is softened."
                )

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
