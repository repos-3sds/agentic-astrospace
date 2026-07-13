"""
Avkahada Chakra — the traditional birth-details table.

Assembles Lagna/Rashi lords, nakshatra data, panchanga limbs and the
classical Melapak attributes (Varna, Vashya, Yoni, Gana, Nadi, Tatwa,
Paya, Vihaga, name syllables). Rules flagged VERIFY in constants.py
follow common software convention pending the reference chart.
"""
from .constants import (
    VARNA_BY_ELEMENT, VASHYA_BY_SIGN, YONI_BY_NAKSHATRA, GANA_BY_NAKSHATRA,
    NADI_BY_NAKSHATRA, TATWA_CYCLE, NAME_SYLLABLES, PAYA_BY_MOON_HOUSE,
    VIHAGA_BIRDS_SHUKLA, VIHAGA_GROUPS, SIGN_ELEMENTS,
)
from .positions import sign_index, sign_name, sign_name_sanskrit, sign_lord, house_from_lagna
from .nakshatra import nakshatra_of


def _vihaga(nak_index: int, paksha: str) -> str:
    birds = VIHAGA_BIRDS_SHUKLA if paksha == "Shukla" else VIHAGA_BIRDS_SHUKLA[::-1]
    for group_idx, (lo, hi) in enumerate(VIHAGA_GROUPS):
        if lo <= nak_index <= hi:
            return birds[group_idx]
    return birds[-1]


def _nadi_pada(pada: int) -> str:
    # VERIFY: sub-nadi per pada; simple 3-cycle convention.
    return ["Aadi", "Madhya", "Antya"][(pada - 1) % 3]


def avkahada_chakra(lagna_lon: float, moon_lon: float, tropical_sun_lon: float,
                    panchanga: dict) -> dict:
    lagna_sign = sign_index(lagna_lon)
    moon_sign = sign_index(moon_lon)
    nak = nakshatra_of(moon_lon)
    moon_house = house_from_lagna(moon_sign, lagna_sign)
    trop_sun_sign = sign_index(tropical_sun_lon)
    paksha = panchanga["tithi"]["paksha"]

    return {
        "lagna": sign_name(lagna_sign),
        "lagna_sanskrit": sign_name_sanskrit(lagna_sign),
        "lagna_lord": sign_lord(lagna_sign),
        "rashi": sign_name(moon_sign),
        "rashi_sanskrit": sign_name_sanskrit(moon_sign),
        "rashi_lord": sign_lord(moon_sign),
        "nakshatra": nak["name"],
        "nakshatra_lord": nak["lord"],
        "charan": nak["pada"],
        "tithi": panchanga["tithi"]["display"],
        "paya": PAYA_BY_MOON_HOUSE[moon_house],
        "yoga": panchanga["yoga"]["name"],
        "karana": panchanga["karana"]["name"],
        "varna": VARNA_BY_ELEMENT[SIGN_ELEMENTS[moon_sign % 4]],
        "tatwa": TATWA_CYCLE[nak["index"] % 5],
        "vashya": VASHYA_BY_SIGN[moon_sign],
        "yoni": "{} ({})".format(*YONI_BY_NAKSHATRA[nak["index"]]),
        "gana": GANA_BY_NAKSHATRA[nak["index"]],
        "nadi": NADI_BY_NAKSHATRA[nak["index"]],
        "nadi_pada": _nadi_pada(nak["pada"]),
        "vihaga": _vihaga(nak["index"], paksha),
        "first_letters": NAME_SYLLABLES[nak["index"]],
        "name_letter": NAME_SYLLABLES[nak["index"]][nak["pada"] - 1],
        "sun_sign_western": sign_name(trop_sun_sign),
        "decanate": int(tropical_sun_lon % 30.0 // 10) + 1,
        "vara": panchanga["vara"]["name"],
    }
