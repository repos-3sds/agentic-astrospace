"""Deterministic yoga and caution-flag detection."""
from __future__ import annotations

from .constants import EXALTATION, SIGN_LORDS, SIGNS
from .positions import house_from_lagna, sign_index, sign_name

CLASSICAL_PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
KENDRA_HOUSES = {1, 4, 7, 10}
TRIKONA_HOUSES = {1, 5, 9}
DUSTHANA_HOUSES = {6, 8, 12}
WEALTH_HOUSES = {2, 5, 9, 11}


def _planet_signs(positions: dict) -> dict[str, int]:
    return {planet: sign_index(data["lon"]) for planet, data in positions.items()}


def _house_lords(lagna_sign: int) -> dict[int, str]:
    return {house: SIGN_LORDS[(lagna_sign + house - 1) % 12] for house in range(1, 13)}


def _same_or_opposite(sign_a: int, sign_b: int) -> bool:
    return sign_a == sign_b or (sign_a - sign_b) % 12 == 6


def _result(name: str, category: str, active: bool, strength: str, rule: str,
            triggers: list[str], planets: list[str], verified: bool = True,
            notes: list[str] | None = None) -> dict:
    return {
        "name": name,
        "category": category,
        "active": active,
        "strength": strength if active else "none",
        "rule": rule,
        "triggers": triggers,
        "planets": planets,
        "verified": verified,
        "notes": notes or [],
    }


def _gajakesari(signs: dict[str, int]) -> dict:
    house = house_from_lagna(signs["Jupiter"], signs["Moon"])
    active = house in KENDRA_HOUSES
    return _result(
        "Gajakesari Yoga",
        "Mind / Wisdom",
        active,
        "strong" if house == 1 else "moderate",
        "Jupiter in a kendra from Moon.",
        [f"Jupiter is {house} from Moon"] if active else [],
        ["Moon", "Jupiter"],
    )


def _chandra_mangal(signs: dict[str, int]) -> dict:
    active = _same_or_opposite(signs["Moon"], signs["Mars"])
    relation = "same sign" if signs["Moon"] == signs["Mars"] else "opposition"
    return _result(
        "Chandra-Mangal Yoga",
        "Wealth / Drive",
        active,
        "strong" if signs["Moon"] == signs["Mars"] else "moderate",
        "Moon and Mars conjoin or mutually oppose.",
        [f"Moon and Mars in {relation}"] if active else [],
        ["Moon", "Mars"],
    )


def _budhaditya(signs: dict[str, int]) -> dict:
    active = signs["Sun"] == signs["Mercury"]
    return _result(
        "Budhaditya Yoga",
        "Intellect / Status",
        active,
        "moderate",
        "Sun and Mercury in the same sign.",
        [f"Sun and Mercury in {sign_name(signs['Sun'])}"] if active else [],
        ["Sun", "Mercury"],
    )


def _kemadruma(signs: dict[str, int]) -> dict:
    moon = signs["Moon"]
    adjacent = {(moon - 1) % 12, (moon + 1) % 12}
    support_planets = [p for p in CLASSICAL_PLANETS if p not in ("Moon", "Sun")]
    adjacent_support = [p for p in support_planets if signs[p] in adjacent]
    kendra_support = [
        p for p in support_planets
        if house_from_lagna(signs[p], moon) in KENDRA_HOUSES
    ]
    active = not adjacent_support and not kendra_support
    return _result(
        "Kemadruma Yoga",
        "Caution / Mind",
        active,
        "strong",
        "No classical support planets adjacent to Moon or in kendras from Moon.",
        ["Moon lacks adjacent and kendra support"] if active else [],
        ["Moon"],
        verified=False,
        notes=["Kemadruma cancellation rules vary; this uses a conservative simplified flag."],
    )


def _neecha_bhanga(signs: dict[str, int], lagna_sign: int) -> list[dict]:
    out = []
    moon_sign = signs["Moon"]
    for planet in CLASSICAL_PLANETS:
        exalt_sign = EXALTATION[planet][0]
        deb_sign = (exalt_sign + 6) % 12
        if signs[planet] != deb_sign:
            continue
        deb_lord = SIGN_LORDS[deb_sign]
        lord_sign = signs.get(deb_lord)
        triggers = []
        if lord_sign is not None and house_from_lagna(lord_sign, lagna_sign) in KENDRA_HOUSES:
            triggers.append(f"{deb_lord}, lord of debilitation sign, is kendra from Lagna")
        if lord_sign is not None and house_from_lagna(lord_sign, moon_sign) in KENDRA_HOUSES:
            triggers.append(f"{deb_lord}, lord of debilitation sign, is kendra from Moon")
        out.append(_result(
            f"Neecha Bhanga for {planet}",
            "Correction / Strength",
            bool(triggers),
            "moderate",
            "Debilitated planet receives cancellation when debilitation sign lord is in kendra from Lagna or Moon.",
            triggers,
            [planet, deb_lord],
            verified=False,
            notes=["Partial Neecha Bhanga implementation; additional cancellation rules pending validation."],
        ))
    return out


def _raja_yoga(signs: dict[str, int], lagna_sign: int) -> list[dict]:
    lords = _house_lords(lagna_sign)
    out = []
    seen = set()
    for kendra in KENDRA_HOUSES:
        for trikona in TRIKONA_HOUSES:
            k_lord = lords[kendra]
            t_lord = lords[trikona]
            if k_lord == t_lord:
                continue
            key = tuple(sorted((k_lord, t_lord)))
            if key in seen:
                continue
            if _same_or_opposite(signs[k_lord], signs[t_lord]):
                seen.add(key)
                out.append(_result(
                    f"Raja Yoga: {k_lord}-{t_lord}",
                    "Power / Career",
                    True,
                    "moderate",
                    "Kendra lord and trikona lord are conjoined or mutually opposite.",
                    [f"{k_lord} and {t_lord} connect as lords of houses {kendra} and {trikona}"],
                    [k_lord, t_lord],
                    verified=False,
                    notes=["Basic Parashari association check; aspects beyond opposition pending."],
                ))
    return out


def _dhana_yoga(signs: dict[str, int], lagna_sign: int) -> list[dict]:
    lords = _house_lords(lagna_sign)
    wealth_lords = {house: lords[house] for house in WEALTH_HOUSES}
    out = []
    seen = set()
    for house_a, lord_a in wealth_lords.items():
        for house_b, lord_b in wealth_lords.items():
            if house_a >= house_b or lord_a == lord_b:
                continue
            key = tuple(sorted((lord_a, lord_b)))
            if key in seen:
                continue
            if _same_or_opposite(signs[lord_a], signs[lord_b]):
                seen.add(key)
                out.append(_result(
                    f"Dhana Yoga: {lord_a}-{lord_b}",
                    "Wealth",
                    True,
                    "moderate",
                    "Wealth-house lords connect by conjunction or opposition.",
                    [f"{lord_a} and {lord_b} connect as lords of houses {house_a} and {house_b}"],
                    [lord_a, lord_b],
                    verified=False,
                    notes=["Basic wealth-lord association check; full strength assessment pending."],
                ))
    return out


def _vipareeta_raja(signs: dict[str, int], lagna_sign: int) -> list[dict]:
    lords = _house_lords(lagna_sign)
    out = []
    for house in DUSTHANA_HOUSES:
        lord = lords[house]
        placed_house = house_from_lagna(signs[lord], lagna_sign)
        if placed_house in DUSTHANA_HOUSES:
            out.append(_result(
                f"Vipareeta Raja Yoga: {lord}",
                "Resilience / Reversal",
                True,
                "moderate",
                "Lord of a dusthana placed in a dusthana.",
                [f"{lord}, lord of house {house}, placed in house {placed_house}"],
                [lord],
            ))
    return out


def _kalasarpa(signs: dict[str, int]) -> dict:
    rahu = signs["Rahu"]
    ketu = signs["Ketu"]
    def clockwise_between(start: int, end: int, point: int) -> bool:
        return 0 < ((point - start) % 12) < ((end - start) % 12)

    planets = [p for p in CLASSICAL_PLANETS]
    between_rahu_ketu = all(clockwise_between(rahu, ketu, signs[p]) for p in planets)
    between_ketu_rahu = all(clockwise_between(ketu, rahu, signs[p]) for p in planets)
    active = between_rahu_ketu or between_ketu_rahu
    return _result(
        "Kalasarpa Flag",
        "Caution / Karmic",
        active,
        "moderate",
        "All seven classical planets fall between Rahu and Ketu on one side of the nodal axis.",
        ["All classical planets lie within one nodal arc"] if active else [],
        ["Rahu", "Ketu"],
        verified=False,
        notes=["Sign-based flag only; degree-precise and exception rules pending validation."],
    )


def yoga_summary(positions: dict, lagna_lon: float) -> dict:
    signs = _planet_signs(positions)
    lagna_sign = sign_index(lagna_lon)
    yogas = [
        _gajakesari(signs),
        _chandra_mangal(signs),
        _budhaditya(signs),
        _kemadruma(signs),
        *_neecha_bhanga(signs, lagna_sign),
        *_raja_yoga(signs, lagna_sign),
        *_dhana_yoga(signs, lagna_sign),
        *_vipareeta_raja(signs, lagna_sign),
        _kalasarpa(signs),
    ]
    active = [y for y in yogas if y["active"]]
    categories = {}
    for yoga in active:
        categories[yoga["category"]] = categories.get(yoga["category"], 0) + 1
    return {
        "lagna": sign_name(lagna_sign),
        "total": len(yogas),
        "active_count": len(active),
        "active": active,
        "all": yogas,
        "categories": categories,
        "conventions": {
            "association": "same sign or opposition unless otherwise stated",
            "status": "first deterministic pass; advanced cancellation and aspect rules remain on checklist",
        },
    }
