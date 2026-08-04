"""
Vedic engine tests.

Two layers:
1. Formula/boundary tests — pure math from BPHS rules, no ephemeris needed.
2. Real-sky invariants — publicly known facts (sankranti windows, ayanamsha
   magnitude, Chaitra Purnima 2024, lagna==Sun sign at sunrise) that hold
   regardless of which reference chart is later supplied.

Reference-chart golden tests will be added once the user provides a
verified chart (see plan.md — Phase 1 Validation).
"""
import pytest
import swisseph as swe
from datetime import datetime, timezone

from astrospace.core.vedic.vargas import (
    d1, d2, d3, d4, d7, d9, d10, d12, d30, d60, all_vargas, VARGA_FUNCTIONS,
)
from astrospace.core.vedic.ashtakavarga import (
    AV_PLANETS,
    BAV_RULES,
    ekadhipatya_shodhana,
    ashtakavarga,
    shodhya_pinda,
    trikona_shodhana,
)
from astrospace.core.vedic.compatibility import gun_milan
from astrospace.core.vedic.dashas import vimshottari_dasha
from astrospace.core.vedic.doshas import manglik_dosha
from astrospace.core.vedic.transits import gochara_rules, transit_analysis, transit_aspects
from astrospace.core.vedic.gocharam import gocharam_profile
from astrospace.core.vedic.yogas import yoga_summary
from astrospace.core.vedic.nakshatra import nakshatra_of
from astrospace.core.vedic.panchanga import tithi_of, yoga_of, karana_of, vara_of
from astrospace.core.vedic.positions import (
    birth_moment, sidereal_positions, sidereal_lagna, tropical_sun,
    ayanamsha_value, local_sunrise, sunrise_jd, sign_index,
)
from astrospace.core.vedic.strength import (
    avastha_of,
    combustion_status,
    dignity_of,
    panchadha_relation,
    planetary_conditions,
    planetary_war,
    retrograde_modifier,
    shadbala,
)
from astrospace.core.vedic.chart import VedicChart

ARIES, TAURUS, GEMINI, CANCER, LEO, VIRGO = 0, 1, 2, 3, 4, 5
LIBRA, SCORPIO, SAGITTARIUS, CAPRICORN, AQUARIUS, PISCES = 6, 7, 8, 9, 10, 11

DELHI = {"lat": 28.6139, "lng": 77.2090, "tz_str": "Asia/Kolkata"}


# ── Varga formulas (BPHS ch.6) ───────────────────────────────────────────────

class TestVargas:
    def test_d1_identity(self):
        assert d1(0.0) == ARIES
        assert d1(45.0) == TAURUS
        assert d1(359.9) == PISCES

    def test_d2_hora_only_cancer_or_leo(self):
        for lon in [x * 3.7 for x in range(98)]:
            assert d2(lon) in (CANCER, LEO)

    def test_d2_hora_boundaries(self):
        assert d2(5.0) == LEO       # odd sign first half → Sun's hora
        assert d2(20.0) == CANCER   # odd sign second half → Moon's hora
        assert d2(35.0) == CANCER   # even sign first half → Moon's hora
        assert d2(50.0) == LEO      # even sign second half → Sun's hora

    def test_d3_drekkana(self):
        assert d3(5.0) == ARIES          # 1st drekkana: same sign
        assert d3(15.0) == LEO           # 2nd: 5th from Aries
        assert d3(25.0) == SAGITTARIUS   # 3rd: 9th from Aries

    def test_d4_chaturthamsha(self):
        assert d4(3.0) == ARIES      # same
        assert d4(10.0) == CANCER    # 4th
        assert d4(18.0) == LIBRA     # 7th
        assert d4(27.0) == CAPRICORN # 10th

    def test_d7_saptamamsha(self):
        assert d7(1.0) == ARIES      # odd sign: from itself
        assert d7(31.0) == SCORPIO   # even sign: from its 7th

    def test_d9_navamsha_element_starts(self):
        assert d9(1.0) == ARIES        # fire starts Aries
        assert d9(31.0) == CAPRICORN   # earth starts Capricorn
        assert d9(61.0) == LIBRA       # air starts Libra
        assert d9(91.0) == CANCER      # water starts Cancer

    def test_d9_navamsha_progression(self):
        assert d9(3.5) == TAURUS       # 2nd navamsha of Aries
        assert d9(29.9) == SAGITTARIUS # 9th navamsha of Aries

    def test_d9_vargottama_corners(self):
        # movable: first navamsha, fixed: middle, dual: last — all vargottama
        assert d9(1.0) == ARIES          # movable first
        assert d9(30.0 + 14.0) == TAURUS # fixed middle (5th navamsha)
        assert d9(330.0 + 28.0) == PISCES  # dual last

    def test_d10_dashamsha(self):
        assert d10(1.0) == ARIES       # odd: from itself
        assert d10(31.0) == CAPRICORN  # even: from its 9th

    def test_d12_dwadashamsha(self):
        assert d12(1.0) == ARIES
        assert d12(3.0) == TAURUS
        assert d12(29.9) == PISCES

    def test_d30_trimshamsha_odd_sign(self):
        assert d30(3.0) == ARIES
        assert d30(7.0) == AQUARIUS
        assert d30(15.0) == SAGITTARIUS
        assert d30(20.0) == GEMINI
        assert d30(27.0) == LIBRA

    def test_d30_trimshamsha_even_sign(self):
        assert d30(33.0) == TAURUS
        assert d30(38.0) == VIRGO
        assert d30(45.0) == PISCES
        assert d30(52.0) == CAPRICORN
        assert d30(58.0) == SCORPIO

    def test_d60_shashtiamsha(self):
        assert d60(0.2) == ARIES
        assert d60(0.7) == TAURUS       # 2nd half-degree → next sign
        assert d60(29.9) == PISCES      # 60th → 12 signs round 5x → back

    def test_all_vargas_valid_signs(self):
        for lon in [x * 1.37 for x in range(263)]:
            for varga, sign in all_vargas(lon).items():
                assert 0 <= sign <= 11, f"{varga} gave {sign} at lon {lon}"

    def test_all_20_vargas_present(self):
        # 17 from the product plan (D1-D30) + D40, D45, D60 bonus vargas
        assert len(VARGA_FUNCTIONS) == 20


# ── Nakshatra ────────────────────────────────────────────────────────────────

class TestNakshatra:
    def test_first_and_last(self):
        assert nakshatra_of(0.0)["name"] == "Ashwini"
        assert nakshatra_of(0.0)["pada"] == 1
        assert nakshatra_of(359.99)["name"] == "Revati"
        assert nakshatra_of(359.99)["pada"] == 4

    def test_pada_boundaries(self):
        assert nakshatra_of(3.30)["pada"] == 1
        assert nakshatra_of(3.35)["pada"] == 2   # 3°20' = 3.333
        assert nakshatra_of(10.1)["pada"] == 4

    def test_moola_starts_sagittarius(self):
        nak = nakshatra_of(240.0)
        assert nak["name"] == "Moola"
        assert nak["pada"] == 1
        assert nak["lord"] == "Ketu"

    def test_lords_cycle(self):
        assert nakshatra_of(0.0)["lord"] == "Ketu"
        assert nakshatra_of(13.5)["lord"] == "Venus"
        assert nakshatra_of(120.1)["lord"] == "Ketu"  # Magha restarts cycle


# ── Dashas ───────────────────────────────────────────────────────────────────

class TestDashas:
    def test_vimshottari_starts_with_birth_nakshatra_lord(self):
        birth = datetime(2000, 1, 1, tzinfo=timezone.utc)
        d = vimshottari_dasha(0.0, birth, birth)
        assert d["birth_nakshatra"]["name"] == "Ashwini"
        assert d["birth_nakshatra"]["lord"] == "Ketu"
        assert d["birth_nakshatra"]["balance_years"] == 7
        assert d["mahadashas"][0]["lord"] == "Ketu"
        assert d["mahadashas"][1]["lord"] == "Venus"

    def test_vimshottari_balance_is_proportional(self):
        birth = datetime(2000, 1, 1, tzinfo=timezone.utc)
        # Halfway through Ashwini leaves half of Ketu's 7-year mahadasha.
        d = vimshottari_dasha((360 / 27) / 2, birth, birth)
        assert d["birth_nakshatra"]["lord"] == "Ketu"
        assert d["birth_nakshatra"]["balance_years"] == pytest.approx(3.5)

    def test_vimshottari_active_periods_are_nested(self):
        birth = datetime(2000, 1, 1, tzinfo=timezone.utc)
        as_of = datetime(2001, 1, 1, tzinfo=timezone.utc)
        d = vimshottari_dasha(0.0, birth, as_of)
        assert d["current"]["mahadasha"]["lord"] == "Ketu"
        assert d["current"]["antardasha"] is not None
        assert d["current"]["pratyantardasha"] is not None
        assert len(d["mahadashas"][0]["antardashas"][0]["pratyantardashas"]) == 9


# ── Ashtakavarga ─────────────────────────────────────────────────────────────

class TestAshtakavarga:
    def test_trikona_shodhana_subtracts_min_when_all_trines_have_bindus(self):
        scores = [3, 0, 0, 0, 2, 0, 0, 0, 5, 0, 0, 0]
        assert trikona_shodhana(scores) == [1, 0, 0, 0, 0, 0, 0, 0, 3, 0, 0, 0]

    def test_trikona_shodhana_keeps_group_when_any_trine_is_zero(self):
        scores = [3, 0, 0, 0, 0, 0, 0, 0, 5, 0, 0, 0]
        assert trikona_shodhana(scores) == scores

    def test_ekadhipatya_shodhana_no_planets_equal_pair_zeroes_both(self):
        scores = [4, 0, 0, 0, 0, 0, 0, 4, 0, 0, 0, 0]
        assert ekadhipatya_shodhana(scores, set())[:8] == [0, 0, 0, 0, 0, 0, 0, 0]

    def test_ekadhipatya_shodhana_no_planets_unequal_pair_keeps_smaller(self):
        scores = [4, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0]
        assert ekadhipatya_shodhana(scores, set())[0] == 2
        assert ekadhipatya_shodhana(scores, set())[7] == 2

    def test_ekadhipatya_shodhana_one_planet_rules(self):
        assert ekadhipatya_shodhana([2, 0, 0, 0, 0, 0, 0, 5, 0, 0, 0, 0], {0})[7] == 3
        assert ekadhipatya_shodhana([5, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0], {0})[7] == 0

    def test_shodhya_pinda_adds_rashi_and_graha_pinda(self):
        scores = [1] * 12
        graha_signs = {planet: i for i, planet in enumerate(AV_PLANETS)}
        pinda = shodhya_pinda(scores, graha_signs)
        assert pinda["rashi_pinda"] == 96
        assert pinda["graha_pinda"] == 45
        assert pinda["shodhya_pinda"] == 141

    def test_rule_table_standard_totals(self):
        assert {p: sum(len(v) for v in rules.values()) for p, rules in BAV_RULES.items()} == {
            "Sun": 48,
            "Moon": 49,
            "Mars": 39,
            "Mercury": 54,
            "Jupiter": 56,
            "Venus": 52,
            "Saturn": 39,
        }

    def test_sarvashtakavarga_total_is_337(self):
        positions = {
            "Sun": {"lon": 10.0},
            "Moon": {"lon": 45.0},
            "Mars": {"lon": 92.0},
            "Mercury": {"lon": 133.0},
            "Jupiter": {"lon": 188.0},
            "Venus": {"lon": 244.0},
            "Saturn": {"lon": 301.0},
        }
        av = ashtakavarga(positions, 80.0)
        assert av["totals"]["sav"] == 337
        assert sum(sign["sav"] for sign in av["signs"]) == 337
        assert len(av["signs"]) == 12

    def test_ashtakavarga_returns_shodhana_prastara_and_pinda(self):
        positions = {
            "Sun": {"lon": 10.0},
            "Moon": {"lon": 45.0},
            "Mars": {"lon": 92.0},
            "Mercury": {"lon": 133.0},
            "Jupiter": {"lon": 188.0},
            "Venus": {"lon": 244.0},
            "Saturn": {"lon": 301.0},
        }
        av = ashtakavarga(positions, 80.0)

        assert set(av["shodhana"]) == set(AV_PLANETS)
        assert set(av["pinda"]) == set(AV_PLANETS)
        assert set(av["prastara"]) == set(AV_PLANETS)
        assert len(av["pinda_rank"]) == 7
        assert av["pinda_rank"] == sorted(av["pinda_rank"], key=lambda row: row["shodhya_pinda"], reverse=True)

        for planet in AV_PLANETS:
            assert len(av["shodhana"][planet]["trikona"]) == 12
            assert len(av["shodhana"][planet]["ekadhipatya"]) == 12
            assert av["shodhana"][planet]["total_after_trikona"] <= av["totals"]["bav"][planet]
            assert av["shodhana"][planet]["total_after_ekadhipatya"] <= av["shodhana"][planet]["total_after_trikona"]
            assert av["pinda"][planet]["shodhya_pinda"] == (
                av["pinda"][planet]["rashi_pinda"] + av["pinda"][planet]["graha_pinda"]
            )


class TestTransitContext:
    def test_transit_context_contains_natal_and_transit_d1_d9(self):
        chart = VedicChart("Transit", 1990, 1, 1, 12, 0, **DELHI)
        ctx = chart.transit_context()
        assert ctx["natal"]["rashi"]["varga"] == "D1"
        assert ctx["natal"]["navamsha"]["varga"] == "D9"
        assert ctx["transit"]["rashi"]["varga"] == "D1"
        assert ctx["transit"]["navamsha"]["varga"] == "D9"
        assert "Saturn" in ctx["gochara"]
        assert "sade_sati" in ctx

    def test_transit_aspects_detects_close_conjunction(self):
        natal = {"Moon": {"lon": 10.0}}
        transit = {"Saturn": {"lon": 10.5, "speed": 0.1, "retrograde": False}}
        aspects = transit_aspects(natal, transit)
        assert aspects[0]["transit_planet"] == "Saturn"
        assert aspects[0]["natal_planet"] == "Moon"
        assert aspects[0]["aspect"] == "Conjunction"
        assert aspects[0]["strength"] >= 90

    def test_gochara_rules_flags_sade_sati(self):
        positions = {
            "Sun": {"lon": 0.0},
            "Moon": {"lon": 20.0},
            "Mars": {"lon": 40.0},
            "Mercury": {"lon": 60.0},
            "Jupiter": {"lon": 120.0},
            "Venus": {"lon": 80.0},
            "Saturn": {"lon": 330.0},
            "Rahu": {"lon": 180.0},
            "Ketu": {"lon": 0.0},
        }
        result = gochara_rules(positions, positions, ARIES, ARIES)
        assert result["sade_sati"]["active"]
        assert any(rule["name"] == "Sade Sati" for rule in result["active_rules"])
        assert result["core_reading"]["active_rule_count"] >= 1
        assert len(result["core_reading"]["sentences"]) == 4
        assert result["core_reading"]["rationale"]
        assert result["core_reading"]["reading"]
        assert result["core_reading"]["timing_summary"]
        assert all(rule["explanation"].count(".") >= 3 for rule in result["rules"])

    def test_transit_analysis_contains_timeline_and_active_rules(self):
        chart = VedicChart("Transit", 1990, 1, 1, 12, 0, **DELHI)
        result = transit_analysis(
            chart.positions,
            chart.lagna_lon,
            datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc),
            chart.ayanamsha,
            chart.node_type,
        )
        assert result["system"] == "Vedic Gochara / Sidereal Transits"
        assert "planets" in result["gochara"]
        assert "Saturn" in result["gochara"]["planets"]
        assert "timeline" in result["gochara"]
        assert result["gochara"]["core_reading"]["rationale"]
        assert result["gochara"]["core_reading"]["reading"]
        assert result["gochara"]["core_reading"]["next"]["timing_summary"]
        assert result["gochara"]["core_reading"]["previous"]["timing_summary"]
        assert "active_windows" in result["gochara"]["timeline"]
        assert "previous_365_days" in result["gochara"]["timeline"]
        assert "next_365_days" in result["gochara"]["timeline"]
        assert "next_7_days" in result["timeline"]

    def test_gocharam_profile_generates_profile_timeline_readings(self):
        chart = VedicChart("Gocharam", 1990, 1, 1, 12, 0, **DELHI)
        result = gocharam_profile(
            chart.positions,
            chart.lagna_lon,
            datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc),
            chart.ayanamsha,
            chart.node_type,
            past_days=90,
            future_days=90,
        )
        assert result["system"] == "South Indian Gocharam"
        assert result["coverage"]["strategy"].startswith("pre-generated")
        assert result["coverage"]["past_days"] == 90
        assert result["coverage"]["future_days"] == 90
        assert result["gochara"]["timeline"]["scan_days"] == 90
        assert result["gochara"]["core_reading"]["next"]["reading"]
        assert result["gochara"]["core_reading"]["previous"]["reading"]
        assert "90-day scan" in result["gochara"]["core_reading"]["next"]["reading"]
        assert "periods" in result

    def test_gocharam_chart_recalculates_for_selected_date(self):
        chart = VedicChart("Timeline snapshot", 1990, 1, 1, 12, 0, **DELHI)
        selected = datetime(2027, 1, 15, 12, 0, tzinfo=timezone.utc)
        result = chart.gocharam(scan_days=30, as_of=selected)
        assert result["as_of"].startswith("2027-01-15")
        assert result["coverage"]["past_days"] == 30
        assert result["gochara"]["interpretation"]["schema_version"] == "gocharam.interpretation.v3"

    def test_calendar_intelligence_merges_core_signal_families(self):
        chart = VedicChart("Calendar", 1990, 1, 1, 12, 0, **DELHI)
        result = chart.calendar_intelligence(
            as_of=datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc),
            city="Delhi",
            nation="IN",
            **DELHI,
            display_tz_str="Asia/Kolkata",
            days=7,
        )
        assert result["system"] == "AstroSpace Calendar Intelligence"
        assert result["current"]["dasha"]["mahadasha"]
        assert result["current"]["panchanga"]["date"] == "2026-07-14"
        categories = {event["category"] for event in result["events"]}
        assert {"dasha", "panchanga", "transit"} <= categories
        assert "2026-07-14" in result["by_date"]


class TestCompatibility:
    class StubChart:
        def __init__(self, name: str, av: dict, moon_nakshatra: str = "Ashwini", moon_sign: str = "Aries"):
            self.name = name
            self._av = av
            self._moon_nakshatra = moon_nakshatra
            self._moon_sign = moon_sign
            # Arbitrary but valid — these tests assert only on koota rows,
            # never on Manglik/Gandanta, so any real longitude works for
            # gun_milan()'s safety_checks to compute without asserting
            # anything meaningful.
            self.positions = {planet: {"lon": 15.0} for planet in
                               ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")}
            self.lagna_lon = 0.0

        def avkahada(self):
            return self._av

        def planet_details(self):
            return {"Moon": {"nakshatra": self._moon_nakshatra, "sign": self._moon_sign}}

    def _row(self, result: dict, label: str) -> dict:
        return next(row for row in result["rows"] if row["label"] == label)

    def test_gun_milan_returns_eight_kootas_and_bounded_total(self):
        a = VedicChart("A", 1990, 1, 1, 12, 0, **DELHI)
        b = VedicChart("B", 1992, 6, 15, 8, 30, **DELHI)
        result = gun_milan(a, b)

        assert result["system"] == "Ashta Koota / Gun Milan"
        assert result["max"] == 36
        assert 0 <= result["total"] <= 36
        assert 0 <= result["percent"] <= 100
        assert [row["label"] for row in result["rows"]] == [
            "Varna", "Vashya", "Tara", "Yoni",
            "Graha Maitri", "Gana", "Bhakoot", "Nadi",
        ]
        assert sum(row["max"] for row in result["rows"]) == 36
        assert result["profiles"]["person1"]["name"] == "A"
        assert result["profiles"]["person2"]["name"] == "B"
        assert all("verified" in row for row in result["rows"])

    def test_tara_scores_janma_and_parama_mitra_as_favourable(self):
        base = {
            "varna": "Brahmin", "vashya": "Manava", "yoni": "Horse (M)",
            "rashi_lord": "Mars", "gana": "Deva", "nadi": "Aadi",
        }
        janma = gun_milan(
            self.StubChart("A", base, "Ashwini"),
            self.StubChart("B", base, "Ashwini"),
        )
        parama = gun_milan(
            self.StubChart("A", base, "Ashwini"),
            self.StubChart("B", base, "Ashlesha"),
        )
        assert self._row(janma, "Tara")["points"] == 3
        assert self._row(parama, "Tara")["points"] == 3

    def test_yoni_enemy_pair_scores_zero(self):
        a = self.StubChart("A", {
            "varna": "Brahmin", "vashya": "Manava", "yoni": "Serpent (M)",
            "rashi_lord": "Mars", "gana": "Deva", "nadi": "Aadi",
        })
        b = self.StubChart("B", {
            "varna": "Brahmin", "vashya": "Manava", "yoni": "Mongoose (M)",
            "rashi_lord": "Mars", "gana": "Deva", "nadi": "Madhya",
        })
        assert self._row(gun_milan(a, b), "Yoni")["points"] == 0

    def test_gana_manushya_rakshasa_scores_zero(self):
        a = self.StubChart("A", {
            "varna": "Brahmin", "vashya": "Manava", "yoni": "Horse (M)",
            "rashi_lord": "Mars", "gana": "Manushya", "nadi": "Aadi",
        })
        b = self.StubChart("B", {
            "varna": "Brahmin", "vashya": "Manava", "yoni": "Horse (F)",
            "rashi_lord": "Mars", "gana": "Rakshasa", "nadi": "Madhya",
        })
        assert self._row(gun_milan(a, b), "Gana")["points"] == 0

    def test_varna_is_binary_and_graha_maitri_uses_lookup(self):
        a = self.StubChart("A", {
            "varna": "Vaishya", "vashya": "Manava", "yoni": "Horse (M)",
            "rashi_lord": "Sun", "gana": "Deva", "nadi": "Aadi",
        })
        b = self.StubChart("B", {
            "varna": "Brahmin", "vashya": "Manava", "yoni": "Horse (F)",
            "rashi_lord": "Venus", "gana": "Deva", "nadi": "Madhya",
        })
        result = gun_milan(a, b)
        assert self._row(result, "Varna")["points"] == 0
        assert self._row(result, "Graha Maitri")["points"] == 0


class TestDoshas:
    def test_manglik_dosha_checks_lagna_moon_and_venus(self):
        positions = {
            "Mars": {"lon": 0.0},
            "Moon": {"lon": 330.0},
            "Venus": {"lon": 180.0},
        }
        dosha = manglik_dosha(positions, 0.0)
        assert dosha["active"]
        assert dosha["severity"] == "strong"
        assert {row["reference"] for row in dosha["checks"]} == {"Lagna", "Moon", "Venus"}
        assert all(row["active"] for row in dosha["checks"])
        assert dosha["rule_id"] == "manglik_dosha"
        assert dosha["source_status"] == "verified_common"
        assert dosha["source_refs"]

    def test_full_payload_contains_doshas(self):
        chart = VedicChart("Dosha", 1990, 1, 1, 12, 0, **DELHI)
        payload = chart.to_dict()
        assert "doshas" in payload
        assert payload["doshas"]["manglik"]["name"] == "Manglik / Kuja Dosha"


class TestYogas:
    def test_yoga_summary_detects_major_rules(self):
        positions = {
            "Sun": {"lon": 10.0},
            "Moon": {"lon": 40.0},
            "Mars": {"lon": 220.0},
            "Mercury": {"lon": 12.0},
            "Jupiter": {"lon": 130.0},
            "Venus": {"lon": 70.0},
            "Saturn": {"lon": 310.0},
            "Rahu": {"lon": 20.0},
            "Ketu": {"lon": 200.0},
        }
        result = yoga_summary(positions, 0.0)
        active_names = {row["name"] for row in result["active"]}
        assert "Gajakesari Yoga" in active_names
        assert "Budhaditya Yoga" in active_names
        assert result["active_count"] >= 2
        assert result["conventions"]["association"]
        assert result["conventions"]["rules_kb"] == "astrospace/knowledge/vedic_rules"
        assert all(row["rule_id"] for row in result["all"])
        assert all(row["source_status"] in {"verified_common", "convention_dependent", "needs_review"} for row in result["all"])
        assert all(isinstance(row["source_refs"], list) for row in result["all"])

    def test_pancha_mahapurusha_yogas_are_detected_from_kendras(self):
        positions = {
            "Sun": {"lon": 20.0},
            "Moon": {"lon": 50.0},
            "Mars": {"lon": 5.0},       # Aries own sign, 1st from Aries lagna
            "Mercury": {"lon": 75.0},
            "Jupiter": {"lon": 95.0},
            "Venus": {"lon": 145.0},
            "Saturn": {"lon": 185.0},   # Libra exaltation, 7th from Aries lagna
            "Rahu": {"lon": 250.0},
            "Ketu": {"lon": 70.0},
        }
        result = yoga_summary(positions, 0.0)
        active_names = {row["name"] for row in result["active"]}
        assert "Ruchaka Yoga" in active_names
        assert "Sasa Yoga" in active_names
        assert any(row["rule_id"] == "ruchaka_yoga" for row in result["active"])

    def test_raja_yoga_detects_parivartana_exchange(self):
        positions = {
            "Sun": {"lon": 15.0},
            "Moon": {"lon": 45.0},
            "Mars": {"lon": 75.0},
            "Mercury": {"lon": 105.0},
            "Jupiter": {"lon": 275.0},  # Capricorn, ruled by Saturn
            "Venus": {"lon": 145.0},
            "Saturn": {"lon": 245.0},   # Sagittarius, ruled by Jupiter
            "Rahu": {"lon": 20.0},
            "Ketu": {"lon": 200.0},
        }
        result = yoga_summary(positions, 0.0)
        raja = [row for row in result["active"] if row["rule_id"] == "raja_yoga"]
        assert any(set(row["planets"]) == {"Jupiter", "Saturn"} for row in raja)
        assert any("parivartana exchange" in " ".join(row["triggers"]) for row in raja)

    def test_full_payload_contains_yogas(self):
        chart = VedicChart("Yoga", 1990, 1, 1, 12, 0, **DELHI)
        payload = chart.to_dict()
        assert "yogas" in payload
        assert "active_count" in payload["yogas"]
        assert payload["yogas"]["conventions"]["rules_kb"] == "astrospace/knowledge/vedic_rules"


# ── Panchanga ────────────────────────────────────────────────────────────────

class TestPanchanga:
    def test_tithi_shukla_pratipada(self):
        t = tithi_of(10.0, 15.0)
        assert t["index"] == 0
        assert t["name"] == "Pratipada"
        assert t["paksha"] == "Shukla"

    def test_tithi_purnima_and_amavasya(self):
        assert tithi_of(0.0, 175.0)["name"] == "Purnima"
        assert tithi_of(0.0, 355.0)["name"] == "Amavasya"

    def test_tithi_krishna_chaturthi(self):
        t = tithi_of(0.0, 220.0)  # elongation 220° → index 18
        assert t["display"] == "Chaturthi Krishna"

    def test_karana_fixed_and_movable(self):
        assert karana_of(0.0, 3.0)["name"] == "Kimstughna"
        assert karana_of(0.0, 8.0)["name"] == "Bava"
        assert karana_of(0.0, 220.0)["name"] == "Bava"    # first half of K-Chaturthi (karana #37)
        assert karana_of(0.0, 225.0)["name"] == "Balava"  # second half of K-Chaturthi (karana #38)
        assert karana_of(0.0, 344.0)["name"] == "Shakuni"
        assert karana_of(0.0, 359.0)["name"] == "Naga"

    def test_yoga(self):
        assert yoga_of(0.0, 5.0)["name"] == "Vishkambha"
        assert yoga_of(180.0, 76.7)["name"] == "Shiva"  # sum 256.7 → idx 19

    def test_vara_before_sunrise_is_previous_day(self):
        # 2024-04-25 was a Thursday; 04:00 IST is before Delhi sunrise (~05:50)
        m = birth_moment(2024, 4, 25, 4, 0, **DELHI)
        assert vara_of(m)["name"] == "Wednesday"
        m2 = birth_moment(2024, 4, 25, 9, 0, **DELHI)
        assert vara_of(m2)["name"] == "Thursday"


# ── Real-sky invariants (Swiss Ephemeris) ────────────────────────────────────

class TestRealSky:
    def test_lahiri_ayanamsha_magnitude_2024(self):
        jd = swe.julday(2024, 1, 1, 0.0)
        assert 23.9 < ayanamsha_value(jd) < 24.4

    def test_sidereal_sun_solar_months(self):
        # Mesha sankranti ~Apr 14, Simha ~Aug 17, Makara ~Jan 15
        jd = swe.julday(2024, 4, 25, 12.0)
        assert sign_index(sidereal_positions(jd)["Sun"]["lon"]) == ARIES
        jd = swe.julday(2024, 1, 20, 12.0)
        assert sign_index(sidereal_positions(jd)["Sun"]["lon"]) == CAPRICORN
        jd = swe.julday(2024, 8, 25, 12.0)
        assert sign_index(sidereal_positions(jd)["Sun"]["lon"]) == LEO

    def test_tropical_sun_after_equinox(self):
        jd = swe.julday(2024, 3, 25, 12.0)
        assert sign_index(tropical_sun(jd)) == ARIES

    def test_chaitra_purnima_2024(self):
        # 2024-04-23 (Hanuman Jayanti) — full moon at 23:49 UT
        jd = swe.julday(2024, 4, 23, 12.0)
        pos = sidereal_positions(jd)
        t = tithi_of(pos["Sun"]["lon"], pos["Moon"]["lon"])
        assert t["name"] == "Purnima"

    def test_rahu_ketu_opposition(self):
        jd = swe.julday(2024, 6, 1, 0.0)
        pos = sidereal_positions(jd)
        diff = (pos["Ketu"]["lon"] - pos["Rahu"]["lon"]) % 360.0
        assert abs(diff - 180.0) < 1e-9

    def test_delhi_sunrise_plausible(self):
        m = birth_moment(2024, 6, 21, 12, 0, **DELHI)
        sr = local_sunrise(m)
        assert sr is not None
        assert 4 <= sr.hour <= 6

    def test_lagna_at_sunrise_equals_sun_sign(self):
        # The rising sign at sunrise is the Sun's sign (mid-month, away
        # from sankranti, so no boundary ambiguity).
        m = birth_moment(2024, 4, 25, 6, 0, **DELHI)
        jd_rise = sunrise_jd(m.jd_ut - 0.5, m.lat, m.lng)
        assert jd_rise is not None
        jd_check = jd_rise + 5.0 / 1440.0
        lagna = sidereal_lagna(jd_check, m.lat, m.lng)
        sun = sidereal_positions(jd_check)["Sun"]["lon"]
        assert sign_index(lagna) == sign_index(sun) == ARIES


# ── Dignity ──────────────────────────────────────────────────────────────────

def _positions_stub(**overrides):
    base = {p: {"lon": 15.0} for p in
            ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]}
    for k, v in overrides.items():
        base[k] = {"lon": v}
    return base


class TestDignity:
    def test_exaltation_and_debilitation(self):
        pos = _positions_stub(Sun=10.0)
        assert dignity_of("Sun", 10.0, pos)["dignity"] == "Exalted"
        pos = _positions_stub(Sun=190.0)
        assert dignity_of("Sun", 190.0, pos)["dignity"] == "Debilitated"

    def test_moolatrikona_vs_own(self):
        pos = _positions_stub(Sun=130.0)
        assert dignity_of("Sun", 130.0, pos)["dignity"] == "Moolatrikona"  # Leo 10°
        pos = _positions_stub(Sun=145.0)
        assert dignity_of("Sun", 145.0, pos)["dignity"] == "Own"           # Leo 25°

    def test_panchadha_combination(self):
        # natural friend + temporal friend = Great Friend
        assert panchadha_relation("Sun", 0, "Jupiter", 1) == "Great Friend"
        # natural friend + temporal enemy (same sign) = Neutral
        assert panchadha_relation("Sun", 0, "Jupiter", 0) == "Neutral"
        # natural enemy + temporal enemy = Great Enemy
        assert panchadha_relation("Sun", 0, "Venus", 0) == "Great Enemy"

    def test_nodes_are_neutral_flagged(self):
        pos = _positions_stub()
        d = dignity_of("Rahu", 45.0, pos)
        assert d["dignity"] == "Neutral"
        assert "note" in d


class TestShadbala:
    def test_shadbala_returns_six_components_for_visible_grahas(self):
        positions = {
            "Sun": {"lon": 10.0, "speed": 1.0, "retrograde": False},
            "Moon": {"lon": 80.0, "speed": 12.0, "retrograde": False},
            "Mars": {"lon": 220.0, "speed": 0.4, "retrograde": False},
            "Mercury": {"lon": 165.0, "speed": 1.2, "retrograde": False},
            "Jupiter": {"lon": 95.0, "speed": 0.08, "retrograde": False},
            "Venus": {"lon": 355.0, "speed": 1.0, "retrograde": False},
            "Saturn": {"lon": 190.0, "speed": -0.03, "retrograde": True},
            "Rahu": {"lon": 340.0, "speed": -0.05, "retrograde": True},
            "Ketu": {"lon": 160.0, "speed": -0.05, "retrograde": True},
        }
        result = shadbala(positions, 0.0)
        assert result["system"] == "Shadbala v1"
        assert set(result["rows"]) == {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"}
        assert "Rahu" in result["excluded"]
        for row in result["rows"].values():
            assert 0 <= row["total_score"] <= 100
            assert set(row["components"]) == {
                "sthana_bala",
                "dig_bala",
                "kala_bala",
                "cheshta_bala",
                "naisargika_bala",
                "drik_bala",
            }
            assert all(0 <= component["score"] <= 100 for component in row["components"].values())
            assert "base_score" in row
            assert "condition_modifier" in row
            assert "conditions" in row

    def test_shadbala_marks_approximation_components(self):
        chart = VedicChart("Strength", 1990, 1, 1, 12, 0, **DELHI)
        payload = chart.shadbala()
        statuses = {item["component"]: item["status"] for item in payload["provenance"]}
        assert statuses["sthana_bala"] == "implemented"
        assert statuses["dig_bala"] == "implemented"
        assert statuses["kala_bala"] == "approximation"
        assert payload["ranking"] == sorted(payload["ranking"], key=lambda row: row["score"], reverse=True)


class TestPlanetaryConditions:
    def test_combustion_flags_close_planet_to_sun(self):
        positions = _positions_stub(Sun=10.0, Mercury=12.0)
        status = combustion_status("Mercury", positions)
        assert status["active"]
        assert status["severity"] == "severe"
        assert status["modifier"] < 0

    def test_avastha_reverses_for_even_signs(self):
        assert avastha_of(2.0)["name"] == "Bala"
        assert avastha_of(32.0)["name"] == "Mrita"
        assert avastha_of(14.0)["name"] == "Yuva"

    def test_retrograde_modifier_applies_to_visible_grahas(self):
        row = retrograde_modifier("Saturn", {"speed": -0.02, "retrograde": True})
        assert row["active"]
        assert row["modifier"] > 0
        assert retrograde_modifier("Sun", {"speed": 1.0, "retrograde": False})["status"] == "not_applicable"

    def test_planetary_war_detects_same_sign_close_longitudes(self):
        positions = {
            "Mars": {"lon": 10.0, "speed": 0.4},
            "Mercury": {"lon": 10.5, "speed": 1.1},
            "Jupiter": {"lon": 95.0, "speed": 0.08},
            "Venus": {"lon": 180.0, "speed": 1.0},
            "Saturn": {"lon": 250.0, "speed": 0.04},
        }
        war = planetary_war(positions)
        assert war["Mercury"]["active"]
        assert war["Mercury"]["role"] == "winner"
        assert war["Mars"]["role"] == "loser"

    def test_planetary_conditions_returns_all_sections(self):
        positions = {
            "Sun": {"lon": 10.0, "speed": 1.0, "retrograde": False},
            "Moon": {"lon": 80.0, "speed": 12.0, "retrograde": False},
            "Mars": {"lon": 10.4, "speed": 0.4, "retrograde": False},
            "Mercury": {"lon": 10.6, "speed": 1.2, "retrograde": False},
            "Jupiter": {"lon": 95.0, "speed": 0.08, "retrograde": False},
            "Venus": {"lon": 355.0, "speed": 1.0, "retrograde": False},
            "Saturn": {"lon": 190.0, "speed": -0.03, "retrograde": True},
            "Rahu": {"lon": 340.0, "speed": -0.05, "retrograde": True},
            "Ketu": {"lon": 160.0, "speed": -0.05, "retrograde": True},
        }
        conditions = planetary_conditions(positions)
        assert conditions["system"] == "Planetary Conditions v1"
        assert "combustion" in conditions["rows"]["Mars"]
        assert "avastha" in conditions["rows"]["Mars"]
        assert "planetary_war" in conditions["rows"]["Mars"]
        assert conditions["rows"]["Saturn"]["retrograde"]["active"]


# ── Full chart smoke test ────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def chart():
    return VedicChart("Test Person", 1990, 3, 15, 8, 30,
                      city="Delhi", nation="IN")


class TestVedicChart:

    def test_payload_sections(self, chart):
        d = chart.to_dict()
        for key in ["meta", "lagna", "planets", "panchanga", "avkahada",
                    "ghatak", "favourable", "dignities", "planetary_conditions", "shadbala", "vargas"]:
            assert key in d, f"missing section {key}"

    def test_nine_grahas(self, chart):
        assert set(chart.planet_details().keys()) == {
            "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu",
        }

    def test_houses_valid(self, chart):
        for p, det in chart.planet_details().items():
            assert 1 <= det["house"] <= 12

    def test_all_vargas_have_lagna_and_planets(self, chart):
        vargas = chart.all_varga_charts()
        assert len(vargas) == 20
        for v, data in vargas.items():
            assert 0 <= data["lagna"]["sign_index"] <= 11
            assert len(data["planets"]) == 9

    def test_avkahada_complete(self, chart):
        avk = chart.avkahada()
        for field in ["lagna", "lagna_lord", "rashi", "rashi_lord", "nakshatra",
                      "nakshatra_lord", "charan", "tithi", "paya", "yoga", "karana",
                      "varna", "tatwa", "vashya", "yoni", "gana", "nadi",
                      "first_letters", "sun_sign_western", "decanate"]:
            assert avk.get(field) not in (None, ""), f"empty avkahada field {field}"

    def test_ayanamsha_reported(self, chart):
        meta = chart.meta()
        assert 23.0 < meta["ayanamsha"]["value"] < 25.0

    def test_moon_sign_consistency(self, chart):
        # Avkahada rashi must equal the Moon's D1 sign
        avk = chart.avkahada()
        moon = chart.planet_details()["Moon"]
        assert avk["rashi"] == moon["sign"]
