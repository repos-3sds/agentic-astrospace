"""
Daily guidance — the "Today for You" panel, assembled through the Context Engine.

Every field here is COMPUTED from the day's panchanga and the person's gochara;
nothing is generic. The verdict, colour of the day, number of the day, and the
do/avoid windows are each derived from named, rule-based signals, and the raw
signals ride along so the UI can show the "why" behind every line.

CE wiring: `assemble_daily_context` builds a Context-Engine bundle (current
gochara with vedha/ashtakavarga, the active dasha chain, the day's personal
panchanga, and KB references routed by the day's dominant signal). The
presentable `daily_guidance` payload is assembled entirely from that bundle.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from ..core.vedic.constants import PLANET_COLORS, PLANET_NUMBER
from ..core.vedic.favourable import digital_root, favourable_points
from ..core.vedic.nakshatra import nakshatra_of
from ..core.vedic.panchanga_day import daily_panchanga, personal_panchanga
from ..core.vedic.positions import sign_index
from ..core.vedic.transits import _jd_from_dt, gochara_rules
from ..core.vedic.positions import sidereal_positions
from .kb import get_knowledge_base

# Plain-language meaning of each tara (the star of the day counted from the
# birth star). {you}/{poss} are filled per subject. BPHS/Muhurta convention.
TARABALA_MEANING = {
    "Janma": "{poss} birth star returns, making this a reflective, inward day best kept for routine rather than fresh launches",
    "Sampat": "one of the naturally prosperous stars for {you}, favouring money matters, purchases and steady forward moves",
    "Vipat": "a cautionary star that asks {you} to guard against loss, delay and hasty risks today",
    "Kshema": "a well-being star that supports health, stability and quiet, dependable progress",
    "Pratyari": "an obstacle-prone star, so expect a little friction and give tasks extra patience",
    "Sadhaka": "an accomplishment star that is strong for finishing work and pushing goals over the line",
    "Vadha": "a difficult star, so it is wise to avoid confrontation and postpone major decisions",
    "Mitra": "a friendly star that favours people, alliances, teamwork and asking for support",
    "Parama Mitra": "{poss} closest-friend star and one of the most naturally fortunate days in {poss} cycle",
}

_FAVOURABLE_TARAS = {"Sampat", "Kshema", "Sadhaka", "Mitra", "Parama Mitra"}


def _subject_words(relation: str | None) -> dict[str, str]:
    is_self = (relation or "").lower() in ("self", "myself", "me")
    if is_self:
        # "you" is used in object position in the tara meanings ("for you").
        return {"who": "you", "you": "you", "poss": "your", "cap_poss": "Your"}
    return {"who": "this profile", "you": "them", "poss": "their", "cap_poss": "Their"}


def _day_color(vara_lord: str, supportive_planet: str | None,
               challenging_planet: str | None) -> dict:
    name, hex_ = PLANET_COLORS[vara_lord]
    out = {
        "name": name,
        "hex": hex_,
        "planet": vara_lord,
        "source": f"colour of {vara_lord}, lord of today's weekday (vara)",
    }
    if supportive_planet and supportive_planet in PLANET_COLORS:
        pname, phex = PLANET_COLORS[supportive_planet]
        out["power_color"] = {
            "name": pname, "hex": phex, "planet": supportive_planet,
            "source": f"{supportive_planet} is running a supportive transit for this profile",
        }
    if challenging_planet and challenging_planet in PLANET_COLORS:
        cname, chex = PLANET_COLORS[challenging_planet]
        out["caution_color"] = {
            "name": cname, "hex": chex, "planet": challenging_planet,
            "source": f"{challenging_planet} is running a challenging transit; ease off this shade today",
        }
    return out


def _day_number(as_of: datetime, vara_lord: str, favourable: dict) -> dict:
    value = digital_root(as_of.year + as_of.month + as_of.day)
    ruling_number = PLANET_NUMBER[vara_lord]
    good = favourable.get("good_numbers", [])
    evil = favourable.get("evil_numbers", [])
    fit = "favourable" if value in good else "challenging" if value in evil else "neutral"
    return {
        "value": value,
        "fit": fit,
        "ruling_planet": vara_lord,
        "ruling_number": ruling_number,
        "personal_good": good,
        "personal_evil": evil,
        "source": (
            "digital root of today's date; ruling number from the weekday lord "
            "(vara); fit judged against birth numerology"
        ),
    }


def _window_time(window: dict | None) -> str | None:
    if not window:
        return None
    return f"{window['start']}–{window['end']}"


def _find_window(windows: list[dict], name: str) -> dict | None:
    return next((w for w in windows if w.get("name", "").startswith(name)), None)


def assemble_daily_context(chart, as_of: datetime, day_payload: dict,
                           personal: dict) -> dict:
    """CE bundle for the day: gochara + dasha chain + personal panchanga +
    KB references routed by the day's dominant tone."""
    positions = sidereal_positions(_jd_from_dt(as_of), chart.ayanamsha, chart.node_type)
    lagna_sign = sign_index(chart.lagna_lon)
    moon_sign = sign_index(chart.positions["Moon"]["lon"])
    gochara = gochara_rules(positions, lagna_sign, moon_sign)

    dashas = chart.dashas()
    current = dashas.get("current", {})
    dasha_chain = [
        {"level": lvl, "lord": current[lvl]["lord"]}
        for lvl in ("mahadasha", "antardasha", "pratyantardasha")
        if current.get(lvl)
    ]

    active = gochara.get("active_rules", [])
    supportive = [r for r in active if r.get("severity") == "supportive"]
    challenging = [r for r in active if r.get("severity") in ("high", "medium")]

    # Route KB references by the day's dominant signal, reusing the CE store.
    if personal.get("chandrabala", {}).get("chandrashtama") or challenging:
        route_domain = "health"
    elif supportive:
        route_domain = "wealth"
    else:
        route_domain = "career"
    references = [
        ref.to_dict()
        for ref in get_knowledge_base().retrieve([route_domain], limit=3)
    ]

    return {
        "gochara": gochara,
        "dasha_chain": dasha_chain,
        "personal_panchanga": personal,
        "route_domain": route_domain,
        "references": references,
        "supportive_rules": supportive,
        "challenging_rules": challenging,
    }


def _score_day(personal: dict, ctx: dict) -> tuple[int, str, str]:
    tara = personal.get("tarabala", {})
    chandra = personal.get("chandrabala", {})
    score = 0
    if tara.get("tara") in _FAVOURABLE_TARAS:
        score += 2
    elif tara.get("tara") == "Janma":
        score -= 1
    else:
        score -= 2
    if chandra.get("chandrashtama"):
        score -= 3
    elif chandra.get("favourable"):
        score += 1
    else:
        score -= 1
    for rule in ctx["supportive_rules"]:
        score += 1
    for rule in ctx["challenging_rules"]:
        score -= 2 if rule.get("severity") == "high" else 1
    matched = [a for a in personal.get("ghatak_alerts", []) if a.get("matched")]
    score -= len(matched)

    if score >= 3:
        return score, "supportive", "a strong, supportive day"
    if score >= 1:
        return score, "positive", "a mostly favourable day"
    if score >= -1:
        return score, "mixed", "a mixed day that rewards a measured approach"
    return score, "caution", "a day for patience and a lighter touch"


def _verdict(chart, relation: str, day_payload: dict, personal: dict,
             ctx: dict) -> dict:
    words = _subject_words(relation)
    you, poss = words["you"], words["poss"]
    score, tone, headline = _score_day(personal, ctx)

    subject = "you" if words["who"] == "you" else chart.name
    tara = personal.get("tarabala", {})
    tara_name = tara.get("tara", "")
    nak_name = day_payload["elements"]["nakshatra"][0]["name"]
    meaning = TARABALA_MEANING.get(tara_name, "a neutral star for the day").format(
        you=you, poss=poss)

    sentences: list[str] = []
    sentences.append(
        f"Today looks like {headline} for {subject}. The Moon travels through "
        f"{nak_name}, which counts as {tara_name} from {poss} birth star — {meaning}."
    )

    chandra = personal.get("chandrabala", {})
    chandra_clause = ""
    if chandra.get("chandrashtama"):
        chandra_clause = (
            f"The Moon also sits in {poss} eighth from the birth sign (chandrashtama), "
            "so energy and mood may dip — go gently and avoid forcing big decisions"
        )
    elif chandra.get("favourable"):
        chandra_clause = (
            f"The Moon rides a comfortable house from {poss} sign, keeping the "
            "emotional tone steady and cooperative"
        )
    else:
        chandra_clause = (
            f"The Moon sits in a mildly draining house from {poss} sign, so it helps "
            "to keep the day light rather than overcommitted"
        )

    gochara_clause = ""
    if ctx["supportive_rules"]:
        r = ctx["supportive_rules"][0]
        gochara_clause = (
            f"On the transit side, {r['name']} is active, which softens pressure and "
            "makes guidance, planning and recovery easier to reach"
        )
    elif ctx["challenging_rules"]:
        r = ctx["challenging_rules"][0]
        gochara_clause = (
            f"On the transit side, {r['name']} is running, so expect a slower, more "
            "demanding background that asks for patience over speed"
        )
    else:
        gochara_clause = (
            "No major slow-planet transit rule is active, so daily choices and the "
            "Moon's movement matter more than big gochara pressure right now"
        )
    sentences.append(f"{chandra_clause}. {gochara_clause}.")

    dasha_clause = ""
    if ctx["dasha_chain"]:
        path = " / ".join(d["lord"] for d in ctx["dasha_chain"])
        dasha_clause = f"The running dasha is {path}, the backdrop these themes play out against"
    rahu = _find_window(day_payload["windows"]["inauspicious"], "Rahu Kalam")
    rahu_time = _window_time(rahu)
    caution_clause = (
        f"keep the {rahu_time} window (Rahu Kalam) for routine work rather than fresh starts"
        if rahu_time else "watch the daily inauspicious windows before starting anything major"
    )
    closing = {
        "supportive": "lean into the day and use the openings while they are here",
        "positive": "move forward steadily and make the most of the favourable tone",
        "mixed": "pick your moments, keep commitments realistic, and avoid overreach",
        "caution": "slow down, protect your energy, and postpone anything that can wait",
    }[tone]
    tail = f"{dasha_clause}; {caution_clause}. Overall, {closing}." if dasha_clause \
        else f"Practically, {caution_clause}. Overall, {closing}."
    sentences.append(tail)

    text = " ".join(sentences)
    return {
        "tone": tone,
        "score": score,
        "headline": headline.capitalize(),
        "text": text,
        "word_count": len(text.split()),
    }


def _do_and_avoid(day_payload: dict, personal: dict, ctx: dict,
                  words: dict) -> tuple[list[dict], list[dict]]:
    poss = words["poss"]
    do: list[dict] = []
    avoid: list[dict] = []

    tara = personal.get("tarabala", {})
    if tara.get("tara") in _FAVOURABLE_TARAS:
        do.append({"text": f"Favourable star day ({tara['tara']}) — good for meaningful starts",
                   "source": "tarabala"})
    elif tara.get("tara") and tara.get("tara") != "Janma":
        avoid.append({"text": f"{tara['tara']} star — hold off on major new commitments",
                      "source": "tarabala"})

    if personal.get("chandrabala", {}).get("chandrashtama"):
        avoid.append({"text": "Chandrashtama — postpone big decisions and travel if you can",
                      "source": "chandrabala"})

    for rule in ctx["supportive_rules"]:
        do.append({"text": f"{rule['name']} is supporting you — plan, learn, seek guidance",
                   "source": "gochara"})
    for rule in ctx["challenging_rules"]:
        avoid.append({"text": f"{rule['name']} is active — avoid rushed or risky moves",
                      "source": "gochara"})

    abhijit = _find_window(day_payload["windows"]["auspicious"], "Abhijit")
    if abhijit:
        do.append({"text": f"Best window {_window_time(abhijit)} (Abhijit Muhurta)",
                   "source": "muhurta", "window": _window_time(abhijit)})
    rahu = _find_window(day_payload["windows"]["inauspicious"], "Rahu Kalam")
    if rahu:
        avoid.append({"text": f"Avoid new starts {_window_time(rahu)} (Rahu Kalam)",
                      "source": "muhurta", "window": _window_time(rahu)})

    for alert in personal.get("ghatak_alerts", []):
        if alert.get("matched"):
            avoid.append({"text": f"Ghatak {alert['type']} match ({alert['ghatak_value']}) — a traditionally tricky marker",
                          "source": "ghatak"})
    return do, avoid


def daily_guidance(chart, relation: str | None = None, as_of: datetime | None = None,
                   city: str | None = None, nation: str | None = None,
                   lat: float | None = None, lng: float | None = None,
                   tz_str: str | None = None) -> dict:
    """The full 'Today for You' payload. Location defaults to the birth place."""
    tz = tz_str or chart.moment.tz_str
    as_of = as_of or datetime.now(ZoneInfo(tz))
    if as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=ZoneInfo(tz))

    place_city = city or chart.city
    place_nation = nation or "IN"
    place_lat = chart.moment.lat if lat is None else lat
    place_lng = chart.moment.lng if lng is None else lng

    day_payload = daily_panchanga(
        as_of.year, as_of.month, as_of.day,
        place_city, place_nation, place_lat, place_lng, tz, tz,
    )

    moon_lon = chart.positions["Moon"]["lon"]
    janma_nak = nakshatra_of(moon_lon)
    janma_rashi = sign_index(moon_lon)
    personal = personal_panchanga(
        day_payload, janma_nakshatra_index=janma_nak["index"],
        janma_rashi_index=janma_rashi, ghatak_moon_sign=janma_rashi,
    )

    ctx = assemble_daily_context(chart, as_of, day_payload, personal)
    words = _subject_words(relation)

    vara_lord = day_payload["vara"]["lord"]
    supportive_planet = ctx["supportive_rules"][0]["planet"] if ctx["supportive_rules"] else None
    challenging_planet = ctx["challenging_rules"][0]["planet"] if ctx["challenging_rules"] else None

    lagna_sign = sign_index(chart.lagna_lon)
    atmakaraka = chart.jaimini()["chara_karakas"]["karakas"]["AK"]["planet"]
    favourable = favourable_points(
        chart.birth_day_of_month, lagna_sign,
        moon_sign=janma_rashi, nakshatra_lord=janma_nak["lord"],
        atmakaraka=atmakaraka,
    )
    astro_number = favourable["astrological_number"]

    verdict = _verdict(chart, relation or "", day_payload, personal, ctx)
    do_today, avoid_today = _do_and_avoid(day_payload, personal, ctx, words)

    return {
        "system": "AstroSpace Daily Guidance",
        "as_of": as_of.isoformat(),
        "date": day_payload["date"],
        "subject": chart.name,
        "relation": relation,
        "vara": day_payload["vara"]["name"],
        "verdict": verdict,
        "color": _day_color(vara_lord, supportive_planet, challenging_planet),
        "number": _day_number(as_of, vara_lord, favourable),
        "tarabala": personal["tarabala"],
        "chandrabala": personal["chandrabala"],
        "star_of_day": {
            "nakshatra": day_payload["elements"]["nakshatra"][0]["name"],
            "moon_rashi": day_payload["moon_rashi_at_sunrise"],
            "tithi": day_payload["elements"]["tithi"][0]["name"],
        },
        "do_today": do_today,
        "avoid_today": avoid_today,
        "lucky_signature": {
            "gem": favourable["lucky_stone"],
            "metal": favourable["lucky_metal"],
            "direction": favourable["lucky_direction"],
            "days": favourable["lucky_days"],
        },
        "lucky_numbers": {
            "numerology": {
                "number": favourable["lucky_number"],
                "ruling_planet": favourable["ruling_planet"],
                "good_numbers": favourable["good_numbers"],
                "evil_numbers": favourable["evil_numbers"],
                "source": "digital root of birth day-of-month (moolank)",
            },
            "astrological": astro_number,
        },
        "context": {
            "route_domain": ctx["route_domain"],
            "dasha_chain": ctx["dasha_chain"],
            "references": ctx["references"],
            "active_gochara": [
                {"name": r["name"], "planet": r["planet"], "severity": r.get("severity")}
                for r in ctx["gochara"].get("active_rules", [])
            ],
        },
        "provenance": {
            "engine": "computed from panchanga + gochara via the Context Engine",
            "place": {"city": place_city, "nation": place_nation, "timezone": tz},
            "note": "Every line is rule-derived; expand any card to see its source signal.",
        },
    }
