"""Gocharam timeline and reading generation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import swisseph as swe

from ..nakshatra import nakshatra_of
from ..positions import (
    degree_in_sign,
    house_from_lagna,
    sidereal_positions,
    sign_index,
    sign_name,
    to_dms,
)
from .rules import GocharaRuleDefinition, RULE_DEFINITIONS, classical_gochara_status

TRANSIT_PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
GOCHARA_TIMELINE_RULE_DAYS = 365
GOCHARA_PROFILE_PAST_DAYS = 365 * 3
GOCHARA_PROFILE_FUTURE_DAYS = 365 * 3
GOCHARA_ACTIVE_WINDOW_DAYS = 3650


def _jd_from_dt(dt: datetime) -> float:
    dt_utc = dt.astimezone(timezone.utc)
    hour = dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, hour)


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


def _details(transit_positions: dict, natal_lagna_sign: int, natal_moon_sign: int) -> dict:
    return {
        planet: _planet_snapshot(transit_positions, planet, natal_lagna_sign, natal_moon_sign)
        for planet in TRANSIT_PLANETS
        if planet in transit_positions
    }


def _rule_house(rule: GocharaRuleDefinition, details: dict) -> int:
    key = "house_from_lagna" if rule.anchor == "lagna" else "house_from_moon"
    return details[rule.planet][key]


def _trigger(rule: GocharaRuleDefinition, house: int) -> str:
    anchor = "natal Lagna" if rule.anchor == "lagna" else "natal Moon"
    return f"{rule.planet} is {house} from {anchor}"


def _severity(rule: GocharaRuleDefinition, active: bool) -> str:
    if not active:
        return "none" if rule.tone == "challenging" else "neutral"
    return rule.severity


def _explanation(rule: GocharaRuleDefinition, active: bool, trigger: str) -> str:
    state = "active" if active else "not active"
    reading = rule.plain_when_active if active else rule.plain_when_inactive
    return (
        f"{trigger}, so {rule.name} is {state}. "
        f"South-Indian Gocharam practice reads this from {'Lagna' if rule.anchor == 'lagna' else 'Moon'} as the primary anchor for this rule. "
        f"{rule.principle} "
        f"{reading}"
    )


def gochara_rules(transit_positions: dict, natal_lagna_sign: int, natal_moon_sign: int) -> dict:
    details = _details(transit_positions, natal_lagna_sign, natal_moon_sign)
    classical = classical_gochara_status(
        {planet: snapshot["house_from_moon"] for planet, snapshot in details.items()}
    )
    rules = []
    for definition in RULE_DEFINITIONS:
        house = _rule_house(definition, details)
        active = house in definition.active_houses
        trigger = _trigger(definition, house)
        note = definition.principle
        status = classical.get(definition.planet)
        obstructed = bool(
            active
            and definition.tone == "supportive"
            and status
            and status["vedha"]["obstructed"]
        )
        if obstructed:
            vedha = status["vedha"]
            note += (
                f" Vedha: {definition.planet}'s favourable transit is obstructed by {vedha['by']} "
                f"transiting the {vedha['vedha_house']}th house from natal Moon, so the promised "
                "support is weakened while the vedha lasts."
            )
        rules.append({
            "id": definition.id,
            "name": definition.name,
            "planet": definition.planet,
            "anchor": definition.anchor,
            "house": house,
            "active": active,
            "severity": _severity(definition, active),
            "tone": definition.tone if active else "neutral",
            "trigger": trigger,
            "note": note,
            "obstructed": obstructed,
            "explanation": _explanation(definition, active, trigger),
            "verified": True,
            "source_status": definition.source_status,
        })

    saturn_rule = next(rule for rule in rules if rule["id"] == "gochara_sade_sati")
    return {
        "planets": details,
        "rules": rules,
        "active_rules": [rule for rule in rules if rule["active"]],
        "classical_gochara": classical,
        "core_reading": core_reading(rules, saturn_rule["house"], natal_moon_sign, natal_lagna_sign),
        "sade_sati": {
            "active": saturn_rule["active"],
            "phase": {12: "first", 1: "second", 2: "third"}.get(saturn_rule["house"]),
            "saturn_house_from_moon": saturn_rule["house"],
        },
    }


def _rule_state(dt: datetime, natal_lagna_sign: int, natal_moon_sign: int, ayanamsha: str, node_type: str) -> dict[str, dict]:
    positions = sidereal_positions(_jd_from_dt(dt), ayanamsha, node_type)
    return {rule["id"]: rule for rule in gochara_rules(positions, natal_lagna_sign, natal_moon_sign)["rules"]}


def _is_rule_active(dt: datetime, rule_id: str, natal_lagna_sign: int, natal_moon_sign: int, ayanamsha: str, node_type: str) -> bool:
    return _rule_state(dt, natal_lagna_sign, natal_moon_sign, ayanamsha, node_type)[rule_id]["active"]


def _active_rule_start(as_of: datetime, rule_id: str, natal_lagna_sign: int, natal_moon_sign: int, ayanamsha: str, node_type: str) -> str | None:
    active_dt = as_of
    inactive_dt = None
    for days in range(7, GOCHARA_ACTIVE_WINDOW_DAYS + 1, 7):
        candidate = as_of - timedelta(days=days)
        if not _is_rule_active(candidate, rule_id, natal_lagna_sign, natal_moon_sign, ayanamsha, node_type):
            inactive_dt = candidate
            break
        active_dt = candidate
    if inactive_dt is None:
        return None
    cursor = inactive_dt + timedelta(days=1)
    while cursor <= active_dt + timedelta(days=7):
        if _is_rule_active(cursor, rule_id, natal_lagna_sign, natal_moon_sign, ayanamsha, node_type):
            return cursor.date().isoformat()
        cursor += timedelta(days=1)
    return active_dt.date().isoformat()


def _active_rule_end(as_of: datetime, rule_id: str, natal_lagna_sign: int, natal_moon_sign: int, ayanamsha: str, node_type: str) -> str | None:
    active_dt = as_of
    inactive_dt = None
    for days in range(7, GOCHARA_ACTIVE_WINDOW_DAYS + 1, 7):
        candidate = as_of + timedelta(days=days)
        if not _is_rule_active(candidate, rule_id, natal_lagna_sign, natal_moon_sign, ayanamsha, node_type):
            inactive_dt = candidate
            break
        active_dt = candidate
    if inactive_dt is None:
        return None
    cursor = active_dt
    last_active = active_dt
    while cursor <= inactive_dt:
        if _is_rule_active(cursor, rule_id, natal_lagna_sign, natal_moon_sign, ayanamsha, node_type):
            last_active = cursor
        else:
            break
        cursor += timedelta(days=1)
    return last_active.date().isoformat()


def _rule_tone(rule: dict, active: bool = True) -> str:
    if not active:
        return "neutral"
    return "supportive" if rule["severity"] == "supportive" else "challenging"


def _window_text(active_windows: list[dict] | None) -> str:
    if not active_windows:
        return "No major Gocharam rule window is active today."
    parts = []
    for window in active_windows[:3]:
        start = window.get("start_date") or "before the scan window"
        end = window.get("end_date") or "beyond the scan window"
        parts.append(f"{window['rule']} runs from {start} to {end}")
    return "; ".join(parts) + "."


def core_reading(
    rules: list[dict],
    saturn_from_moon: int,
    natal_moon_sign: int,
    natal_lagna_sign: int,
    active_windows: list[dict] | None = None,
) -> dict:
    active_rules = [rule for rule in rules if rule["active"]]
    challenging = [rule for rule in active_rules if rule["tone"] == "challenging"]
    supportive = [rule for rule in active_rules if rule["tone"] == "supportive"]
    if challenging and supportive:
        tone = "mixed"
        title = "Mixed Gocharam: pressure and protection are both active"
    elif challenging:
        tone = "challenging"
        title = "Caution Gocharam: pressure signals are active"
    elif supportive:
        tone = "supportive"
        title = "Supportive Gocharam: growth signals are active"
    else:
        tone = "neutral"
        title = "Neutral Gocharam: no major classical trigger is active"

    active_names = ", ".join(rule["name"] for rule in active_rules[:3]) or "no major rule trigger"
    timing = _window_text(active_windows)
    rationale = (
        f"This Gocharam is judged in the South-Indian style: Moon first, Lagna as a practical cross-check. "
        f"The natal Moon is {sign_name(natal_moon_sign)}, the Lagna is {sign_name(natal_lagna_sign)}, and Saturn is "
        f"{saturn_from_moon} from the Moon. The active rule set found {active_names}. {timing}"
    )
    if challenging and supportive:
        reading = (
            "This is a mixed phase. Some areas may feel slow, heavy, or uncertain, but there is still support for learning, planning, recovery, or guidance. "
            "Move carefully where pressure is visible, and use the supportive window for steady progress."
        )
    elif challenging:
        reading = (
            "This period asks for patience. Avoid rushed decisions, keep routines simple, and handle responsibilities one by one. "
            "The pressure can reduce when the active Gocharam window closes."
        )
    elif supportive:
        reading = (
            "This is a helpful background period. It supports planning, guidance, learning, family support, repairs, and steady growth. "
            "Use the window while it is active instead of waiting for perfect timing."
        )
    else:
        reading = (
            "No major Gocharam pressure or support rule is active right now. Daily choices, dasha, Moon movement, and exact aspects may matter more than big transit rules. "
            "Check the upcoming timeline for the next stronger phase."
        )
    return {
        "title": title,
        "tone": tone,
        "rationale": rationale,
        "reading": reading,
        "timing_summary": timing,
        "active_rule_count": len(active_rules),
        "supportive_rule_count": len(supportive),
        "challenging_rule_count": len(challenging),
    }


def _period_reading(rule: dict, start_date: str | None, end_date: str | None, status: str) -> dict:
    start = start_date or "before the scan window"
    end = end_date or "beyond the scan window"
    status_text = {"past": "was active", "current": "is active now", "future": "will be active"}.get(status, "is tracked")
    rationale = (
        f"{rule['name']} {status_text} because {rule['trigger']}. "
        f"The period runs from {start} to {end}. This uses the South-Indian Moon-first Gocharam rule set."
    )
    plain = (
        f"{rule['name']} describes a {'supportive' if rule['tone'] == 'supportive' else 'caution'} background during this window. "
        f"{rule['explanation'].split('. ')[-1]}"
    )
    return {
        "rationale": rationale,
        "reading": plain,
        "validation_prompt": (
            f"Review events between {start} and {end}. Did this period feel "
            f"{'supportive and easier to use' if rule['tone'] == 'supportive' else 'heavier, sharper, delayed, or more uncertain'}?"
        ),
    }


def _period_strength(rule: dict) -> int:
    if rule["severity"] == "high":
        return 92
    if rule["severity"] == "medium":
        return 76
    if rule["severity"] == "supportive":
        return 82
    return 55


def _timeline_events(
    as_of: datetime,
    natal_lagna_sign: int,
    natal_moon_sign: int,
    ayanamsha: str,
    node_type: str,
    days: int,
    direction: int,
) -> list[dict]:
    events = []
    previous_state = _rule_state(as_of, natal_lagna_sign, natal_moon_sign, ayanamsha, node_type)
    for offset in range(1, days + 1):
        day = as_of + timedelta(days=offset * direction)
        state = _rule_state(day, natal_lagna_sign, natal_moon_sign, ayanamsha, node_type)
        for rule_id, rule in state.items():
            was_active = previous_state[rule_id]["active"]
            is_active = rule["active"]
            if was_active == is_active:
                continue
            if direction > 0:
                transition = "starts" if is_active else "ends"
                event_rule = rule if is_active else previous_state[rule_id]
                date = day.date().isoformat()
            else:
                transition = "started" if was_active else "ended"
                event_rule = previous_state[rule_id] if was_active else rule
                date = (day + timedelta(days=1)).date().isoformat()
            events.append({
                "date": date,
                "type": "gochara_rule",
                "planet": event_rule["planet"],
                "title": f"{event_rule['name']} {transition}",
                "detail": event_rule["trigger"],
                "tone": _rule_tone(event_rule, True),
                "strength": _period_strength(event_rule),
                "rule": event_rule["name"],
                "rule_id": event_rule["id"],
                "transition": transition,
            })
        previous_state = state
    reverse = direction < 0
    events.sort(key=lambda event: (event["date"], -event["strength"], event["title"]), reverse=reverse)
    return events


def _timeline_core_reading(events: list[dict], mode: str, scan_days: int) -> dict:
    if not events:
        title = "No major Gocharam rule change is coming soon" if mode == "next" else "No major Gocharam rule change was found recently"
        window = "next" if mode == "next" else "previous"
        return {
            "title": title,
            "tone": "neutral",
            "rationale": f"The {window} scan checked South-Indian Gocharam rule transitions for {scan_days} days and found no major start/end change.",
            "reading": "The big Gocharam background is stable. Look at dasha, Moon movement, and exact transit aspects for smaller changes.",
            "timing_summary": "No major rule transition in the scan window.",
        }
    first = events[0]
    names = ", ".join(f"{event['title']} on {event['date']}" for event in events[:3])
    label = "What next" if mode == "next" else "What happened before"
    return {
        "title": f"{label}: {first['title']}",
        "tone": first["tone"],
        "rationale": f"The {mode} Gocharam scan found {names}. These are deterministic dates where a rule changes active state.",
        "reading": (
            f"Around {first['date']}, the background tone can shift. Use that date as a validation or planning marker, "
            "not as a single isolated event."
        ),
        "timing_summary": f"{first['title']} on {first['date']}.",
    }


def gocharam_rule_timeline(
    as_of: datetime,
    natal_lagna_sign: int,
    natal_moon_sign: int,
    ayanamsha: str,
    node_type: str,
    current_gochara: dict,
    scan_days: int = GOCHARA_TIMELINE_RULE_DAYS,
) -> dict:
    active_windows = []
    for rule in current_gochara["active_rules"]:
        start = _active_rule_start(as_of, rule["id"], natal_lagna_sign, natal_moon_sign, ayanamsha, node_type)
        end = _active_rule_end(as_of, rule["id"], natal_lagna_sign, natal_moon_sign, ayanamsha, node_type)
        active_windows.append({
            "rule": rule["name"],
            "rule_id": rule["id"],
            "planet": rule["planet"],
            "start_date": start,
            "end_date": end,
            "tone": _rule_tone(rule),
            "trigger": rule["trigger"],
            "summary": f"{rule['name']} is active now. It began {start or 'before the scan window'} and is estimated to remain active until {end or 'beyond the scan window'}.",
        })

    previous_events = _timeline_events(as_of, natal_lagna_sign, natal_moon_sign, ayanamsha, node_type, scan_days, -1)[:24]
    next_events = _timeline_events(as_of, natal_lagna_sign, natal_moon_sign, ayanamsha, node_type, scan_days, 1)[:36]
    return {
        "active_windows": active_windows,
        "previous_365_days": previous_events,
        "next_365_days": next_events,
        "scan_days": scan_days,
    }


def _periods_from_events(as_of: datetime, current_gochara: dict, timeline: dict, all_events: list[dict]) -> list[dict]:
    periods = []
    for window in timeline["active_windows"]:
        rule = next(rule for rule in current_gochara["rules"] if rule["id"] == window["rule_id"])
        reading = _period_reading(rule, window["start_date"], window["end_date"], "current")
        periods.append({
            **window,
            "status": "current",
            "strength": _period_strength(rule),
            **reading,
        })
    for event in all_events:
        if "starts" not in event["transition"] and event["transition"] != "started":
            continue
        rule = next((r for r in current_gochara["rules"] if r["id"] == event["rule_id"]), None)
        if not rule:
            continue
        status = "future" if event["date"] >= as_of.date().isoformat() else "past"
        reading = _period_reading(rule, event["date"], None, status)
        periods.append({
            "rule": rule["name"],
            "rule_id": rule["id"],
            "planet": rule["planet"],
            "start_date": event["date"],
            "end_date": None,
            "tone": rule["tone"],
            "trigger": rule["trigger"],
            "summary": event["title"],
            "status": status,
            "strength": _period_strength(rule),
            **reading,
        })
    periods.sort(key=lambda period: ((period["start_date"] or ""), period["rule"]))
    return periods


def gocharam_profile(
    natal_positions: dict,
    natal_lagna_lon: float,
    as_of: datetime,
    ayanamsha: str,
    node_type: str,
    past_days: int = GOCHARA_PROFILE_PAST_DAYS,
    future_days: int = GOCHARA_PROFILE_FUTURE_DAYS,
) -> dict:
    natal_lagna_sign = sign_index(natal_lagna_lon)
    natal_moon_sign = sign_index(natal_positions["Moon"]["lon"])
    current_positions = sidereal_positions(_jd_from_dt(as_of), ayanamsha, node_type)
    current = gochara_rules(current_positions, natal_lagna_sign, natal_moon_sign)
    timeline = gocharam_rule_timeline(
        as_of,
        natal_lagna_sign,
        natal_moon_sign,
        ayanamsha,
        node_type,
        current,
        max(past_days, future_days),
    )
    current["timeline"] = timeline
    current["core_reading"] = core_reading(
        current["rules"],
        current["sade_sati"]["saturn_house_from_moon"],
        natal_moon_sign,
        natal_lagna_sign,
        timeline["active_windows"],
    )
    current["core_reading"]["next"] = _timeline_core_reading(timeline["next_365_days"], "next", future_days)
    current["core_reading"]["previous"] = _timeline_core_reading(timeline["previous_365_days"], "previous", past_days)
    periods = _periods_from_events(as_of, current, timeline, timeline["previous_365_days"] + timeline["next_365_days"])
    return {
        "system": "South Indian Gocharam",
        "as_of": as_of.isoformat(),
        "ayanamsha": ayanamsha,
        "node_type": node_type,
        "natal": {"lagna_sign": sign_name(natal_lagna_sign), "moon_sign": sign_name(natal_moon_sign)},
        "gochara": current,
        "periods": periods,
        "coverage": {
            "past_days": past_days,
            "future_days": future_days,
            "strategy": "pre-generated deterministic rule windows for this profile timeline",
        },
        "notes": [
            "Moon is the primary Gocharam anchor; Lagna is used as a practical cross-check.",
            "Readings are deterministic text generated from rule windows, not AI.",
        ],
    }
