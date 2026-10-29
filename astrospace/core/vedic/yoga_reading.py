"""Plain-words evidence for yogas and doshas: why this chart has one.

Each computed yoga or dosha gets a `why` list — short sentences naming the
exact placements that form it, written for a reader rather than an
astrologer ("Jupiter in Gemini is 10th from your Moon in Virgo"). The
engine's own `triggers` stay as they are for Practitioner and for Ask.

Also adds `weakened`: plain notes on what classically dims a yoga that is
present (a debilitated or combust participant), so a reader is never told a
weak yoga is strong. Nothing here changes whether a rule is active.
"""
from __future__ import annotations

from .constants import EXALTATION, SIGN_LORDS
from .positions import house_from_lagna, sign_index, sign_name

KENDRA = {1, 4, 7, 10}
SPECIAL_ASPECTS = {"Mars": {4, 8}, "Jupiter": {5, 9}, "Saturn": {3, 10}}
CLASSICAL = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
QUALITY = {0: "moving", 1: "fixed", 2: "dual"}
# Combustion orbs (degrees from the Sun) in the common Surya Siddhanta table.
COMBUST_ORB = {"Moon": 12, "Mars": 17, "Mercury": 14, "Jupiter": 11, "Venus": 10, "Saturn": 15}


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}" + {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def _and(items: list[str]) -> str:
    items = list(items)
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


class _Chart:
    def __init__(self, positions: dict, lagna_lon: float):
        self.lons = {p: data["lon"] for p, data in positions.items()}
        self.signs = {p: sign_index(lon) for p, lon in self.lons.items()}
        self.lagna = sign_index(lagna_lon)

    def sign(self, planet: str) -> str:
        return sign_name(self.signs[planet])

    def house(self, planet: str) -> int:
        return house_from_lagna(self.signs[planet], self.lagna)

    def at(self, planet: str) -> str:
        """'Jupiter in Gemini (your 4th house)'."""
        return f"{planet} in {self.sign(planet)} (your {ordinal(self.house(planet))} house)"

    def ruled(self, planet: str) -> list[int]:
        return [h for h in range(1, 13) if SIGN_LORDS[(self.lagna + h - 1) % 12] == planet]

    def from_moon(self, planet: str) -> int:
        return house_from_lagna(self.signs[planet], self.signs["Moon"])

    def dignity(self, planet: str) -> str | None:
        if planet not in EXALTATION:
            return None
        sign = self.signs[planet]
        if sign == EXALTATION[planet][0]:
            return "exalted"
        if sign == (EXALTATION[planet][0] + 6) % 12:
            return "debilitated"
        if SIGN_LORDS[sign] == planet:
            return "own"
        return None

    def combust(self, planet: str) -> bool:
        if planet not in COMBUST_ORB or "Sun" not in self.lons:
            return False
        gap = abs((self.lons[planet] - self.lons["Sun"] + 180) % 360 - 180)
        return gap < COMBUST_ORB[planet]

    def aspects(self, planet: str, target: str) -> bool:
        house = house_from_lagna(self.signs[target], self.signs[planet])
        return house == 7 or house in SPECIAL_ASPECTS.get(planet, set())


def _houses_text(houses: list[int]) -> str:
    return _and([ordinal(h) for h in houses]) + (" houses" if len(houses) > 1 else " house")


def _link(c: _Chart, a: str, b: str) -> str:
    if c.signs[a] == c.signs[b]:
        return f"{a} and {b} sit together in {c.sign(a)}"
    if SIGN_LORDS[c.signs[a]] == b and SIGN_LORDS[c.signs[b]] == a:
        return f"{a} and {b} sit in each other's signs ({c.sign(a)} and {c.sign(b)}), an exchange"
    a_b, b_a = c.aspects(a, b), c.aspects(b, a)
    if a_b and b_a:
        if house_from_lagna(c.signs[b], c.signs[a]) == 7:
            return f"{a} in {c.sign(a)} and {b} in {c.sign(b)} face each other across the chart"
        return f"{a} in {c.sign(a)} and {b} in {c.sign(b)} look at each other"
    looker, seen = (a, b) if a_b else (b, a)
    return f"{looker} in {c.sign(looker)} looks at {seen} in {c.sign(seen)}, a one-way link"


def _occupant_line(c: _Chart, planets: list[str], anchor: str, side: str) -> str:
    sign = c.sign(planets[0])
    anchor_sign = c.sign(anchor) if anchor in c.signs else ""
    return f"{_and(planets)} in {sign}, the sign just {side} your {anchor} in {anchor_sign}."


def _flank(c: _Chart, anchor_sign: int, planets: list[str], offset: int) -> list[str]:
    target = (anchor_sign + offset) % 12
    return [p for p in planets if c.signs.get(p) == target]


def _yoga_why(y: dict, c: _Chart) -> list[str]:
    rid = y["rule_id"]
    planets = [p for p in y.get("planets", []) if p in c.signs]
    if rid in {"ruchaka_yoga", "bhadra_yoga", "hamsa_yoga", "malavya_yoga", "sasa_yoga"}:
        p = planets[0]
        kind = "its exalted sign" if c.dignity(p) == "exalted" else "its own sign"
        anchors = []
        if c.house(p) in KENDRA:
            anchors.append(f"your {ordinal(c.house(p))} house from the rising sign")
        if c.from_moon(p) in KENDRA:
            anchors.append(f"the {ordinal(c.from_moon(p))} place from your Moon")
        return [f"{p} is in {c.sign(p)}, {kind}.",
                f"It sits in {_and(anchors)}, one of the four pillar places (1st, 4th, 7th, 10th)."]
    if rid == "gaja_kesari_yoga":
        return [f"Jupiter in {c.sign('Jupiter')} is {ordinal(c.from_moon('Jupiter'))} from your Moon in {c.sign('Moon')}."]
    if rid == "chandra_mangal_yoga":
        if c.signs["Moon"] == c.signs["Mars"]:
            return [f"Your Moon and Mars sit together in {c.sign('Moon')}."]
        return [f"Mars in {c.sign('Mars')} faces your Moon in {c.sign('Moon')}, seven signs away."]
    if rid == "budhaditya_yoga":
        return [f"Sun and Mercury sit together in {c.sign('Sun')}, your {ordinal(c.house('Sun'))} house."]
    if rid in {"sunapha_yoga", "anapha_yoga", "durudhara_yoga"}:
        moon = c.signs["Moon"]
        lines = []
        support = ["Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
        after, before = _flank(c, moon, support, 1), _flank(c, moon, support, -1)
        if after and rid in {"sunapha_yoga", "durudhara_yoga"}:
            lines.append(_occupant_line(c, after, "Moon", "after"))
        if before and rid in {"anapha_yoga", "durudhara_yoga"}:
            lines.append(_occupant_line(c, before, "Moon", "before"))
        return lines
    if rid.endswith(("vesi_yoga", "vosi_yoga", "ubhayachari_yoga")):
        sun = c.signs["Sun"]
        pool = ["Mars", "Saturn"] if rid.startswith("asubha_") else ["Mercury", "Jupiter", "Venus"]
        after, before = _flank(c, sun, pool, 1), _flank(c, sun, pool, -1)
        lines = []
        if after and ("vesi" in rid or "ubhayachari" in rid):
            lines.append(_occupant_line(c, after, "Sun", "after"))
        if before and ("vosi" in rid or "ubhayachari" in rid):
            lines.append(_occupant_line(c, before, "Sun", "before"))
        return lines
    if rid == "adhi_yoga":
        return [f"{p} in {c.sign(p)} is {ordinal(c.from_moon(p))} from your Moon in {c.sign('Moon')}."
                for p in planets if p != "Moon"]
    if rid == "kemadruma_yoga":
        lines = [f"Your Moon is in {c.sign('Moon')}. No planet sits with it, in the sign before or after it, "
                 "or in the 4th, 7th or 10th place from it."]
        return lines
    if rid == "amala_yoga":
        lines = []
        for anchor, base, label in (("Lagna", c.lagna, "rising sign"), ("Moon", c.signs["Moon"], "Moon")):
            tenth = (base + 9) % 12
            found = [p for p in planets if c.signs[p] == tenth]
            if found:
                lines.append(f"{_and(found)} in {sign_name(tenth)} is 10th from your {label} in {sign_name(base)}.")
        return lines
    if rid == "saraswati_yoga":
        return [f"{_and([c.at(p) for p in ['Jupiter', 'Venus', 'Mercury']])} all sit in good houses.",
                f"Jupiter in {c.sign('Jupiter')} is in a sign where it is comfortable."]
    if rid in {"shubha_kartari_yoga", "papa_kartari_yoga"}:
        anchor = "Moon" if "Moon" in y.get("name", "") else "Lagna"
        base = c.signs["Moon"] if anchor == "Moon" else c.lagna
        label = "Moon" if anchor == "Moon" else "rising sign"
        before = [p for p in planets if c.signs[p] == (base - 1) % 12]
        after = [p for p in planets if c.signs[p] == (base + 1) % 12]
        return [f"{_and(before)} in {sign_name((base - 1) % 12)} and {_and(after)} in {sign_name((base + 1) % 12)} "
                f"sit on both sides of your {label} in {sign_name(base)}."]
    if rid == "shakata_yoga":
        return [f"Your Moon in {c.sign('Moon')} is {ordinal(house_from_lagna(c.signs['Moon'], c.signs['Jupiter']))} "
                f"from Jupiter in {c.sign('Jupiter')}."]
    if rid == "guru_chandala_yoga":
        node = next((p for p in planets if p in ("Rahu", "Ketu")), "Rahu")
        return [f"Jupiter and {node} sit together in {c.sign('Jupiter')}, your {ordinal(c.house('Jupiter'))} house."]
    if rid == "neecha_bhanga_raja_yoga":
        fallen = planets[0]
        return [f"{fallen} is in {c.sign(fallen)}, its weakest sign.",
                *[_plain_trigger(t) for t in y.get("triggers", [])]]
    if rid in {"raja_yoga", "dhana_yoga"} and len(planets) == 2:
        a, b = planets
        return [f"{a} rules your {_houses_text(c.ruled(a))} and {b} rules your {_houses_text(c.ruled(b))}.",
                f"{_link(c, a, b)}."]
    if rid == "viparita_raja_yoga":
        p = planets[0]
        hard = [h for h in c.ruled(p) if h in (6, 8, 12)]
        return [f"{p} rules your {_houses_text(hard)} and sits in your {ordinal(c.house(p))} house. "
                "All of these are the hard houses (6th, 8th, 12th)."]
    if rid == "kalasarpa_flag":
        return [f"Rahu is in {c.sign('Rahu')} and Ketu in {c.sign('Ketu')}. All seven planets sit on one side between them."]
    if rid in {"rajju_yoga", "musala_yoga", "nala_yoga"}:
        quality = QUALITY[c.signs["Sun"] % 3]
        return [f"All seven planets are in {quality} signs: "
                + _and([f"{p} in {c.sign(p)}" for p in CLASSICAL]) + "."]
    if rid in {"mala_yoga", "sarpa_yoga"}:
        return [f"{_and([c.at(p) for p in planets])}: each sits in a pillar house (1st, 4th, 7th, 10th)."]
    if rid in {"gola_yoga", "yuga_yoga", "shoola_yoga", "kedara_yoga", "pasa_yoga", "dama_yoga", "veena_yoga"}:
        groups: dict[int, list[str]] = {}
        for p in CLASSICAL:
            groups.setdefault(c.signs[p], []).append(p)
        return [f"Your seven planets sit in {len(groups)} signs: "
                + "; ".join(f"{sign_name(s)} ({_and(ps)})" for s, ps in groups.items()) + "."]
    return [f"{_and([c.at(p) for p in planets])}."] if planets else []


_PLAIN = (
    ("lord of debilitation sign", "the lord of that sign"),
    ("lord of ", "the lord of "),
    ("is kendra from Lagna and Moon", "sits in a pillar house from both your rising sign and your Moon"),
    ("is kendra from Lagna", "sits in a pillar house (1st, 4th, 7th, 10th) from your rising sign"),
    ("is kendra from Moon", "sits in a pillar house (1st, 4th, 7th, 10th) from your Moon"),
    ("(debilitation and exaltation lords) are in mutual kendras",
     "(the lords of its weak and strong signs) sit in pillar places from each other"),
    ("aspects", "looks at"),
)


def _plain_trigger(trigger: str) -> str:
    text = trigger
    for old, new in _PLAIN:
        text = text.replace(old, new)
    text = text.replace("the the", "the")
    return text[0].upper() + text[1:] + ("" if text.endswith(".") else ".") + (
        "" if "repair" in text else " That repairs the weakness.")


def _weakened(y: dict, c: _Chart) -> list[str]:
    rid = y["rule_id"]
    out = []
    if rid == "gaja_kesari_yoga":
        if c.dignity("Jupiter") == "debilitated":
            out.append("Jupiter is in Capricorn, its weakest sign, so this yoga gives less.")
        if c.combust("Jupiter"):
            out.append("Jupiter is very close to the Sun (combust), so this yoga gives less.")
        if c.dignity("Moon") == "debilitated":
            out.append("Your Moon is in Scorpio, its weakest sign, so this yoga gives less.")
    if rid == "budhaditya_yoga" and c.combust("Mercury"):
        out.append("Mercury is within 14 degrees of the Sun (combust). Many astrologers read the yoga as milder then.")
    if rid in {"raja_yoga", "dhana_yoga"}:
        for p in y.get("planets", []):
            if c.dignity(p) == "debilitated":
                out.append(f"{p} is in {c.sign(p)}, its weakest sign, so this link gives less.")
    return out


def _dosha_why(name: str, d: dict, c: _Chart) -> list[str]:
    if name == "manglik":
        labels = {"Lagna": "rising sign", "Moon": "Moon", "Venus": "Venus"}
        hit = [ch for ch in d.get("checks", []) if ch.get("active")]
        clear = [ch for ch in d.get("checks", []) if not ch.get("active")]
        lines = [f"From your {labels[ch['reference']]} in {ch['reference_sign']}, Mars in {ch['mars_sign']} "
                 f"is in the {ordinal(ch['house'])} place."
                 + (" (Mars and Venus sit together.)" if ch["reference"] == "Venus" and ch["house"] == 1 else "")
                 for ch in hit]
        if hit and clear:
            lines.append(f"From your {_and([labels[ch['reference']] for ch in clear])}, Mars is clear.")
        return lines
    if name == "gandanta":
        bodies = {"Moon": "Your Moon", "Lagna": "Your rising point", "Sun": "Your Sun"}
        return [f"{bodies.get(h['body'], h['body'])} is {h['degrees_from_junction']:.1f} degrees from the "
                f"{h['signs'].replace('→', ' to ')} changeover." for h in d.get("hits", [])]
    if name == "grahan":
        return [f"Your {h['luminary']} and {h['node']} sit together in {h['sign']}, {h['orb']:.0f} degrees apart."
                for h in d.get("hits", [])]
    return []


def attach_yoga_reading(yogas: list[dict], positions: dict, lagna_lon: float) -> None:
    chart = _Chart(positions, lagna_lon)
    for y in yogas:
        y.setdefault("cancelled", False)
        y.setdefault("cancellations", [])
        y.setdefault("partial", False)
        shown = y["active"] or y["cancelled"]
        y["why"] = _yoga_why(y, chart) if shown else []
        y["weakened"] = _weakened(y, chart) if y["active"] else []


def attach_dosha_reading(doshas: dict, positions: dict, lagna_lon: float) -> None:
    chart = _Chart(positions, lagna_lon)
    for name, d in doshas.items():
        d["why"] = _dosha_why(name, d, chart) if d.get("active") else []
