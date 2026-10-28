"""Checks every birth-chart placement an answer states against the chart.

"Rahu touches your 5th house" for a chart with Rahu in the 12th (Lilliput
re-run, 2026-10-28) is a fabricated fact, not a worse reading. Each sentence
that puts a planet in a house of the BIRTH chart is read here and compared
with `birth_placements`, the planet -> house map the orchestrator adds to
every bundle. Sentences about another frame (a divisional chart, the view
from the Moon or Sun, the Karakamsha, transits) are skipped: their houses
are counted differently and are checked nowhere else either.
"""
from __future__ import annotations

import re

PLANETS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")
_PLANET = r"\b(" + "|".join(PLANETS) + r")\b"

_ORDINAL_WORDS = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6,
    "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10, "eleventh": 11, "twelfth": 12,
}
_ORDINAL = r"(\d{1,2})(?:st|nd|rd|th)|(" + "|".join(_ORDINAL_WORDS) + r")"

# Another frame than the birth chart's houses counted from the Lagna.
_OTHER_FRAME = re.compile(
    r"\bD\d{1,2}\b|dashamsha|dasamsa|navamsha|navamsa|divisional|varga|karakamsh|"
    r"\bfrom (?:the |your )?(?:moon|sun|lagna lord|arudha)|chandra lagna|surya lagna|"
    r"\btransit|\bgochara|\bmoving (?:through|into)|\bpassing (?:through|over)|\bcurrently in\b|"
    r"\bnow in\b|\bthis year\b|\bwill (?:enter|move)|\bentering\b|\bfrom it\b",
    re.IGNORECASE)

# "<planets> ... sits in / is in / touches / placed in ... <N>th house"
_IN_HOUSE = re.compile(
    r"\b(?:sits?|sitting|is|are|placed|located|lies|lie|occupies|occupy|touch(?:es)?|"
    r"joins?|stays?|resides?|positioned)\b"
    r"(?:\s+\w+){0,2}?\s+(?:in|into|on)?\s*(?:your|the|her|his|their)?\s*(?:own\s+)?"
    r"(?:" + _ORDINAL + r")\s+house\b",
    re.IGNORECASE)
# "Venus in your 5th house", with no verb.
_BARE_IN_HOUSE = re.compile(
    _PLANET + r"\s+(?:\(\w+\)\s+)?in\s+(?:(?:your|the|her|his|their)\s+)?(?:" + _ORDINAL + r")\s+"
    r"(?:house\b|(?=(?:Aries|Taurus|Gemini|Cancer|Leo|Virgo|Libra|Scorpio|Sagittarius|Capricorn|"
    r"Aquarius|Pisces)\b))",
    re.IGNORECASE)
# "your 5th house holds / has / hosts Venus, Mercury and the Sun"
_HOUSE_HOLDS = re.compile(
    r"(?:" + _ORDINAL + r")\s+house\b[^.;:]{0,40}?\b(?:holds|has|hosts|contains|houses)\b",
    re.IGNORECASE)

_CLAUSE_START = re.compile(r"[;:—]|\b(?:but|while|whereas|although|though|however|which|where)\b",
                           re.IGNORECASE)
_NEGATION = re.compile(r"\b(?:not|no|never|neither|nor)\b", re.IGNORECASE)
# "Venus is lord of your 1st house" names lordship, not a placement.
_NOT_PLACEMENT = re.compile(r"\b(?:lord|lords|ruler|rules|ruling|owner|owns|aspect|aspects|"
                            r"aspecting|looks? at|karaka)\b", re.IGNORECASE)
# "... in the 6th house with Ketu and Saturn"
_WITH = re.compile(r"^\s*,?\s*(?:together |along )?(?:with|alongside|beside|next to)\b",
                   re.IGNORECASE)


def _house(match: re.Match, digits_group: int, word_group: int) -> int | None:
    if match.group(digits_group):
        value = int(match.group(digits_group))
    else:
        value = _ORDINAL_WORDS.get((match.group(word_group) or "").lower(), 0)
    return value if 1 <= value <= 12 else None


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+|\n+", text or "") if s.strip()]


def _planets_in(span: str) -> list[str]:
    found = []
    for match in re.finditer(_PLANET, span, re.IGNORECASE):
        # "the 2nd lord Mars" names Mars; "lord of Mars" does not occur, so
        # every planet name in the subject span is a subject.
        found.append(match.group(1).capitalize())
    return found


def stated_placements(text: str) -> list[tuple[str, int, str]]:
    """(planet, house, sentence) for each birth-chart placement the text
    asserts. Sentences in another frame are left out."""
    claims: list[tuple[str, int, str]] = []
    for sentence in _sentences(text):
        if _OTHER_FRAME.search(sentence):
            continue
        previous_end = 0
        for match in _IN_HOUSE.finditer(sentence):
            house = _house(match, 1, 2)
            # "Jupiter is in the 4th house and Rahu is in the 12th": the
            # second claim's subject starts after the first claim.
            head = sentence[previous_end:match.start()]
            previous_end = match.end()
            boundaries = list(_CLAUSE_START.finditer(head))
            subject = head[boundaries[-1].end():] if boundaries else head
            matched = sentence[match.start():match.end()]
            if house is None or _NEGATION.search(matched) or _NOT_PLACEMENT.search(matched):
                continue
            tail = sentence[match.end():]
            companions = []
            if _WITH.match(tail):
                stop = re.search(r"[;:—,]|\b(?:but|while|which|where|so|showing|giving|making|"
                                 r"is|are|sits?|gives?|shows?)\b", tail[_WITH.match(tail).end():])
                rest = tail[_WITH.match(tail).end():]
                companions = _planets_in(rest[:stop.start()] if stop else rest)
            for planet in [*_planets_in(subject), *companions]:
                claims.append((planet, house, sentence.strip()))
        for match in _BARE_IN_HOUSE.finditer(sentence):
            house = _house(match, 2, 3)
            if house is not None:
                claims.append((match.group(1).capitalize(), house, sentence.strip()))
        for match in _HOUSE_HOLDS.finditer(sentence):
            house = _house(match, 1, 2)
            if house is None:
                continue
            tail = sentence[match.end():]
            stop = _CLAUSE_START.search(tail)
            for planet in _planets_in(tail[:stop.start()] if stop else tail):
                claims.append((planet, house, sentence.strip()))
    # One claim per planet and house per sentence.
    return list(dict.fromkeys(claims))


def wrong_placements(text: str, placements: dict) -> list[tuple[str, int, int, str]]:
    """(planet, stated house, real house, sentence) for every stated
    birth-chart placement that does not match the chart."""
    wrong = []
    for planet, house, sentence in stated_placements(text):
        actual = (placements.get(planet) or {}).get("house")
        if actual and int(actual) != house:
            wrong.append((planet, house, int(actual), sentence))
    return wrong


def birth_placements(chart) -> dict:
    """{planet: {"house", "sign"}} in the birth chart, houses counted whole
    sign from the Lagna (the same numbers chart_overview reports)."""
    details = chart.planet_details() or {}
    return {planet: {"house": row.get("house"), "sign": row.get("sign")}
            for planet in PLANETS if (row := details.get(planet))}


SIGNS = ("Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
         "Sagittarius", "Capricorn", "Aquarius", "Pisces")
_SIGN = r"\b(" + "|".join(SIGNS) + r")\b"
# "Gemini (3rd house)", "the 3rd house (Gemini)", "12th Virgo", "4th house, Capricorn"
_SIGN_HOUSE = [
    (re.compile(_SIGN + r"\s*\(\s*(?:the\s+|your\s+)?(?:" + _ORDINAL + r")(?:\s+house)?\b", re.IGNORECASE),
     1, 2, 3),
    (re.compile(r"(?:" + _ORDINAL + r")(?:\s+house)?\s*[(,]?\s*(?:in\s+)?" + _SIGN, re.IGNORECASE),
     3, 1, 2),
]


def lagna_sign(placements: dict) -> int | None:
    """The Lagna's sign index, read back from any planet's sign and house."""
    for row in placements.values():
        sign, house = (row or {}).get("sign"), (row or {}).get("house")
        if sign in SIGNS and house:
            return (SIGNS.index(sign) - (int(house) - 1)) % 12
    return None


def wrong_sign_houses(text: str, placements: dict) -> list[tuple[str, int, int, str]]:
    """(sign, stated house, real house, sentence) where the text pairs a sign
    with a birth-chart house number that does not match the Lagna."""
    base = lagna_sign(placements)
    if base is None:
        return []
    wrong = []
    for sentence in _sentences(text):
        if _OTHER_FRAME.search(sentence):
            continue
        for pattern, sign_group, digits_group, word_group in _SIGN_HOUSE:
            for match in pattern.finditer(sentence):
                house = _house(match, digits_group, word_group)
                sign = match.group(sign_group).capitalize()
                if house is None:
                    continue
                actual = (SIGNS.index(sign) - base) % 12 + 1
                if actual != house:
                    wrong.append((sign, house, actual, sentence.strip()))
    return list(dict.fromkeys(wrong))


def drop_false_sentences(text: str, placements: dict) -> str:
    """The text without any sentence that misplaces a planet or pairs a sign
    with the wrong house. For model text that cannot be sent back for repair
    (the angle reasons on the "How we weighed it" card)."""
    if not placements:
        return text
    kept = [s for s in _sentences(text)
            if not wrong_placements(s, placements) and not wrong_sign_houses(s, placements)]
    return " ".join(kept)
