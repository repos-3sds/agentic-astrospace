"""Deterministic yoga and caution-flag detection."""
from __future__ import annotations

from .constants import EXALTATION, NATURAL_RELATIONS, SIGN_LORDS, SIGNS
from .positions import house_from_lagna, sign_index, sign_name
from ...knowledge.vedic_rules import enrich_rule_result

CLASSICAL_PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
KENDRA_HOUSES = {1, 4, 7, 10}
TRIKONA_HOUSES = {1, 5, 9}
DUSTHANA_HOUSES = {6, 8, 12}
WEALTH_HOUSES = {2, 5, 9, 11}
# Natural benefics/malefics for the sign-based yogas below.
# Mercury is treated as a natural benefic; Moon is handled per rule.
NATURAL_BENEFICS = ["Jupiter", "Venus", "Mercury"]
NATURAL_MALEFICS = ["Sun", "Mars", "Saturn", "Rahu", "Ketu"]
# Planets counted for Sunapha/Anapha/Durudhara (excl. Sun, Moon, nodes)
# and Vesi/Vosi/Ubhayachari (excl. Sun, Moon, nodes) — the same five grahas.
LUNISOLAR_SUPPORT_PLANETS = ["Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
STRENGTH_ORDER = ["weak", "moderate", "strong"]
# Kendra (1,4,7,10) + trikona (5,9) + 2nd house — placements accepted for Saraswati.
SARASWATI_HOUSES = {1, 2, 4, 5, 7, 9, 10}
PANCHA_MAHAPURUSHA = {
    "Mars": ("ruchaka_yoga", "Ruchaka Yoga"),
    "Mercury": ("bhadra_yoga", "Bhadra Yoga"),
    "Jupiter": ("hamsa_yoga", "Hamsa Yoga"),
    "Venus": ("malavya_yoga", "Malavya Yoga"),
    "Saturn": ("sasa_yoga", "Sasa Yoga"),
}
SPECIAL_ASPECT_HOUSES = {
    "Mars": {4, 8},
    "Jupiter": {5, 9},
    "Saturn": {3, 10},
}


def _planet_signs(positions: dict) -> dict[str, int]:
    return {planet: sign_index(data["lon"]) for planet, data in positions.items()}


def _house_lords(lagna_sign: int) -> dict[int, str]:
    return {house: SIGN_LORDS[(lagna_sign + house - 1) % 12] for house in range(1, 13)}


def _same_or_opposite(sign_a: int, sign_b: int) -> bool:
    return sign_a == sign_b or (sign_a - sign_b) % 12 == 6


def _planet_aspects(planet: str, from_sign: int, to_sign: int) -> bool:
    house = house_from_lagna(to_sign, from_sign)
    return house == 7 or house in SPECIAL_ASPECT_HOUSES.get(planet, set())


def _parivartana(signs: dict[str, int], planet_a: str, planet_b: str) -> bool:
    return SIGN_LORDS[signs[planet_a]] == planet_b and SIGN_LORDS[signs[planet_b]] == planet_a


def _association(signs: dict[str, int], planet_a: str, planet_b: str) -> tuple[bool, str, bool]:
    """Sambandha check. Returns (associated, mode, mutual).

    Mutual sambandha (conjunction, mutual aspect — incl. mutual 7th — or
    parivartana) is full; a one-way graha drishti is only partial.
    """
    if signs[planet_a] == signs[planet_b]:
        return True, "conjunction", True
    a_aspects_b = _planet_aspects(planet_a, signs[planet_a], signs[planet_b])
    b_aspects_a = _planet_aspects(planet_b, signs[planet_b], signs[planet_a])
    if a_aspects_b and b_aspects_a:
        if house_from_lagna(signs[planet_b], signs[planet_a]) == 7:
            return True, "mutual opposition", True
        return True, "mutual graha drishti", True
    if _parivartana(signs, planet_a, planet_b):
        return True, "parivartana exchange", True
    if a_aspects_b or b_aspects_a:
        return True, "one-way graha drishti (partial sambandha)", False
    return False, "", False


def _debilitation_sign(planet: str) -> int:
    return (EXALTATION[planet][0] + 6) % 12


def _dignity_adjusted(signs: dict[str, int], participants: list[str],
                      strength: str) -> tuple[str, list[str]]:
    """Shift strength one step for participant dignity.

    Any debilitated participant downgrades one step (strong→moderate→weak);
    otherwise an exalted or own-sign participant upgrades one step
    (weak→moderate→strong). Debilitation takes precedence. Returns the
    adjusted strength and explanatory notes for any change applied.
    """
    if strength not in STRENGTH_ORDER:
        return strength, []
    idx = STRENGTH_ORDER.index(strength)
    rated = [p for p in participants if p in EXALTATION and p in signs]
    debilitated = [p for p in rated if signs[p] == _debilitation_sign(p)]
    dignified = [
        p for p in rated
        if signs[p] == EXALTATION[p][0] or SIGN_LORDS[signs[p]] == p
    ]
    notes: list[str] = []
    if debilitated:
        if idx > 0:
            idx -= 1
            notes.append("downgraded: " + ", ".join(f"{p} debilitated" for p in debilitated))
    elif dignified:
        if idx < len(STRENGTH_ORDER) - 1:
            idx += 1
            notes.append("upgraded: " + ", ".join(
                f"{p} {'exalted' if signs[p] == EXALTATION[p][0] else 'in own sign'}"
                for p in dignified
            ))
    return STRENGTH_ORDER[idx], notes


def _occupants(signs: dict[str, int], target_sign: int, planet_set: list[str]) -> list[str]:
    return [p for p in planet_set if signs.get(p) == target_sign]


def _result(rule_id: str, name: str, category: str, active: bool, strength: str, rule: str,
            triggers: list[str], planets: list[str], verified: bool = True,
            notes: list[str] | None = None) -> dict:
    return enrich_rule_result(rule_id, {
        "name": name,
        "category": category,
        "active": active,
        "strength": strength if active else "none",
        "rule": rule,
        "triggers": triggers,
        "planets": planets,
        "verified": verified,
        "notes": notes or [],
    })


def _pancha_mahapurusha(signs: dict[str, int], lagna_sign: int) -> list[dict]:
    out = []
    for planet, (rule_id, name) in PANCHA_MAHAPURUSHA.items():
        sign = signs[planet]
        house = house_from_lagna(sign, lagna_sign)
        exalt_sign = EXALTATION[planet][0]
        own_sign = SIGN_LORDS[sign] == planet
        exalted = sign == exalt_sign
        active = house in KENDRA_HOUSES and (own_sign or exalted)
        dignity = "exalted" if exalted else "own sign" if own_sign else "not own/exalted"
        notes = ["Strength should still consider combustion, aspects, house condition, and divisional support."]
        if active:
            # Own/exalted dignity is definitional here, so no dignity upgrade
            # is applied — the dignity is only reported.
            notes.append(f"dignity: {planet} {dignity} (definitional; no strength adjustment applied)")
        out.append(_result(
            rule_id,
            name,
            "Pancha Mahapurusha",
            active,
            "strong" if exalted else "moderate",
            f"{planet} in own or exaltation sign while placed in a kendra from Lagna.",
            [f"{planet} in {sign_name(sign)} ({dignity}), house {house} from Lagna"] if active else [],
            [planet],
            verified=True,
            notes=notes,
        ))
    return out


def _gajakesari(signs: dict[str, int]) -> dict:
    house = house_from_lagna(signs["Jupiter"], signs["Moon"])
    active = house in KENDRA_HOUSES
    strength, dignity_notes = _dignity_adjusted(
        signs, ["Moon", "Jupiter"], "strong" if house == 1 else "moderate")
    return _result(
        "gaja_kesari_yoga",
        "Gajakesari Yoga",
        "Mind / Wisdom",
        active,
        strength,
        "Jupiter in a kendra from Moon.",
        [f"Jupiter is {house} from Moon"] if active else [],
        ["Moon", "Jupiter"],
        notes=dignity_notes if active else None,
    )


def _chandra_mangal(signs: dict[str, int]) -> dict:
    active = _same_or_opposite(signs["Moon"], signs["Mars"])
    relation = "same sign" if signs["Moon"] == signs["Mars"] else "opposition"
    return _result(
        "chandra_mangal_yoga",
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
        "budhaditya_yoga",
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
        "kemadruma_yoga",
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


def _chandra_yogas(signs: dict[str, int]) -> list[dict]:
    """Sunapha / Anapha / Durudhara — support around the Moon."""
    moon = signs["Moon"]
    second = (moon + 1) % 12
    twelfth = (moon - 1) % 12
    in_second = _occupants(signs, second, LUNISOLAR_SUPPORT_PLANETS)
    in_twelfth = _occupants(signs, twelfth, LUNISOLAR_SUPPORT_PLANETS)
    durudhara = bool(in_second) and bool(in_twelfth)
    subsume_note = ["Subsumed by Durudhara Yoga (both 2nd and 12th from Moon occupied)."] if durudhara else None
    out = [
        _result(
            "sunapha_yoga",
            "Sunapha Yoga",
            "Lunar Support",
            bool(in_second),
            "moderate",
            "A planet other than Sun, Moon, Rahu, Ketu occupies the 2nd sign from Moon.",
            [f"{', '.join(in_second)} in {sign_name(second)}, 2nd from Moon"] if in_second else [],
            ["Moon", *in_second],
            notes=subsume_note if in_second else None,
        ),
        _result(
            "anapha_yoga",
            "Anapha Yoga",
            "Lunar Support",
            bool(in_twelfth),
            "moderate",
            "A planet other than Sun, Moon, Rahu, Ketu occupies the 12th sign from Moon.",
            [f"{', '.join(in_twelfth)} in {sign_name(twelfth)}, 12th from Moon"] if in_twelfth else [],
            ["Moon", *in_twelfth],
            notes=subsume_note if in_twelfth else None,
        ),
        _result(
            "durudhara_yoga",
            "Durudhara Yoga",
            "Lunar Support",
            durudhara,
            "strong",
            "Planets other than Sun, Moon, Rahu, Ketu occupy both the 2nd and 12th signs from Moon.",
            [
                f"{', '.join(in_second)} in {sign_name(second)}, 2nd from Moon",
                f"{', '.join(in_twelfth)} in {sign_name(twelfth)}, 12th from Moon",
            ] if durudhara else [],
            ["Moon", *in_second, *in_twelfth],
        ),
    ]
    return out


def _surya_yogas(signs: dict[str, int]) -> list[dict]:
    """Vesi / Vosi / Ubhayachari — support around the Sun."""
    sun = signs["Sun"]
    second = (sun + 1) % 12
    twelfth = (sun - 1) % 12
    in_second = _occupants(signs, second, LUNISOLAR_SUPPORT_PLANETS)
    in_twelfth = _occupants(signs, twelfth, LUNISOLAR_SUPPORT_PLANETS)
    ubhayachari = bool(in_second) and bool(in_twelfth)
    subsume_note = ["Subsumed by Ubhayachari Yoga (both 2nd and 12th from Sun occupied)."] if ubhayachari else None
    return [
        _result(
            "vesi_yoga",
            "Vesi Yoga",
            "Solar Support",
            bool(in_second),
            "moderate",
            "A planet other than Moon, Rahu, Ketu occupies the 2nd sign from Sun.",
            [f"{', '.join(in_second)} in {sign_name(second)}, 2nd from Sun"] if in_second else [],
            ["Sun", *in_second],
            notes=subsume_note if in_second else None,
        ),
        _result(
            "vosi_yoga",
            "Vosi Yoga",
            "Solar Support",
            bool(in_twelfth),
            "moderate",
            "A planet other than Moon, Rahu, Ketu occupies the 12th sign from Sun.",
            [f"{', '.join(in_twelfth)} in {sign_name(twelfth)}, 12th from Sun"] if in_twelfth else [],
            ["Sun", *in_twelfth],
            notes=subsume_note if in_twelfth else None,
        ),
        _result(
            "ubhayachari_yoga",
            "Ubhayachari Yoga",
            "Solar Support",
            ubhayachari,
            "strong",
            "Planets other than Moon, Rahu, Ketu occupy both the 2nd and 12th signs from Sun.",
            [
                f"{', '.join(in_second)} in {sign_name(second)}, 2nd from Sun",
                f"{', '.join(in_twelfth)} in {sign_name(twelfth)}, 12th from Sun",
            ] if ubhayachari else [],
            ["Sun", *in_second, *in_twelfth],
        ),
    ]


def _adhi(signs: dict[str, int]) -> dict:
    moon = signs["Moon"]
    occupied: dict[int, list[str]] = {}
    for offset in (6, 7, 8):
        target = (moon + offset - 1) % 12
        found = _occupants(signs, target, NATURAL_BENEFICS)
        if found:
            occupied[offset] = found
    count = len(occupied)
    active = count >= 2
    triggers = [
        f"{', '.join(planets)} in {sign_name((moon + house - 1) % 12)}, {house} from Moon"
        for house, planets in sorted(occupied.items())
    ] if active else []
    participants = ["Moon", *[p for planets in occupied.values() for p in planets]] if active else ["Moon"]
    return _result(
        "adhi_yoga",
        "Adhi Yoga",
        "Lunar Support",
        active,
        "strong" if count == 3 else "moderate",
        "Natural benefics (Jupiter, Venus, Mercury) occupy the 6th, 7th, and 8th signs from Moon.",
        triggers,
        participants,
        verified=False,
        notes=[f"{count} of the three houses (6/7/8 from Moon) hold a benefic."] if active else None,
    )


def _amala(signs: dict[str, int], lagna_sign: int) -> dict:
    triggers = []
    participants: list[str] = []
    anchors_hit = []
    for anchor, base in (("Lagna", lagna_sign), ("Moon", signs["Moon"])):
        tenth = (base + 9) % 12
        found = _occupants(signs, tenth, NATURAL_BENEFICS)
        if found:
            anchors_hit.append(anchor)
            triggers.append(f"{', '.join(found)} in {sign_name(tenth)}, 10th from {anchor}")
            participants.extend(p for p in found if p not in participants)
    active = bool(anchors_hit)
    return _result(
        "amala_yoga",
        "Amala Yoga",
        "Reputation / Career",
        active,
        "strong" if len(anchors_hit) == 2 else "moderate",
        "A natural benefic (Jupiter, Venus, Mercury) occupies the 10th from Lagna or the 10th from Moon.",
        triggers,
        participants,
        notes=[f"Anchor(s): {', '.join(anchors_hit)}."] if active else None,
    )


def _saraswati(signs: dict[str, int], lagna_sign: int) -> dict:
    placements = {
        planet: house_from_lagna(signs[planet], lagna_sign)
        for planet in NATURAL_BENEFICS
    }
    houses_ok = all(house in SARASWATI_HOUSES for house in placements.values())
    jup_sign = signs["Jupiter"]
    jup_lord = SIGN_LORDS[jup_sign]
    exalted = jup_sign == EXALTATION["Jupiter"][0]
    own = jup_lord == "Jupiter"
    friendly = jup_lord in NATURAL_RELATIONS["Jupiter"]["friends"]
    jup_dignity = "exalted" if exalted else "own sign" if own else "friendly sign" if friendly else "weak sign"
    active = houses_ok and (exalted or own or friendly)
    triggers = [
        *[f"{planet} in house {house} from Lagna (kendra/trikona/2nd)" for planet, house in placements.items()],
        f"Jupiter in {sign_name(jup_sign)} ({jup_dignity})",
    ] if active else []
    return _result(
        "saraswati_yoga",
        "Saraswati Yoga",
        "Learning / Wisdom",
        active,
        "strong",
        "Jupiter, Venus, and Mercury each in a kendra, trikona, or the 2nd house from Lagna, "
        "with Jupiter in own, exaltation, or a friendly sign.",
        triggers,
        list(NATURAL_BENEFICS),
        notes=["Friendly sign judged by natural friendship of the sign lord toward Jupiter (Sun, Moon, Mars)."] if active else None,
    )


def _kartari(signs: dict[str, int], lagna_sign: int) -> list[dict]:
    """Shubha / Papa Kartari (scissors) yogas around Lagna and Moon."""
    out = []
    for anchor, base in (("Lagna", lagna_sign), ("Moon", signs["Moon"])):
        second = (base + 1) % 12
        twelfth = (base - 1) % 12
        ben_second = _occupants(signs, second, NATURAL_BENEFICS)
        ben_twelfth = _occupants(signs, twelfth, NATURAL_BENEFICS)
        mal_second = _occupants(signs, second, NATURAL_MALEFICS)
        mal_twelfth = _occupants(signs, twelfth, NATURAL_MALEFICS)
        shubha = bool(ben_second) and bool(ben_twelfth) and not mal_second and not mal_twelfth
        papa = bool(mal_second) and bool(mal_twelfth) and not ben_second and not ben_twelfth
        out.append(_result(
            "shubha_kartari_yoga",
            f"Shubha Kartari Yoga (from {anchor})",
            "Support / Protection",
            shubha,
            "moderate",
            "Natural benefics occupy both the 12th and 2nd signs from the anchor, with no malefic in either.",
            [
                f"{', '.join(ben_twelfth)} in {sign_name(twelfth)}, 12th from {anchor}",
                f"{', '.join(ben_second)} in {sign_name(second)}, 2nd from {anchor}",
            ] if shubha else [],
            [*ben_twelfth, *ben_second] if shubha else [],
        ))
        out.append(_result(
            "papa_kartari_yoga",
            f"Papa Kartari Yoga (from {anchor})",
            "Caution / Affliction",
            papa,
            "moderate",
            "Natural malefics occupy both the 12th and 2nd signs from the anchor, with no benefic in either.",
            [
                f"{', '.join(mal_twelfth)} in {sign_name(twelfth)}, 12th from {anchor}",
                f"{', '.join(mal_second)} in {sign_name(second)}, 2nd from {anchor}",
            ] if papa else [],
            [*mal_twelfth, *mal_second] if papa else [],
        ))
    return out


def _shakata(signs: dict[str, int], lagna_sign: int) -> dict:
    house_from_jupiter = house_from_lagna(signs["Moon"], signs["Jupiter"])
    base_condition = house_from_jupiter in DUSTHANA_HOUSES
    moon_in_kendra = house_from_lagna(signs["Moon"], lagna_sign) in KENDRA_HOUSES
    cancelled = base_condition and moon_in_kendra
    active = base_condition and not moon_in_kendra
    notes = None
    if cancelled:
        notes = ["Cancelled: Moon occupies a kendra from Lagna."]
    return _result(
        "shakata_yoga",
        "Shakata Yoga",
        "Caution / Mind",
        active,
        "moderate",
        "Moon in the 6th, 8th, or 12th from Jupiter; cancelled when Moon is in a kendra from Lagna.",
        [f"Moon is {house_from_jupiter} from Jupiter"] if active else [],
        ["Moon", "Jupiter"],
        notes=notes,
    )


def _guru_chandala(signs: dict[str, int]) -> dict:
    with_rahu = signs["Jupiter"] == signs["Rahu"]
    with_ketu = signs["Jupiter"] == signs["Ketu"]
    active = with_rahu or with_ketu
    node = "Rahu" if with_rahu else "Ketu"
    notes = None
    if with_ketu and not with_rahu:
        notes = ["Jupiter-Ketu variant: reported as a milder form of the classical Jupiter-Rahu combination."]
    return _result(
        "guru_chandala_yoga",
        "Guru-Chandala Yoga",
        "Caution / Beliefs",
        active,
        "moderate" if with_rahu else "weak",
        "Jupiter conjunct Rahu in the same sign (primary); Jupiter conjunct Ketu reported as a milder variant.",
        [f"Jupiter and {node} in {sign_name(signs['Jupiter'])}"] if active else [],
        ["Jupiter", node] if active else ["Jupiter"],
        notes=notes,
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
            "neecha_bhanga_raja_yoga",
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
            associated, mode, mutual = _association(signs, k_lord, t_lord)
            if associated:
                seen.add(key)
                strength, dignity_notes = _dignity_adjusted(
                    signs, [k_lord, t_lord], "moderate" if mutual else "weak")
                out.append(_result(
                    "raja_yoga",
                    f"Raja Yoga: {k_lord}-{t_lord}",
                    "Power / Career",
                    True,
                    strength,
                    "Kendra lord and trikona lord associate by conjunction, opposition, graha drishti, or parivartana.",
                    [f"{k_lord} and {t_lord} connect by {mode} as lords of houses {kendra} and {trikona}"],
                    [k_lord, t_lord],
                    verified=False,
                    notes=["Parivartana and classical graha drishti included; full strength assessment pending.",
                           *dignity_notes],
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
            associated, mode, mutual = _association(signs, lord_a, lord_b)
            if associated:
                seen.add(key)
                strength, dignity_notes = _dignity_adjusted(
                    signs, [lord_a, lord_b], "moderate" if mutual else "weak")
                out.append(_result(
                    "dhana_yoga",
                    f"Dhana Yoga: {lord_a}-{lord_b}",
                    "Wealth",
                    True,
                    strength,
                    "Wealth-house lords associate by conjunction, opposition, graha drishti, or parivartana.",
                    [f"{lord_a} and {lord_b} connect by {mode} as lords of houses {house_a} and {house_b}"],
                    [lord_a, lord_b],
                    verified=False,
                    notes=["Parivartana and classical graha drishti included; full strength assessment pending.",
                           *dignity_notes],
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
                "viparita_raja_yoga",
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
        "kalasarpa_flag",
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


# ── Nabhasa yogas (T3.1, docs/backend_astro_depth_checklist_2026-08-06.md) ───
# BPHS ch. 35/37 describes 32 Nabhasa yogas in four groups: Ashraya (3),
# Dala (2), Akriti (20), Sankhya (6) — 1 + 2 + ... doesn't sum that way
# because Akriti is itself further subdivided; the widely-cited headline
# count is 32. This pass implements the Ashraya, Dala and Sankhya groups
# (11 yogas) — the ones with unambiguous, single-source-agreed trigger
# conditions found in research for this pass. The 20 Akriti (shape) yogas
# are deliberately deferred: their trigger conditions (which of the 12
# houses from Lagna are occupied, in which specific pattern) have more
# room for source disagreement per-yoga, and guessing at 20 of them in one
# pass risks more error than value — see the checklist for what a future
# pass should do with them.

_SANKHYA_NAMES = {
    1: ("gola_yoga", "Gola Yoga"),
    2: ("yuga_yoga", "Yuga Yoga"),
    3: ("shoola_yoga", "Shoola Yoga"),
    4: ("kedara_yoga", "Kedara Yoga"),
    5: ("pasa_yoga", "Pasa Yoga"),
    6: ("dama_yoga", "Dama Yoga"),
}


def _ashraya_yogas(signs: dict[str, int]) -> list[dict]:
    """Rajju/Musala/Nala: all seven classical planets share one sign
    quality (movable/fixed/dual)."""
    qualities = {signs[p] % 3 for p in CLASSICAL_PLANETS}
    single_quality = qualities if len(qualities) == 1 else None
    quality = next(iter(single_quality)) if single_quality else None
    specs = [
        (0, "rajju_yoga", "Rajju Yoga", "movable"),
        (1, "musala_yoga", "Musala Yoga", "fixed"),
        (2, "nala_yoga", "Nala Yoga", "dual"),
    ]
    out = []
    for q, rule_id, name, label in specs:
        active = quality == q
        out.append(_result(
            rule_id, name, "Nabhasa / Ashraya", active, "moderate" if active else "none",
            f"All seven classical planets occupy {label} signs.",
            [f"All planets in {label} signs"] if active else [],
            list(CLASSICAL_PLANETS),
            verified=False,
            notes=["Ashraya group: a whole-chart placement pattern, not tied to a house or lord."],
        ))
    return out


def _dala_yogas(signs: dict[str, int], lagna_sign: int) -> list[dict]:
    """Mala (benefic) / Sarpa (malefic): Mercury+Venus+Jupiter, or
    Sun+Mars+Saturn, each individually placed in a kendra (1/4/7/10) from
    Lagna."""
    def _in_kendra(planets: list[str]) -> tuple[bool, list[str]]:
        houses = {p: house_from_lagna(signs[p], lagna_sign) for p in planets}
        active = all(h in KENDRA_HOUSES for h in houses.values())
        triggers = [f"{p} in house {h} from Lagna" for p, h in houses.items()] if active else []
        return active, triggers

    mala_active, mala_triggers = _in_kendra(["Mercury", "Venus", "Jupiter"])
    sarpa_active, sarpa_triggers = _in_kendra(["Sun", "Mars", "Saturn"])
    return [
        _result(
            "mala_yoga", "Mala Yoga", "Nabhasa / Dala", mala_active,
            "moderate" if mala_active else "none",
            "Mercury, Venus and Jupiter each occupy a kendra (1/4/7/10) from Lagna.",
            mala_triggers, ["Mercury", "Venus", "Jupiter"],
            verified=False,
            notes=["Dala group, benefic form: 'mutual kendras' read as each planet "
                   "individually in a kendra from Lagna (convention — see Sarpa Yoga)."],
        ),
        _result(
            "sarpa_yoga", "Sarpa Yoga", "Nabhasa / Dala (Caution)", sarpa_active,
            "moderate" if sarpa_active else "none",
            "Sun, Mars and Saturn each occupy a kendra (1/4/7/10) from Lagna.",
            sarpa_triggers, ["Sun", "Mars", "Saturn"],
            verified=False,
            notes=["Dala group, caution form — a caution flag, not a verdict.",
                   "'Mutual kendras' read as each planet individually in a kendra from "
                   "Lagna, not pairwise 90 degree separation between the three planets; "
                   "sources are not fully explicit on which reading is intended."],
        ),
    ]


def _sankhya_yoga(signs: dict[str, int]) -> dict:
    """Gola/Yuga/Shoola/Kedara/Pasa/Dama: graded by how many distinct
    signs the seven classical planets occupy (1 through 6; 7 distinct
    signs forms no Sankhya yoga in the source used for this pass)."""
    occupied = {signs[p] for p in CLASSICAL_PLANETS}
    count = len(occupied)
    rule_id, name = _SANKHYA_NAMES.get(count, (None, None))
    active = rule_id is not None
    return _result(
        rule_id or "sankhya_yoga", name or "Sankhya Yoga (none)", "Nabhasa / Sankhya",
        active, "moderate" if active else "none",
        "Graded by the count of distinct signs occupied by the seven classical "
        "planets: 1=Gola, 2=Yuga, 3=Shoola, 4=Kedara, 5=Pasa, 6=Dama.",
        [f"Seven classical planets occupy {count} distinct signs"] if active else [],
        list(CLASSICAL_PLANETS),
        verified=False,
        notes=[f"{count} distinct sign(s) occupied.",
               "Nodes (Rahu/Ketu) excluded, matching the classical Sankhya definition."],
    )


def yoga_summary(positions: dict, lagna_lon: float) -> dict:
    signs = _planet_signs(positions)
    lagna_sign = sign_index(lagna_lon)
    yogas = [
        *_pancha_mahapurusha(signs, lagna_sign),
        _gajakesari(signs),
        _chandra_mangal(signs),
        _budhaditya(signs),
        *_chandra_yogas(signs),
        _adhi(signs),
        _kemadruma(signs),
        *_surya_yogas(signs),
        _amala(signs, lagna_sign),
        _saraswati(signs, lagna_sign),
        *_kartari(signs, lagna_sign),
        _shakata(signs, lagna_sign),
        _guru_chandala(signs),
        *_neecha_bhanga(signs, lagna_sign),
        *_raja_yoga(signs, lagna_sign),
        *_dhana_yoga(signs, lagna_sign),
        *_vipareeta_raja(signs, lagna_sign),
        _kalasarpa(signs),
        *_ashraya_yogas(signs),
        *_dala_yogas(signs, lagna_sign),
        _sankhya_yoga(signs),
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
            "association": "conjunction, mutual aspect (incl. mutual 7th and special drishti for Mars/Jupiter/Saturn), or parivartana grade moderate; one-way graha drishti grades weak (partial sambandha)",
            "dignity": "Raja/Dhana/Gajakesari strength shifts one step down for a debilitated participant, one step up for an exalted/own-sign participant",
            "benefics": "natural benefics for sign-based yogas: Jupiter, Venus, Mercury (Moon handled per rule); malefics: Sun, Mars, Saturn, Rahu, Ketu",
            "status": "first deterministic pass; advanced cancellation and aspect rules remain on checklist",
            "rules_kb": "astrospace/knowledge/vedic_rules",
        },
    }
