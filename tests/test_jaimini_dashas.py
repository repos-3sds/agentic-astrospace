"""Tests for Jaimini karakas/arudhas, special lagnas, Yogini dasha and
the sookshma/prana extension of Vimshottari."""
from datetime import datetime, timedelta

import pytest

from astrospace.core.vedic.constants import NAKSHATRA_SPAN
from astrospace.core.vedic.dashas import vimshottari_dasha
from astrospace.core.vedic.jaimini import (
    arudha_lagna,
    arudha_pada,
    arudha_pada_detail,
    arudha_padas,
    chara_karakas,
    upapada,
)
from astrospace.core.vedic.special_lagnas import special_lagnas
from astrospace.core.vedic.yogini import CYCLE_YEARS, YOGINIS, yogini_dasha


def _positions(**lons):
    return {planet: {"lon": lon} for planet, lon in lons.items()}


# Synthetic chart with known degrees-in-sign:
# Moon 28.9 > Rahu eff 25.0 > Jupiter 20.0 > Sun 15.0 > Venus 12.0
# > Mars 10.0 > Mercury 8.0 > Saturn 3.0
CHART = _positions(
    Sun=15.0,        # Aries 15°
    Moon=58.9,       # Taurus 28.9°
    Mars=70.0,       # Gemini 10°
    Mercury=98.0,    # Cancer 8°
    Jupiter=140.0,   # Leo 20°
    Venus=192.0,     # Libra 12°
    Saturn=273.0,    # Capricorn 3°
    Rahu=185.0,      # Libra 5° -> effective 25°
    Ketu=5.0,
)


class TestCharaKarakas:
    def test_eight_scheme_assignments(self):
        k = chara_karakas(CHART, scheme="eight")["karakas"]
        assert k["AK"]["planet"] == "Moon"
        assert k["AmK"]["planet"] == "Rahu"
        assert k["BK"]["planet"] == "Jupiter"
        assert k["MK"]["planet"] == "Sun"
        assert k["PK"]["planet"] == "Venus"
        assert k["PiK"]["planet"] == "Mars"
        assert k["GK"]["planet"] == "Mercury"
        assert k["DK"]["planet"] == "Saturn"

    def test_rahu_degree_reversal(self):
        k = chara_karakas(CHART, scheme="eight")["karakas"]
        assert k["AmK"]["degree_in_sign"] == pytest.approx(5.0)
        assert k["AmK"]["effective_degree"] == pytest.approx(25.0)
        # Non-node planets keep their real degree.
        assert k["AK"]["effective_degree"] == pytest.approx(28.9)

    def test_seven_scheme_excludes_rahu_and_pik(self):
        result = chara_karakas(CHART, scheme="seven")
        k = result["karakas"]
        assert "PiK" not in k
        assert all(row["planet"] != "Rahu" for row in k.values())
        # Without Rahu everything below AK shifts up one slot.
        assert k["AK"]["planet"] == "Moon"
        assert k["AmK"]["planet"] == "Jupiter"
        assert k["BK"]["planet"] == "Sun"
        assert k["MK"]["planet"] == "Venus"
        assert k["PK"]["planet"] == "Mars"
        assert k["GK"]["planet"] == "Mercury"
        assert k["DK"]["planet"] == "Saturn"
        assert len(result["ordered"]) == 7

    def test_ordered_list_and_notes(self):
        result = chara_karakas(CHART, scheme="eight")
        assert [row["code"] for row in result["ordered"]] == [
            "AK", "AmK", "BK", "MK", "PK", "PiK", "GK", "DK",
        ]
        assert result["notes"]

    def test_arcsecond_tie_is_noted(self):
        chart = dict(CHART)
        chart["Jupiter"] = {"lon": 148.9}  # Leo 28.9° — ties the Moon exactly
        notes = chara_karakas(chart, scheme="eight")["notes"]
        assert any("Tie" in n for n in notes)

    def test_bad_scheme_raises(self):
        with pytest.raises(ValueError):
            chara_karakas(CHART, scheme="nine")


class TestArudhaPada:
    def test_worked_example_lord_in_tenth(self):
        # Aries lagna, house 1 lord Mars in Capricorn (10th sign): n = 9,
        # counting 9 further lands on Libra ((9 + 9) % 12 = 6) — the 7th
        # from Aries, so the BPHS exception moves it 10 signs on to Cancer.
        positions = _positions(Mars=275.0)  # Capricorn 5°
        detail = arudha_pada_detail(1, 0, positions)
        assert detail["count"] == 9
        assert detail["raw_sign"] == 6          # Libra, as far from Mars as Mars from Aries
        assert detail["exception_applied"] is True
        assert detail["sign"] == 3              # 10th from Libra = Cancer
        assert detail["sign_name"] == "Cancer"
        assert arudha_pada(1, 0, positions) == 3

    def test_no_exception_case(self):
        # Aries lagna, Mars in Gemini (3rd): n = 2, arudha = 3rd from Gemini = Leo.
        positions = _positions(Mars=70.0)
        detail = arudha_pada_detail(1, 0, positions)
        assert detail["count"] == 2
        assert detail["exception_applied"] is False
        assert detail["sign"] == 4
        assert detail["sign_name"] == "Leo"

    def test_exception_lord_in_own_house(self):
        # Lord in the house itself: arudha would be the house — take the 10th.
        positions = _positions(Mars=10.0)  # Aries
        detail = arudha_pada_detail(1, 0, positions)
        assert detail["count"] == 0
        assert detail["raw_sign"] == 0
        assert detail["exception_applied"] is True
        assert detail["sign"] == 9  # Capricorn, 10th from Aries

    def test_exception_lord_in_seventh(self):
        # Lord in the 7th: the count returns to the house itself — same exception.
        positions = _positions(Mars=190.0)  # Libra
        detail = arudha_pada_detail(1, 0, positions)
        assert detail["count"] == 6
        assert detail["raw_sign"] == 0
        assert detail["exception_applied"] is True
        assert detail["sign"] == 9

    def test_arudha_lagna_and_upapada_helpers(self):
        positions = _positions(
            Sun=130.0, Moon=100.0, Mars=70.0, Mercury=160.0,
            Jupiter=250.0, Venus=20.0, Saturn=300.0,
        )
        al = arudha_lagna(0, positions)
        assert al["house"] == 1
        assert al == arudha_pada_detail(1, 0, positions)
        ul = upapada(0, positions)
        assert ul["house"] == 12
        # A12 house sign from Aries lagna is Pisces, lord Jupiter.
        assert ul["lord"] == "Jupiter"

    def test_all_padas(self):
        positions = _positions(
            Sun=130.0, Moon=100.0, Mars=70.0, Mercury=160.0,
            Jupiter=250.0, Venus=20.0, Saturn=300.0,
        )
        out = arudha_padas(0, positions)
        assert set(out["padas"]) == {f"A{h}" for h in range(1, 13)}
        assert out["arudha_lagna"] == out["padas"]["A1"]
        assert out["upapada"] == out["padas"]["A12"]
        for row in out["padas"].values():
            assert 0 <= row["sign"] <= 11
            # Exception guarantee: never the house itself nor the 7th from it.
            assert row["sign"] != row["house_sign"]
            assert row["sign"] != (row["house_sign"] + 6) % 12


class TestSpecialLagnas:
    SUNRISE_JD = 2451545.25
    SUN_LON = 100.0

    def test_at_sunrise_all_equal_sun(self):
        out = special_lagnas(self.SUNRISE_JD, self.SUNRISE_JD, self.SUN_LON)
        for key in ("bhava_lagna", "hora_lagna", "ghati_lagna"):
            assert out[key]["longitude"] == pytest.approx(self.SUN_LON)

    def test_two_hours_after_sunrise(self):
        out = special_lagnas(self.SUNRISE_JD + 2.0 / 24.0, self.SUNRISE_JD, self.SUN_LON)
        assert out["hours_since_sunrise"] == pytest.approx(2.0)
        assert out["ghatis_since_sunrise"] == pytest.approx(5.0)
        assert out["bhava_lagna"]["longitude"] == pytest.approx(130.0)  # +30°
        assert out["hora_lagna"]["longitude"] == pytest.approx(160.0)   # +60°
        assert out["ghati_lagna"]["longitude"] == pytest.approx(250.0)  # +150°

    def test_wraps_and_names(self):
        out = special_lagnas(self.SUNRISE_JD + 6.0 / 24.0, self.SUNRISE_JD, 350.0)
        # Ghati lagna: 350 + 450 = 800 -> 80° Gemini.
        gl = out["ghati_lagna"]
        assert gl["longitude"] == pytest.approx(80.0)
        assert gl["sign"] == 2
        assert gl["sign_name"] == "Gemini"
        assert "dms" in gl


class TestYoginiDasha:
    BIRTH = datetime(1990, 1, 1)

    def test_yogini_table(self):
        assert [(y[0], y[1], y[2]) for y in YOGINIS] == [
            ("Mangala", "Moon", 1), ("Pingala", "Sun", 2), ("Dhanya", "Jupiter", 3),
            ("Bhramari", "Mars", 4), ("Bhadrika", "Mercury", 5), ("Ulka", "Saturn", 6),
            ("Siddha", "Venus", 7), ("Sankata", "Rahu", 8),
        ]
        assert sum(y[2] for y in YOGINIS) == CYCLE_YEARS == 36

    def test_starting_yogini_from_ashwini(self):
        # Ashwini (1): (1 + 3) % 8 = 4 -> Bhramari (Mars).
        d = yogini_dasha(0.0, self.BIRTH)
        assert d["birth_nakshatra"]["name"] == "Ashwini"
        assert d["birth_nakshatra"]["starting_yogini"] == "Bhramari"
        assert d["mahadashas"][0]["yogini"] == "Bhramari"
        assert d["mahadashas"][0]["planet"] == "Mars"
        # Moon at 0° Ashwini: nothing traversed, full 4-year balance.
        assert d["birth_nakshatra"]["balance_years"] == pytest.approx(4.0)

    def test_balance_proportional_to_untraversed_fraction(self):
        # Halfway through Ashwini leaves half of Bhramari's 4 years.
        d = yogini_dasha(NAKSHATRA_SPAN / 2.0, self.BIRTH)
        assert d["birth_nakshatra"]["balance_years"] == pytest.approx(2.0)
        assert d["mahadashas"][0]["years"] == pytest.approx(2.0)

    def test_cycle_sums_to_36_years(self):
        d = yogini_dasha(0.0, self.BIRTH)
        # Full balance at birth, so the first 8 mahadashas are one whole cycle.
        first_cycle = d["mahadashas"][:8]
        assert sum(p["years"] for p in first_cycle) == pytest.approx(36.0)
        # Cycle order from Bhramari onward.
        assert [p["yogini"] for p in first_cycle] == [
            "Bhramari", "Bhadrika", "Ulka", "Siddha", "Sankata",
            "Mangala", "Pingala", "Dhanya",
        ]

    def test_antardashas_structure(self):
        d = yogini_dasha(0.0, self.BIRTH)
        md = d["mahadashas"][1]  # Bhadrika, 5 years
        ads = md["antardashas"]
        assert len(ads) == 8
        assert ads[0]["yogini"] == md["yogini"]  # starts from its own yogini
        assert sum(p["years"] for p in ads) == pytest.approx(md["years"])
        assert ads[1]["yogini"] == "Ulka"  # cycle order continues
        assert all("planet" in p and "lord" in p for p in ads)

    def test_active_flags_nest(self):
        as_of = self.BIRTH + timedelta(days=int(10 * 365.25))
        d = yogini_dasha(0.0, self.BIRTH, as_of)
        md = d["current"]["mahadasha"]
        ad = d["current"]["antardasha"]
        assert md is not None and md["active"]
        assert ad is not None and ad["active"]
        assert md["start"] <= as_of.isoformat() < md["end"]
        assert ad["start"] <= as_of.isoformat() < ad["end"]
        # Exactly one active mahadasha, one active antardasha within it.
        assert sum(p["active"] for p in d["mahadashas"]) == 1
        assert sum(p["active"] for p in md["antardashas"]) == 1


class TestVimshottariDepth:
    BIRTH = datetime(1990, 1, 1, 12, 0)
    AS_OF = datetime(2020, 6, 1)

    def test_current_block_has_all_levels(self):
        d = vimshottari_dasha(0.0, self.BIRTH, self.AS_OF)
        cur = d["current"]
        # Existing keys unchanged.
        for key in ("mahadasha", "antardasha", "pratyantardashas", "pratyantardasha"):
            assert key in cur
        # New 4th/5th levels.
        for key in ("sookshmadashas", "sookshmadasha", "pranadashas", "pranadasha"):
            assert key in cur
        assert cur["sookshmadasha"] is not None
        assert cur["pranadasha"] is not None

    def test_active_intervals_contain_as_of(self):
        cur = vimshottari_dasha(0.0, self.BIRTH, self.AS_OF)["current"]
        iso = self.AS_OF.isoformat()
        for level in ("mahadasha", "antardasha", "pratyantardasha",
                      "sookshmadasha", "pranadasha"):
            p = cur[level]
            assert p["start"] <= iso < p["end"], level

    def test_chain_lords_consistent(self):
        cur = vimshottari_dasha(0.0, self.BIRTH, self.AS_OF)["current"]
        # Each level's sequence starts from its parent's lord.
        assert cur["sookshmadashas"][0]["lord"] == cur["pratyantardasha"]["lord"]
        assert cur["pranadashas"][0]["lord"] == cur["sookshmadasha"]["lord"]
        assert len(cur["sookshmadashas"]) == 9
        assert len(cur["pranadashas"]) == 9
        # Sub-periods partition the parent period.
        assert sum(p["years"] for p in cur["sookshmadashas"]) == pytest.approx(
            cur["pratyantardasha"]["years"], rel=1e-4)
        assert sum(p["years"] for p in cur["pranadashas"]) == pytest.approx(
            cur["sookshmadasha"]["years"], rel=1e-4)
        assert cur["sookshmadashas"][0]["start"] == cur["pratyantardasha"]["start"]
        assert cur["pranadashas"][0]["start"] == cur["sookshmadasha"]["start"]

    def test_without_as_of_new_keys_empty(self):
        cur = vimshottari_dasha(0.0, self.BIRTH)["current"]
        assert cur["sookshmadashas"] == []
        assert cur["sookshmadasha"] is None
        assert cur["pranadashas"] == []
        assert cur["pranadasha"] is None

    def test_tree_depth_unchanged_below_active_chain(self):
        # Pratyantardashas remain attached everywhere; sookshma only in current.
        d = vimshottari_dasha(0.0, self.BIRTH, self.AS_OF)
        ad = d["mahadashas"][0]["antardashas"][0]
        assert "pratyantardashas" in ad
        assert all("sookshmadashas" not in p for p in ad["pratyantardashas"])
