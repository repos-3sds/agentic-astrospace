"""
Divisional chart payloads for one fixed birth chart, worked by hand.

A tester saw the planet table on the Charts & Vargas screen show the same
signs for D1 through D60 (2026-10-24). The screen was reading D1; the varga
payload was right. These tests pin what that payload says for a known chart,
so the screen has something correct to read.

Chart: 15 Aug 1965, 06:30 IST, Rajahmundry (16.98 N, 81.78 E), Lahiri.
D1 longitudes from the engine, then each varga sign worked from BPHS ch. 6:

  Lagna    Leo 8.01      D9 Leo is fire, from Aries, part 3     -> Gemini
                         D10 odd sign, from Leo, part 3          -> Libra
  Sun      Cancer 28.62  D9 water, from Cancer, part 9           -> Pisces
                         D10 even, from Pisces, part 10          -> Sagittarius
  Moon     Aquarius 28.49 D9 air, from Libra, part 9             -> Gemini
                         D10 odd, from Aquarius, part 10         -> Scorpio
  Mars     Libra 3.20    D9 air, from Libra, part 1              -> Libra
                         D10 odd, from Libra, part 2             -> Scorpio
  Jupiter  Gemini 1.65   D9 air, from Libra, part 1              -> Libra
                         D10 odd, from Gemini, part 1            -> Gemini
  Venus    Virgo 1.23    D9 earth, from Capricorn, part 1        -> Capricorn
                         D10 even, from Taurus, part 1           -> Taurus
  Saturn   Aquarius 22.10 D9 air, from Libra, part 7             -> Aries
                         D10 odd, from Aquarius, part 8          -> Virgo
  Rahu     Taurus 16.63  D9 earth, from Capricorn, part 5        -> Taurus
                         D10 even, from Capricorn, part 6        -> Gemini
  Ketu     Scorpio 16.63 D9 water, from Cancer, part 5           -> Scorpio
                         D10 even, from Cancer, part 6           -> Sagittarius
"""
import pytest

from astrospace.core.vedic.chart import VedicChart
from astrospace.core.vedic.nakshatra import nakshatra_of
from astrospace.core.vedic.vargas import VARGA_FUNCTIONS, varga_longitude

D1 = {
    "Sun": "Cancer", "Moon": "Aquarius", "Mars": "Libra", "Mercury": "Cancer",
    "Jupiter": "Gemini", "Venus": "Virgo", "Saturn": "Aquarius",
    "Rahu": "Taurus", "Ketu": "Scorpio",
}
D9 = {
    "Sun": "Pisces", "Moon": "Gemini", "Mars": "Libra", "Mercury": "Pisces",
    "Jupiter": "Libra", "Venus": "Capricorn", "Saturn": "Aries",
    "Rahu": "Taurus", "Ketu": "Scorpio",
}
D10 = {
    "Sun": "Sagittarius", "Moon": "Scorpio", "Mars": "Scorpio", "Mercury": "Sagittarius",
    "Jupiter": "Gemini", "Venus": "Taurus", "Saturn": "Virgo",
    "Rahu": "Gemini", "Ketu": "Sagittarius",
}


@pytest.fixture(scope="module")
def chart():
    return VedicChart("Known chart", 1965, 8, 15, 6, 30,
                      lat=16.98, lng=81.78, tz_str="Asia/Kolkata")


@pytest.mark.parametrize("varga, lagna, signs", [
    ("D1", "Leo", D1),
    ("D9", "Gemini", D9),
    ("D10", "Libra", D10),
])
def test_varga_signs_match_hand_worked_chart(chart, varga, lagna, signs):
    payload = chart.varga_chart(varga)
    assert payload["lagna"]["sign"] == lagna
    assert {p: row["sign"] for p, row in payload["planets"].items()} == signs


def test_varga_houses_count_from_the_varga_lagna(chart):
    # D9 lagna Gemini: Libra is the 5th, Pisces the 10th, Gemini itself the 1st
    planets = chart.varga_chart("D9")["planets"]
    assert planets["Mars"]["house"] == 5
    assert planets["Sun"]["house"] == 10
    assert planets["Moon"]["house"] == 1


def test_vargottama_is_the_same_sign_in_d1_and_d9(chart):
    planets = chart.varga_chart("D9")["planets"]
    assert {p for p, row in planets.items() if row["vargottama"]} == {"Mars", "Rahu", "Ketu"}


def test_dignity_is_judged_in_the_varga_not_copied_from_d1(chart):
    # Saturn sits in Aries in D9 and the Moon in Scorpio in D10: both debilitated
    # there, whatever their D1 dignity is.
    assert chart.varga_chart("D9")["planets"]["Saturn"]["dignity"] == "Debilitated"
    assert chart.varga_chart("D10")["planets"]["Moon"]["dignity"] == "Debilitated"
    assert chart.dignities()["Saturn"]["dignity"] != "Debilitated"


def test_d1_varga_dignity_agrees_with_the_chart_dignities(chart):
    d1 = chart.varga_chart("D1")["planets"]
    dignities = chart.dignities()
    for planet, row in d1.items():
        assert row["dignity"] == dignities[planet]["dignity"], planet


def test_every_varga_carries_a_dignity_for_every_planet(chart):
    for varga, payload in chart.all_varga_charts().items():
        for planet, row in payload["planets"].items():
            assert row["dignity"], (varga, planet)


# ── Degree and nakshatra inside a varga ─────────────────────────────────────
# Sun is at Cancer 28.62 in D1. 28.62 x 9 = 257.57, so it is 0.57 of the way
# through its 9th navamsha: Pisces 17.57, which is Revati (346.67-360) pada 1.
# The same Sun in D10: 28.62 x 10 = 286.19 -> 0.54 through the 10th part:
# Sagittarius 16.19, Purva Ashadha (253.33-266.67) pada 1.

def test_varga_degree_and_nakshatra_follow_the_planet_into_the_varga(chart):
    sun9 = chart.varga_chart("D9")["planets"]["Sun"]
    assert sun9["nakshatra"] == "Revati" and sun9["nakshatra_pada"] == 1
    assert sun9["degree_in_sign"] == pytest.approx(17.57, abs=0.01)
    sun10 = chart.varga_chart("D10")["planets"]["Sun"]
    assert sun10["nakshatra"] == "Purva Ashadha" and sun10["nakshatra_pada"] == 1
    assert sun10["degree_in_sign"] == pytest.approx(16.19, abs=0.01)


def test_d1_degree_and_nakshatra_are_the_real_position(chart):
    d1 = chart.varga_chart("D1")["planets"]
    for planet, data in chart.positions.items():
        assert d1[planet]["nakshatra"] == nakshatra_of(data["lon"])["name"]
        assert d1[planet]["longitude"] == pytest.approx(data["lon"], abs=1e-4)
    assert chart.varga_chart("D1")["degree_convention"] is None
    assert chart.varga_chart("D9")["degree_convention"]["is_convention_dependent"] is True


@pytest.mark.parametrize("varga", [v for v in VARGA_FUNCTIONS if v not in ("D1", "D30")])
def test_equal_varga_degree_is_degree_times_n_mod_30(varga):
    n = int(varga[1:])
    for i in range(1, 3600):
        lon = i / 10 + 0.0123
        expected = (lon % 30) * n % 30
        got = varga_longitude(varga, lon)
        assert int(got // 30) == VARGA_FUNCTIONS[varga](lon), (varga, lon)
        assert got % 30 == pytest.approx(expected, abs=1e-6), (varga, lon)


@pytest.mark.parametrize("lon, expected", [
    (14.0, 255.0),        # Aries 14: 10-18 part (Sagittarius), halfway -> Sag 15
    (43.0, 333.75),       # Taurus 13: 12-20 part (Pisces), 1/8 in -> Pisces 3.75
    (2.5, 15.0),          # Aries 2.5: 0-5 part (Aries), halfway -> Aries 15
    (59.0, 7 * 30 + 24),  # Taurus 29: 25-30 part (Scorpio), 4/5 in -> Scorpio 24
])
def test_d30_degree_spreads_each_unequal_part_over_the_sign(lon, expected):
    assert varga_longitude("D30", lon) == pytest.approx(expected)


# ── Symbols drawn inside each chart ─────────────────────────────────────────

def _symbols(payload):
    return {p: {a["code"] for a in row["annotations"]} for p, row in payload["planets"].items()}


def test_d1_symbols_are_the_birth_chart_annotations(chart):
    d1 = chart.varga_chart("D1")["planets"]
    for planet, rows in chart.planet_annotations().items():
        assert d1[planet]["annotations"] == rows


def test_exalted_and_debilitated_arrows_are_judged_in_each_varga(chart):
    # Venus is debilitated in D1 (Virgo) but sits in Capricorn in D9; Mercury
    # and Saturn are debilitated in D9 (Pisces, Aries), not in D1.
    d1, d9 = _symbols(chart.varga_chart("D1")), _symbols(chart.varga_chart("D9"))
    assert "debilitated" in d1["Venus"] and "debilitated" not in d9["Venus"]
    assert "debilitated" in d9["Mercury"] and "debilitated" not in d1["Mercury"]
    assert "debilitated" in d9["Saturn"]
    assert "debilitated" in _symbols(chart.varga_chart("D10"))["Moon"]


def test_retrograde_follows_the_planet_and_combust_stays_on_d1(chart):
    d1 = _symbols(chart.varga_chart("D1"))
    assert "combust" in d1["Mercury"]
    for varga in VARGA_FUNCTIONS:
        if varga == "D1":
            continue
        symbols = _symbols(chart.varga_chart(varga))
        assert all("combust" not in codes for codes in symbols.values()), varga
        for planet, data in chart.positions.items():
            assert ("retrograde" in symbols[planet]) == bool(data["retrograde"]), (varga, planet)


def test_every_arrow_matches_that_chart_dignity(chart):
    for varga, payload in chart.all_varga_charts().items():
        for planet, row in payload["planets"].items():
            codes = {a["code"] for a in row["annotations"]}
            assert ("exalted" in codes) == (row["dignity"] == "Exalted"), (varga, planet)
            assert ("debilitated" in codes) == (row["dignity"] == "Debilitated"), (varga, planet)
