"""
Favourable points — lucky numbers, days, planets, gem, metal, direction, colour.

Derivations:
- Lucky/root number: digital root of the birth day-of-month; good/evil
  numbers from the numerology table (VERIFY — convention-dependent). This is
  the numerology *moolank* — distinct from the chart-derived number below.
- Astrological lucky number: the lagna lord's ruling number, cross-checked
  against the rashi lord, nakshatra lord and Jaimini Atmakaraka. See
  astrological_lucky_number(). Only included when the caller supplies the
  moon sign / nakshatra lord / Atmakaraka (chart.favourable() always does).
- Good years: calendar ages whose digital root equals the root number.
- Good/evil planets: functional benefics/malefics for the lagna
  (Parashari house-lordship principles, VERIFY).
- Lucky days: weekdays of the good planets.
- Gem/metal/direction/time/colour: associations of the lagna lord.
- Functional colours (functional_planets()): every colour family sorted into
  suits / avoid / neutral by the lagna's functional benefics and malefics.
  This is what Ask grounds colour, gem and day advice in.
"""
import re

from .constants import (
    NUMEROLOGY, FUNCTIONAL_BY_LAGNA, PLANET_COLORS, PLANET_COLOUR_FAMILIES,
    PLANET_DAYS, PLANET_GEMS, PLANET_METALS, PLANET_DIRECTIONS, PLANET_NUMBER,
    SIGN_LORDS, OWN_SIGNS,
)
from .positions import sign_name


def digital_root(n: int) -> int:
    while n > 9:
        n = sum(int(c) for c in str(n))
    return n


def favourable_points(birth_day: int, lagna_sign: int, *,
                      moon_sign: int | None = None,
                      nakshatra_lord: str | None = None,
                      atmakaraka: str | None = None) -> dict:
    root = digital_root(birth_day)
    num = NUMEROLOGY[root]
    functional = FUNCTIONAL_BY_LAGNA[lagna_sign % 12]
    good_planets = functional["benefics"]
    evil_planets = functional["malefics"]
    lagna_lord = SIGN_LORDS[lagna_sign % 12]

    good_years = [y for y in range(1, 100) if digital_root(y) == root][:8]
    lucky_days = [PLANET_DAYS[p] for p in good_planets if p in PLANET_DAYS]
    friendly_signs = sorted({
        sign_name(s) for p in good_planets for s in OWN_SIGNS.get(p, [])
    })
    color_name, color_hex = PLANET_COLORS[lagna_lord]

    result = {
        "lucky_number": root,
        "ruling_planet": num["planet"],
        "good_numbers": num["good"],
        "evil_numbers": num["evil"],
        "good_years": good_years,
        "lucky_days": lucky_days,
        "good_planets": good_planets,
        "evil_planets": evil_planets,
        "yogakaraka": functional["yogakaraka"],
        "friendly_signs": friendly_signs,
        "lucky_metal": PLANET_METALS[lagna_lord],
        "lucky_stone": PLANET_GEMS[lagna_lord],
        "lucky_direction": PLANET_DIRECTIONS[lagna_lord],
        "lucky_time": f"Hora of {lagna_lord}" + (" (sunrise)" if lagna_lord == "Sun" else ""),
        "lucky_color": {
            "name": color_name, "hex": color_hex, "planet": lagna_lord,
            "source": f"colour of {lagna_lord}, the Lagna lord",
        },
    }
    if moon_sign is not None and nakshatra_lord and atmakaraka:
        result["astrological_number"] = astrological_lucky_number(
            lagna_sign, moon_sign, nakshatra_lord, atmakaraka,
        )
    return result


def astrological_lucky_number(lagna_sign: int, moon_sign: int,
                              nakshatra_lord: str, atmakaraka: str) -> dict:
    """Chart-derived lucky number — distinct from the numerology moolank.

    This is the OTHER convention for a "lucky number": instead of reducing
    the birth date, several jyotisha traditions assign the number of the
    planet that rules a key chart point. The lagna lord (ascendant ruler) is
    the most commonly cited primary source, since it governs the native's
    overall identity and fortune; the rashi (Moon-sign) lord, the birth
    nakshatra's lord, and the Jaimini Atmakaraka (soul planet) are checked as
    supporting witnesses. When one or more agree with the lagna lord, the
    number is reported as more strongly confirmed by the chart.
    """
    lagna_lord = SIGN_LORDS[lagna_sign % 12]
    rashi_lord = SIGN_LORDS[moon_sign % 12]
    witnesses = [
        {"label": "Lagna lord", "planet": lagna_lord},
        {"label": "Rashi (Moon) lord", "planet": rashi_lord},
        {"label": "Nakshatra lord", "planet": nakshatra_lord},
        {"label": "Atmakaraka", "planet": atmakaraka},
    ]
    for w in witnesses:
        w["number"] = PLANET_NUMBER.get(w["planet"])

    primary_number = PLANET_NUMBER[lagna_lord]
    confirmed_by = [
        w["label"] for w in witnesses[1:] if w["number"] == primary_number
    ]
    return {
        "number": primary_number,
        "planet": lagna_lord,
        "source": "Lagna lord (ascendant ruler) — the chart's primary identity indicator",
        "witnesses": witnesses,
        "confirmed_by": confirmed_by,
        "confirmation_count": len(confirmed_by),
    }


_GRAHAS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")


def functional_planets(lagna_sign: int) -> dict:
    """Which grahas help and which work against this lagna, and the colours
    that follow from that — one fixed answer per chart.

    Before this, Ask had no colour rule at all and improvised one per turn
    from whatever placement suited the moment: the same "Jupiter in Leo"
    argued for white in one answer and for red two turns later, once the
    reader said the family liked red (2026-10-26, a Virgo-lagna tester).
    Computing it here makes the answer the chart's, not the conversation's.

    Rule: a colour SUITS when a helpful graha (functional benefic, the lagna
    lord, the yogakaraka) owns it; otherwise it is one to AVOID when a
    functional malefic owns it; anything else is NEUTRAL. A colour shared by
    a helpful and a difficult graha (white: Venus and the Moon) suits, since
    the helpful owner is enough to make it usable. An avoid colour is `firm`
    when its graha rules the 6th, 8th or 12th from the lagna (Mars for Virgo,
    lord of the 8th), and `mild` otherwise (the Moon for Virgo, lord of the
    11th): the second is less helpful, not harmful.
    """
    functional = FUNCTIONAL_BY_LAGNA[lagna_sign % 12]
    lagna_lord = SIGN_LORDS[lagna_sign % 12]
    helpful = list(dict.fromkeys(
        [lagna_lord, *functional["benefics"],
         *([functional["yogakaraka"]] if functional["yogakaraka"] else [])]
    ))
    difficult = [p for p in functional["malefics"] if p not in helpful]
    neutral = [p for p in _GRAHAS if p not in helpful and p not in difficult]
    houses_ruled = {
        planet: [h for h in range(1, 13) if SIGN_LORDS[(lagna_sign + h - 1) % 12] == planet]
        for planet in difficult
    }

    owners: dict[str, list[str]] = {}
    for planet in _GRAHAS:
        for colour in PLANET_COLOUR_FAMILIES[planet]:
            owners.setdefault(colour, []).append(planet)

    colours = {"suit": [], "avoid": [], "neutral": []}
    for colour, planets in owners.items():
        good = [p for p in planets if p in helpful]
        bad = [p for p in planets if p in difficult]
        if good:
            colours["suit"].append({"colour": colour, "planet": good[0]})
        elif bad:
            firm = any(h in (6, 8, 12) for h in houses_ruled[bad[0]])
            colours["avoid"].append({"colour": colour, "planet": bad[0],
                                     "firmness": "firm" if firm else "mild"})
        else:
            colours["neutral"].append({"colour": colour, "planet": planets[0]})

    return {
        "ascendant": sign_name(lagna_sign % 12),
        "ascendant_lord": lagna_lord,
        "helpful_planets": helpful,
        "difficult_planets": difficult,
        "houses_ruled_by_difficult": houses_ruled,
        "neutral_planets": neutral,
        "yogakaraka": functional["yogakaraka"],
        "colours": colours,
        "lucky_days": [PLANET_DAYS[p] for p in helpful if p in PLANET_DAYS],
        "lucky_stone": PLANET_GEMS[lagna_lord],
        "rule": ("Helpful and difficult planets are the functional benefics and "
                 "malefics for this ascendant (Parashari house lordship). A colour "
                 "suits when a helpful planet rules it, is one to avoid when only a "
                 "difficult planet rules it, and is neutral otherwise. An avoid "
                 "colour is firm when its planet rules the 6th, 8th or 12th house, "
                 "and mild (less helpful, not harmful) otherwise."),
        "is_convention_dependent": True,
        "observance_note": ("Astrologers weigh functional planets a little "
                            "differently, especially a planet that rules one good "
                            "and one hard house; this follows the standard "
                            "Parashari list for the ascendant."),
    }


# Shade words a reader types (often a maker's paint name) -> the colour family
# in PLANET_COLOUR_FAMILIES it belongs to. Longer phrases first, so "black
# pearl" is a black car and "pearl white" a white one, not the Moon's pearl.
_SHADE_WORDS: tuple[tuple[str, str], ...] = (
    ("black pearl", "black"), ("pearl black", "black"), ("pearl white", "white"),
    ("snow white", "white"), ("off-white", "cream"), ("off white", "cream"),
    ("light blue", "pastel shades"), ("sky blue", "pastel shades"), ("baby pink", "pastel shades"),
    ("olive", "olive green"), ("emerald", "emerald"), ("green", "green"), ("teal", "green"),
    ("maroon", "maroon"), ("burgundy", "maroon"), ("wine", "maroon"),
    ("crimson", "red"), ("ruby", "red"), ("red", "red"), ("coral", "coral"),
    ("saffron", "saffron"), ("orange", "orange"), ("copper", "copper"), ("bronze", "brown"),
    ("golden", "gold"), ("gold", "gold"), ("mustard", "yellow"), ("yellow", "yellow"),
    ("navy", "navy"), ("blue", "dark blue"), ("black", "black"),
    ("graphite", "dark grey"), ("charcoal", "dark grey"), ("grey", "dark grey"),
    ("gray", "dark grey"), ("silver", "silver"), ("pearl", "pearl"),
    ("ivory", "cream"), ("beige", "cream"), ("cream", "cream"), ("white", "white"),
    ("pink", "pastel shades"), ("pastel", "pastel shades"), ("brown", "brown"),
)
_SHADE_ORDER = sorted((w for w, _ in _SHADE_WORDS), key=len, reverse=True)
_SHADE_RE = re.compile(r"\b(" + "|".join(re.escape(w) for w in _SHADE_ORDER) + r")\b", re.I)
# A maker's paint name: "Magma Red", "Pewter Olive" — a capitalised word then
# a capitalised shade word. Case-sensitive on purpose: "Is gold good?" is not one.
_PAINT_NAME = re.compile(
    r"\b[A-Z][a-z]+ (?:" + "|".join(re.escape(w.title()) for w in _SHADE_ORDER) + r")\b")
_COLOUR_TALK = re.compile(r"\b(colou?rs?|shades?|paint|wear|dress|saree|car|bike|scooter|"
                          r"wall|room)\b", re.I)
_LEAD_WORD = re.compile(r"([A-Z][a-z]+) $")
# Capitalised only because they start a sentence: never part of a paint name.
_NOT_PAINT_WORDS = {"is", "are", "a", "an", "the", "and", "or", "but", "what", "which",
                    "how", "about", "our", "my", "we", "i", "should", "will", "would",
                    "can", "does", "do", "like", "also", "then", "so", "only", "go", "with"}


def shade_verdicts(text: str, lagna_sign: int) -> list[dict]:
    """The shades a reader named, each sorted by functional_planets().

    Ask used to judge "Magma Red" or "Pewter Olive" from scratch on every turn;
    this sorts each named shade once, in code, so a follow-up cannot re-argue
    it. Empty unless `text` is about colour or names a paint ("Magma Red"), so
    "gold" in a wealth question is not read as a shade."""
    if not text or not (_COLOUR_TALK.search(text) or _PAINT_NAME.search(text)):
        return []
    families = dict(_SHADE_WORDS)
    shade_words = set(families)
    verdict_of = {}
    for verdict, rows in functional_planets(lagna_sign)["colours"].items():
        for row in rows:
            verdict_of[row["colour"]] = {**row, "verdict": verdict}
    found, seen = [], set()
    for match in _SHADE_RE.finditer(text):
        word = match.group(1)
        family = families[word.lower()]
        # Up to two capitalised words before it make the paint name
        # ("Aurora Black Pearl"), never another shade word.
        name, start = word, match.start()
        for _ in range(2):
            lead = _LEAD_WORD.search(text[:start])
            if not lead or lead.group(1).lower() in shade_words | _NOT_PAINT_WORDS:
                break
            name, start = f"{lead.group(1)} {name}", lead.start()
        if name.lower() in seen:
            continue
        seen.add(name.lower())
        row = verdict_of[family]
        found.append({"named": name, "family": family, "planet": row["planet"],
                      "verdict": row["verdict"],
                      **({"firmness": row["firmness"]} if "firmness" in row else {})})
    return found
