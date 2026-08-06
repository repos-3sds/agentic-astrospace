"""Tests for the Nabhasa yogas added under T3.1
(docs/backend_astro_depth_checklist_2026-08-06.md): Ashraya (Rajju/Musala/
Nala), Dala (Mala/Sarpa) and Sankhya (Gola..Dama) groups.
"""
from __future__ import annotations

from astrospace.core.vedic.yogas import (
    _ashraya_yogas,
    _dala_yogas,
    _planet_signs,
    _sankhya_yoga,
    yoga_summary,
)


def _positions(**lons):
    return {planet: {"lon": lon} for planet, lon in lons.items()}


ALL_MOVABLE = _positions(
    Sun=10.0, Moon=100.0, Mars=190.0, Mercury=280.0,
    Jupiter=15.0, Venus=105.0, Saturn=195.0, Rahu=0.0, Ketu=180.0,
)  # signs 0(Aries),3(Cancer),6(Libra),9(Capricorn) -- all movable (s%3==0)

ALL_FIXED = _positions(
    Sun=40.0, Moon=130.0, Mars=220.0, Mercury=310.0,
    Jupiter=45.0, Venus=135.0, Saturn=225.0, Rahu=0.0, Ketu=180.0,
)  # signs 1(Taurus),4(Leo),7(Scorpio),10(Aquarius) -- all fixed (s%3==1)

ALL_DUAL = _positions(
    Sun=70.0, Moon=160.0, Mars=250.0, Mercury=340.0,
    Jupiter=75.0, Venus=165.0, Saturn=255.0, Rahu=0.0, Ketu=180.0,
)  # signs 2(Gemini),5(Virgo),8(Sagittarius),11(Pisces) -- all dual (s%3==2)

MIXED = _positions(
    Sun=15.0, Moon=58.9, Mars=70.0, Mercury=98.0, Jupiter=140.0,
    Venus=192.0, Saturn=273.0, Rahu=185.0, Ketu=5.0,
)


class TestAshrayaYogas:
    def test_all_movable_signs_triggers_rajju(self):
        signs = _planet_signs(ALL_MOVABLE)
        results = {r["rule_id"]: r for r in _ashraya_yogas(signs)}
        assert results["rajju_yoga"]["active"] is True
        assert results["musala_yoga"]["active"] is False
        assert results["nala_yoga"]["active"] is False

    def test_all_fixed_signs_triggers_musala(self):
        signs = _planet_signs(ALL_FIXED)
        results = {r["rule_id"]: r for r in _ashraya_yogas(signs)}
        assert results["musala_yoga"]["active"] is True
        assert results["rajju_yoga"]["active"] is False
        assert results["nala_yoga"]["active"] is False

    def test_all_dual_signs_triggers_nala(self):
        signs = _planet_signs(ALL_DUAL)
        results = {r["rule_id"]: r for r in _ashraya_yogas(signs)}
        assert results["nala_yoga"]["active"] is True
        assert results["rajju_yoga"]["active"] is False
        assert results["musala_yoga"]["active"] is False

    def test_mixed_chart_triggers_none(self):
        signs = _planet_signs(MIXED)
        results = {r["rule_id"]: r for r in _ashraya_yogas(signs)}
        assert not any(r["active"] for r in results.values())

    def test_ashraya_yogas_are_mutually_exclusive(self):
        for positions in (ALL_MOVABLE, ALL_FIXED, ALL_DUAL, MIXED):
            signs = _planet_signs(positions)
            active = [r for r in _ashraya_yogas(signs) if r["active"]]
            assert len(active) <= 1


class TestDalaYogas:
    def test_mala_active_when_benefics_all_in_kendra(self):
        # Lagna Aries(0): kendras are Aries/Cancer/Libra/Capricorn (0,3,6,9).
        positions = _positions(
            Mercury=10.0, Venus=100.0, Jupiter=190.0,  # Aries, Cancer, Libra
            Sun=45.0, Mars=135.0, Saturn=225.0,        # non-kendra signs
        )
        signs = _planet_signs(positions)
        results = {r["rule_id"]: r for r in _dala_yogas(signs, lagna_sign=0)}
        assert results["mala_yoga"]["active"] is True
        assert results["sarpa_yoga"]["active"] is False

    def test_sarpa_active_when_malefics_all_in_kendra(self):
        positions = _positions(
            Sun=10.0, Mars=100.0, Saturn=190.0,        # Aries, Cancer, Libra
            Mercury=45.0, Venus=135.0, Jupiter=225.0,  # non-kendra signs
        )
        signs = _planet_signs(positions)
        results = {r["rule_id"]: r for r in _dala_yogas(signs, lagna_sign=0)}
        assert results["sarpa_yoga"]["active"] is True
        assert results["mala_yoga"]["active"] is False

    def test_neither_active_when_one_planet_breaks_the_pattern(self):
        positions = _positions(
            Mercury=10.0, Venus=100.0, Jupiter=45.0,  # Jupiter NOT in kendra
            Sun=1.0, Mars=1.0, Saturn=1.0,
        )
        signs = _planet_signs(positions)
        results = {r["rule_id"]: r for r in _dala_yogas(signs, lagna_sign=0)}
        assert results["mala_yoga"]["active"] is False


class TestSankhyaYoga:
    def test_one_distinct_sign_is_gola(self):
        positions = _positions(Sun=1.0, Moon=2.0, Mars=3.0, Mercury=4.0,
                               Jupiter=5.0, Venus=6.0, Saturn=7.0)
        signs = _planet_signs(positions)
        result = _sankhya_yoga(signs)
        assert result["rule_id"] == "gola_yoga"
        assert result["active"] is True

    def test_four_distinct_signs_is_kedara(self):
        positions = _positions(Sun=1.0, Moon=2.0, Mars=31.0, Mercury=32.0,
                               Jupiter=61.0, Venus=62.0, Saturn=91.0)
        signs = _planet_signs(positions)
        result = _sankhya_yoga(signs)
        assert result["rule_id"] == "kedara_yoga"
        assert result["active"] is True

    def test_seven_distinct_signs_matches_no_named_tier(self):
        positions = _positions(Sun=1.0, Moon=31.0, Mars=61.0, Mercury=91.0,
                               Jupiter=121.0, Venus=151.0, Saturn=181.0)
        signs = _planet_signs(positions)
        result = _sankhya_yoga(signs)
        assert result["rule_id"] == "sankhya_yoga"
        assert result["active"] is False

    def test_nodes_excluded_from_the_count(self):
        # Rahu/Ketu placed in two extra signs must not change the count.
        positions = _positions(Sun=1.0, Moon=2.0, Mars=3.0, Mercury=4.0,
                               Jupiter=5.0, Venus=6.0, Saturn=7.0,
                               Rahu=200.0, Ketu=20.0)
        signs = _planet_signs(positions)
        result = _sankhya_yoga(signs)
        assert result["rule_id"] == "gola_yoga"


class TestNabhasaInYogaSummary:
    def test_new_rule_ids_appear_in_summary(self):
        out = yoga_summary(MIXED, lagna_lon=10.0)
        found = {y["rule_id"] for y in out["all"]}
        expected = {
            "rajju_yoga", "musala_yoga", "nala_yoga",
            "mala_yoga", "sarpa_yoga",
        }
        assert expected <= found

    def test_every_nabhasa_result_carries_kb_fields(self):
        out = yoga_summary(MIXED, lagna_lon=10.0)
        nabhasa = [y for y in out["all"] if "Nabhasa" in y["category"]]
        assert nabhasa
        for y in nabhasa:
            assert y["classical_name"]
            assert y["source_status"]
