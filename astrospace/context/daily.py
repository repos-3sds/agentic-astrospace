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
from ..core.vedic.gocharam import gochara_rules
from ..core.vedic.gocharam.strength import (
    apply_ashtakavarga_context,
    ashtakavarga_transit_support,
)
from ..core.vedic.transits import _jd_from_dt
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
    gochara = gochara_rules(positions, chart.positions, lagna_sign, moon_sign)
    av_support = ashtakavarga_transit_support(chart.ashtakavarga(), positions)
    apply_ashtakavarga_context(gochara, av_support)

    dashas = chart.dashas()
    current = dashas.get("current", {})
    dasha_chain = [
        {"level": lvl, "lord": current[lvl]["lord"]}
        for lvl in ("mahadasha", "antardasha", "pratyantardasha", "sookshmadasha")
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
        return score, "supportive", "a rare window of clarity"
    if score >= 1:
        return score, "positive", "a quietly powerful day"
    if score >= -1:
        return score, "mixed", "a day of friction and flow"
    return score, "caution", "a day to pull back and observe"


def _verdict(chart, relation: str, day_payload: dict, personal: dict,
             ctx: dict) -> dict:
    words = _subject_words(relation)
    score, tone, headline = _score_day(personal, ctx)

    subject = "you" if words["who"] == "you" else chart.name
    tara = personal.get("tarabala", {})
    tara_name = tara.get("tara", "")
    chandra = personal.get("chandrabala", {})
    sentences: list[str] = [f"Today looks like {headline} for {subject}."]

    if tara_name in _FAVOURABLE_TARAS:
        sentences.append("The stars align for steady motion. Say what you mean and follow through.")
    elif tara_name and tara_name != "Janma":
        sentences.append("The energy is jagged. Be fiercely selective about where you put your attention.")
    else:
        sentences.append("Your own birth star returns. Retreat, reflect, and refuse to rush.")

    if chandra.get("chandrashtama"):
        sentences.append("The Moon crosses a shadow zone. Expect emotional static—don't force a resolution.")
    elif chandra.get("favourable"):
        sentences.append("The lunar current is steady, offering a rare moment of internal quiet.")
    else:
        sentences.append("The lunar tide is pulling away. Protect your time and stay close to the ground.")

    if ctx["supportive_rules"]:
        sentences.append("A long-term cosmic tailwind is at your back. Lean into the momentum.")
    elif ctx["challenging_rules"]:
        sentences.append("A heavy planetary anchor is dragging. Patience isn't optional today.")
    else:
        sentences.append("The deep sky is quiet. The day is what you make of it.")

    rahu = _find_window(day_payload["windows"]["inauspicious"], "Rahu Kalam")
    rahu_time = _window_time(rahu)
    caution_clause = (
        f"Keep {rahu_time} for routine work rather than fresh starts"
        if rahu_time else "watch the daily inauspicious windows before starting anything major"
    )
    closing = {
        "supportive": "take the shot—the window won't stay open forever",
        "positive": "keep your head down and let the current do the work",
        "mixed": "play it cool, hold your boundaries, and don't overreach",
        "caution": "disappear into the background until the weather breaks",
    }[tone]
    sentences.append(f"Practically, {caution_clause}. Overall, {closing}.")

    text = " ".join(sentences)
    return {
        "tone": tone,
        "score": score,
        "headline": headline.capitalize(),
        "text": text,
        "word_count": len(text.split()),
    }


def _plain_why(day_payload: dict, personal: dict, ctx: dict, words: dict) -> list[str]:
    poss = words["poss"]
    tara = personal.get("tarabala", {})
    chandra = personal.get("chandrabala", {})
    why: list[str] = []

    tara_name = tara.get("tara")
    if tara_name in _FAVOURABLE_TARAS:
        why.append("Your personal timing marker is green. The friction is gone.")
    elif tara_name and tara_name != "Janma":
        why.append("Your personal timing marker flashes yellow. Reduce risk and step carefully.")
    else:
        why.append("Your personal timing marker points inward. It's a day for reflection, not action.")

    if chandra.get("chandrashtama"):
        why.append("The Moon sits in its most vulnerable house for you. Emotions will run hot.")
    elif chandra.get("favourable"):
        why.append(f"The Moon sits comfortably from {poss} birth sign, anchoring your mood.")
    else:
        why.append("The Moon is indifferent today. You'll need to generate your own emotional warmth.")

    if ctx["supportive_rules"]:
        why.append("A slow-moving transit is actively supporting your chart, granting long-term clarity.")
    elif ctx["challenging_rules"]:
        why.append("A heavy outer planet is testing your chart. Slow, deliberate choices are required.")
    else:
        why.append("No major outer planet transit is pressing on your chart. The daily weather rules.")
    return why


def _technical_why(day_payload: dict, personal: dict, ctx: dict) -> list[str]:
    nak_name = day_payload["elements"]["nakshatra"][0]["name"]
    tithi_name = day_payload["elements"]["tithi"][0]["name"]
    tara = personal.get("tarabala", {})
    chandra = personal.get("chandrabala", {})
    rows = [
        f"Nakshatra: {nak_name}",
        f"Tithi: {tithi_name}",
        f"Tarabala: {tara.get('tara', '—')} ({tara.get('count', '—')}/9)",
        f"Chandrabala: house {chandra.get('house_from_rashi', '—')} from natal Moon",
    ]
    if ctx["dasha_chain"]:
        rows.append("Dasha: " + " / ".join(d["lord"] for d in ctx["dasha_chain"]))
    for rule in ctx["gochara"].get("active_rules", [])[:3]:
        rows.append(f"Transit rule: {rule['name']} ({rule.get('severity', 'neutral')})")
    rahu = _find_window(day_payload["windows"]["inauspicious"], "Rahu Kalam")
    if rahu:
        rows.append(f"Rahu Kalam: {_window_time(rahu)}")
    return rows


def _reading(chart, relation: str, day_payload: dict, personal: dict, ctx: dict,
             verdict: dict, do_today: list[dict], avoid_today: list[dict]) -> dict:
    words = _subject_words(relation)
    subject = "you" if words["who"] == "you" else chart.name
    tone = verdict["tone"]
    rahu = _find_window(day_payload["windows"]["inauspicious"], "Rahu Kalam")
    rahu_time = _window_time(rahu)

    energy = {
        "supportive": "vibrant",
        "positive": "steady",
        "mixed": "fragmented",
        "caution": "drained",
    }[tone]
    focus = {
        "supportive": "The momentum is real. Tackle the thing you've been avoiding, then let the rest of the day coast.",
        "positive": "Keep it simple. You have the runway for steady progress and conversations that actually land.",
        "mixed": "Don't force a square peg into a round hole. Move forward, but drop the expectation of perfection.",
        "caution": "Downshift. This is a day for maintenance, rest, and ignoring manufactured urgency.",
    }[tone]
    summary = {
        "supportive": f"The stars are handing {subject} the wheel.",
        "positive": f"The sky clears, making way for steady movement for {subject}.",
        "mixed": f"The sky is conflicted, demanding a delicate touch from {subject}.",
        "caution": f"The sky is heavy. It's a day for {subject} to retreat and observe.",
    }[tone]
    timing_note = (
        f"Avoid starting anything crucial during {rahu_time}. Use that window to clean house instead."
        if rahu_time else "There are no major cosmic red lights. Move at your own pace."
    )

    return {
        "summary": summary,
        "focus": focus,
        "best_for": [row["text"] for row in do_today[:4]],
        "avoid": [row["text"] for row in avoid_today[:4]],
        "energy": energy,
        "relationship_tone": (
            "The air is clear. Speak your mind, but leave room for the other person to breathe."
            if tone in ("supportive", "positive", "mixed")
            else "Tension is high. Do not go digging for emotional closure today."
        ),
        "money_tone": (
            "A good day to map out your resources. You see the board clearly."
            if tone != "caution" else
            "Keep your wallet closed. Everything looks like a better idea than it actually is."
        ),
        "work_tone": (
            "Focus. You can actually get things done if you cut the noise."
            if tone in ("supportive", "positive") else
            "Lower your expectations. Plan, document, and survive the meeting."
        ),
        "timing_note": timing_note,
        "plain_why": _plain_why(day_payload, personal, ctx, words),
        "technical_why": _technical_why(day_payload, personal, ctx),
    }


def _do_and_avoid(day_payload: dict, personal: dict, ctx: dict,
                  words: dict) -> tuple[list[dict], list[dict]]:
    poss = words["poss"]
    do: list[dict] = []
    avoid: list[dict] = []

    tara = personal.get("tarabala", {})
    if tara.get("tara") in _FAVOURABLE_TARAS:
        do.append({"text": "Good for meaningful starts, follow-through and important conversations",
                   "source": "tarabala"})
    elif tara.get("tara") and tara.get("tara") != "Janma":
        avoid.append({"text": "Hold off on major new commitments unless they are necessary",
                      "source": "tarabala"})

    if personal.get("chandrabala", {}).get("chandrashtama"):
        avoid.append({"text": "Postpone big decisions and travel if you can",
                      "source": "chandrabala"})

    for rule in ctx["supportive_rules"]:
        do.append({"text": "Plan, learn, seek guidance or ask for help from the right person",
                   "source": "gochara"})
    for rule in ctx["challenging_rules"]:
        avoid.append({"text": "Avoid rushed, risky or ego-driven moves",
                      "source": "gochara"})

    abhijit = _find_window(day_payload["windows"]["auspicious"], "Abhijit")
    if abhijit:
        do.append({"text": f"Use {_window_time(abhijit)} for your most important start or decision",
                   "source": "muhurta", "window": _window_time(abhijit)})
    rahu = _find_window(day_payload["windows"]["inauspicious"], "Rahu Kalam")
    if rahu:
        avoid.append({"text": f"Keep {_window_time(rahu)} for routine work, not fresh starts",
                      "source": "muhurta", "window": _window_time(rahu)})

    for alert in personal.get("ghatak_alerts", []):
        if alert.get("matched"):
            avoid.append({"text": "Treat the day as sensitive; avoid unnecessary risk or confrontation",
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
    reading = _reading(chart, relation or "", day_payload, personal, ctx,
                       verdict, do_today, avoid_today)

    return {
        "system": "AstroSpace Daily Guidance",
        "as_of": as_of.isoformat(),
        "date": day_payload["date"],
        "subject": chart.name,
        "relation": relation,
        "vara": day_payload["vara"]["name"],
        "verdict": verdict,
        "reading": reading,
        "color": _day_color(vara_lord, supportive_planet, challenging_planet),
        "number": _day_number(as_of, vara_lord, favourable),
        "tarabala": personal["tarabala"],
        "chandrabala": personal["chandrabala"],
        "star_of_day": {
            "nakshatra": day_payload["elements"]["nakshatra"][0]["name"],
            "moon_rashi": day_payload["moon_rashi_at_sunrise"],
            "tithi": day_payload["elements"]["tithi"][0]["name"],
        },
        # Practitioner-surface detail: the panchanga engine already computes
        # yoga and karana alongside tithi/nakshatra (panchanga.py), they just
        # were not projected into a response field before.
        "panchanga_details": {
            "tithi": day_payload["elements"]["tithi"][0]["name"],
            "nakshatra": day_payload["elements"]["nakshatra"][0]["name"],
            "yoga": day_payload["elements"]["yoga"][0]["name"],
            "karana": day_payload["elements"]["karana"][0]["name"],
            "vara": day_payload["vara"]["name"],
        },
        # The four horary windows kala.py already computes for the day
        # (Rahu Kalam, Yamaganda, Gulika, Abhijit), surfaced as one list
        # instead of requiring a caller to know which sub-window to look up.
        "muhurta_windows": [
            {"name": w["name"], "time": _window_time(w), "kind": kind}
            for kind, names in (
                ("inauspicious", ("Rahu Kalam", "Yamaganda", "Gulika Kalam")),
                ("auspicious", ("Abhijit Muhurta",)),
            )
            for name in names
            for w in [_find_window(day_payload["windows"][kind], name)]
            if w
        ],
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
                {
                    "name": r["name"],
                    "planet": r["planet"],
                    "severity": r.get("severity"),
                    "av_bindus": (r.get("av_context") or {}).get("bindus"),
                }
                for r in ctx["gochara"].get("active_rules", [])
            ],
        },
        "provenance": {
            "engine": "computed from panchanga + gochara via the Context Engine",
            "place": {"city": place_city, "nation": place_nation, "timezone": tz},
            "note": "Every line is rule-derived; expand any card to see its source signal.",
        },
    }
