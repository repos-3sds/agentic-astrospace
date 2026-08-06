"""Tests for Jaimini Chara Dasha (T1.2, backend_astro_depth_checklist_2026-08-06.md).

Worked examples cross-checked against secondary published sources (see the
module docstring in chara_dasha.py for citations searched): an Aries dasha
under a direct-direction chart with Mars in the 5th house counts to 4
years; a Leo dasha under a reverse-direction chart with the Sun (Leo's own
lord) in Leo gets the full 12 years.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from astrospace.core.vedic.chara_dasha import (
    APASAVYA_SIGNS,
    SAVYA_SIGNS,
    chara_dasha,
    chart_direction,
    sign_duration_years,
)


def _positions(**lons):
    return {planet: {"lon": lon} for planet, lon in lons.items()}


class TestSignGroups:
    def test_savya_apasavya_partition_all_signs(self):
        assert SAVYA_SIGNS | APASAVYA_SIGNS == set(range(12))
        assert SAVYA_SIGNS & APASAVYA_SIGNS == set()

    def test_savya_signs_are_aries_taurus_gemini_libra_scorpio_sagittarius(self):
        assert SAVYA_SIGNS == {0, 1, 2, 6, 7, 8}


class TestChartDirection:
    def test_aries_lagna_is_direct(self):
        # 9th from Aries(0) = Sagittarius(8), a Savya sign.
        assert chart_direction(0) == "direct"

    def test_cancer_lagna_is_reverse(self):
        # 9th from Cancer(3) = Pisces(11), an Apasavya sign.
        assert chart_direction(3) == "reverse"


class TestSignDurationYears:
    def test_aries_direct_mars_in_fifth_house_is_four_years(self):
        """Worked example: Aries dasha (direct), Mars in 5th (Leo) -> count
        5, duration 5-1 = 4 years."""
        positions = _positions(Mars=130.0)  # Leo — 5th from Aries
        assert sign_duration_years(0, positions, "direct") == 4

    def test_leo_reverse_lord_in_own_sign_is_twelve_years(self):
        """Worked example: Leo dasha (indirect/reverse), Sun (Leo's lord) in
        Leo itself -> count 1 -> full 12 years, not 1-1=0."""
        positions = _positions(Sun=125.0)  # Leo — Leo's own lord in Leo
        assert sign_duration_years(4, positions, "reverse") == 12

    def test_duration_bounded_one_to_twelve(self):
        # Sweep every dispositor placement for Aries (Mars) under direct.
        for lord_sign in range(12):
            positions = _positions(Mars=lord_sign * 30.0 + 10.0)
            years = sign_duration_years(0, positions, "direct")
            assert 1 <= years <= 12


class TestCharaDasha:
    BIRTH = datetime(1990, 1, 1, 12, 0)
    # Aries lagna (direct), a spread of planets so every sign has a lord
    # placement to count against.
    POSITIONS = _positions(
        Sun=15.0, Moon=45.0, Mars=130.0, Mercury=190.0, Jupiter=250.0,
        Venus=310.0, Saturn=100.0, Rahu=70.0, Ketu=250.0,
    )

    def test_sequence_starts_at_lagna_and_covers_all_signs(self):
        out = chara_dasha(0, self.POSITIONS, self.BIRTH)
        signs = [m["sign"] for m in out["mahadashas"]]
        assert signs[0] == 0
        assert len(signs) == 12
        assert set(signs) == set(range(12))

    def test_direct_sequence_is_zodiacal_order(self):
        out = chara_dasha(0, self.POSITIONS, self.BIRTH)
        assert out["direction"] == "direct"
        assert [m["sign"] for m in out["mahadashas"]] == list(range(12))

    def test_reverse_sequence_is_anti_zodiacal(self):
        out = chara_dasha(3, self.POSITIONS, self.BIRTH)  # Cancer lagna
        assert out["direction"] == "reverse"
        signs = [m["sign"] for m in out["mahadashas"]]
        assert signs[0] == 3
        assert signs[1] == 2  # counts backward

    def test_mahadashas_are_contiguous(self):
        out = chara_dasha(0, self.POSITIONS, self.BIRTH)
        for a, b in zip(out["mahadashas"], out["mahadashas"][1:]):
            assert a["end"] == b["start"]

    def test_total_years_matches_sum_of_mahadashas(self):
        out = chara_dasha(0, self.POSITIONS, self.BIRTH)
        assert out["total_years"] == pytest.approx(sum(m["years"] for m in out["mahadashas"]))

    def test_antardashas_sum_to_mahadasha_years_and_start_on_own_sign(self):
        out = chara_dasha(0, self.POSITIONS, self.BIRTH)
        for md in out["mahadashas"]:
            ads = md["antardashas"]
            assert len(ads) == 12
            assert ads[0]["sign"] == md["sign"]
            assert sum(a["years"] for a in ads) == pytest.approx(md["years"], rel=1e-4)

    def test_current_block_active_when_as_of_supplied(self):
        as_of = self.BIRTH + timedelta(days=365 * 3)
        out = chara_dasha(0, self.POSITIONS, self.BIRTH, as_of=as_of)
        md = out["current"]["mahadasha"]
        assert md is not None and md["active"]
        assert md["start"] <= as_of.isoformat() < md["end"]
        ad = out["current"]["antardasha"]
        assert ad is not None and ad["active"]
        assert sum(m["active"] for m in out["mahadashas"]) == 1

    def test_current_block_empty_without_as_of(self):
        out = chara_dasha(0, self.POSITIONS, self.BIRTH)
        assert out["current"]["mahadasha"] is None
        assert out["current"]["antardasha"] is None

    def test_scorpio_and_aquarius_use_primary_lord_convention(self):
        out = chara_dasha(0, self.POSITIONS, self.BIRTH)
        by_sign = {m["sign"]: m for m in out["mahadashas"]}
        assert by_sign[7]["lord"] == "Mars"     # Scorpio
        assert by_sign[10]["lord"] == "Saturn"  # Aquarius
