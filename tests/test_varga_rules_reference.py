"""
Higher-varga rules checked against an independent table of BPHS start signs.

A tester who practises astrology reported the lagna differing from his own
software from D7 upward (2026-10-20). The rules in vargas.py were checked
against BPHS ch. 6 and matched; these tests pin that result so a later edit
cannot quietly break one of the equal-part vargas. The table below is written
as "which sign does part 1 start from", the way the texts state it, rather
than as the arithmetic vargas.py uses, so the two are independent.
"""
from fractions import Fraction

import pytest

from astrospace.core.vedic.positions import birth_moment, sidereal_lagna
from astrospace.core.vedic.vargas import VARGA_FUNCTIONS

ARIES, TAURUS, CANCER, LEO, LIBRA, SAGITTARIUS, CAPRICORN = 0, 1, 3, 4, 6, 8, 9


def _start_sign(n: int, s: int) -> int:
    odd = s % 2 == 0  # Aries, Gemini, Leo ... are odd signs
    quality = s % 3   # movable, fixed, dual
    element = s % 4   # fire, earth, air, water
    rules = {
        7: s if odd else s + 6,
        9: (ARIES, CAPRICORN, LIBRA, CANCER)[element],
        10: s if odd else s + 8,
        12: s,
        16: (ARIES, LEO, SAGITTARIUS)[quality],
        20: (ARIES, SAGITTARIUS, LEO)[quality],
        24: LEO if odd else CANCER,
        27: (ARIES, CANCER, LIBRA, CAPRICORN)[element],
        40: ARIES if odd else LIBRA,
        45: (ARIES, LEO, SAGITTARIUS)[quality],
        60: s,
    }
    return rules[n] % 12


@pytest.mark.parametrize("n", [7, 9, 10, 12, 16, 20, 24, 27, 40, 45, 60])
def test_equal_part_varga_matches_bphs_table(n):
    fn = VARGA_FUNCTIONS[f"D{n}"]
    # every half arc-minute of the zodiac, nudged off the exact boundaries
    for i in range(360 * 120):
        lon = Fraction(i, 120) + Fraction(1, 10**7)
        s = int(lon // 30)
        part = int((lon - 30 * s) * n / 30)
        assert fn(float(lon)) == (_start_sign(n, s) + part) % 12, (n, float(lon))


def test_lagna_agrees_with_tropical_ascendant_minus_true_ayanamsha():
    """The sidereal lagna is the tropical ascendant less Lahiri ayanamsha
    (with nutation, as for the planets): within a couple of arc-seconds."""
    import swisseph as swe

    m = birth_moment(1965, 8, 15, 6, 30, lat=16.98, lng=81.78, tz_str="Asia/Kolkata")
    lagna = sidereal_lagna(m.jd_ut, m.lat, m.lng, "lahiri")
    swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
    _cusps, ascmc = swe.houses(m.jd_ut, m.lat, m.lng, b"W")
    true_ayanamsha = swe.get_ayanamsa_ex_ut(m.jd_ut, swe.FLG_SWIEPH)[1]
    assert abs(((ascmc[0] - true_ayanamsha) % 360.0) - lagna) * 3600 < 2
