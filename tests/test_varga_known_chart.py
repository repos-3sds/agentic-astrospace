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
