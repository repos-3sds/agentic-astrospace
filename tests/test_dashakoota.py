"""Tests for the Dashakoota extension (T3.2,
docs/backend_astro_depth_checklist_2026-08-06.md): Rajju, Vedha, Stree
Deergha kootas, returned as a block separate from gun_milan()'s 36-point
Ashtakoota total.
"""
from __future__ import annotations

import pytest

from astrospace.core.vedic.compatibility import (
    RAJJU_GROUPS,
    STREE_DEERGHA_MIN_COUNT,
    VEDHA_PAIRS,
    dashakoota_extension,
    gun_milan,
)
from astrospace.core.vedic.constants import NAKSHATRAS


class StubChart:
    """Minimal chart stub — dashakoota_extension only reads Moon nakshatra."""

    def __init__(self, name: str, moon_nakshatra: str):
        self.name = name
        self._moon_nakshatra = moon_nakshatra
        self.positions = {planet: {"lon": 15.0} for planet in
                           ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")}
        self.lagna_lon = 0.0

    def avkahada(self):
        return {"varna": "Brahmin", "vashya": "Manava", "yoni": "Horse (M)",
                "rashi_lord": "Mars", "gana": "Deva", "nadi": "Aadi"}

    def planet_details(self):
        return {"Moon": {"nakshatra": self._moon_nakshatra, "sign": "Aries",
                         "nakshatra_pada": 1}}


def _koota(result: dict, label: str) -> dict:
    return next(row for row in result["rows"] if row["label"] == label)


class TestRajjuTable:
    def test_every_nakshatra_assigned_exactly_once(self):
        assert set(RAJJU_GROUPS) == set(NAKSHATRAS)

    def test_five_groups_with_expected_sizes(self):
        from collections import Counter
        sizes = Counter(RAJJU_GROUPS.values())
        assert sizes == {"Shiro": 3, "Kantha": 6, "Udara": 6, "Kati": 6, "Pada": 6}


class TestVedhaTable:
    def test_thirteen_pairs_covering_twenty_six_nakshatras(self):
        covered = set()
        for pair in VEDHA_PAIRS:
            covered |= pair
        assert len(VEDHA_PAIRS) == 13
        assert len(covered) == 26
        assert set(NAKSHATRAS) - covered == {"Chitra"}

    def test_pairs_are_symmetric_lookup(self):
        # frozenset membership makes direction irrelevant by construction;
        # confirm a known pair matches regardless of which chart is which.
        a, b = StubChart("A", "Ashwini"), StubChart("B", "Jyeshtha")
        b2, a2 = StubChart("B", "Jyeshtha"), StubChart("A", "Ashwini")
        assert _koota(dashakoota_extension(a, b), "Vedha")["points"] == 0
        assert _koota(dashakoota_extension(b2, a2), "Vedha")["points"] == 0


class TestDashakootaExtension:
    def test_same_rajju_group_is_dosha(self):
        a = StubChart("A", "Rohini")   # Kantha
        b = StubChart("B", "Ardra")    # Kantha
        row = _koota(dashakoota_extension(a, b), "Rajju")
        assert row["points"] == 0

    def test_different_rajju_groups_is_full_points(self):
        a = StubChart("A", "Rohini")   # Kantha
        b = StubChart("B", "Ashwini")  # Pada
        row = _koota(dashakoota_extension(a, b), "Rajju")
        assert row["points"] == 2

    def test_vedha_pair_is_dosha(self):
        a = StubChart("A", "Ashwini")
        b = StubChart("B", "Jyeshtha")
        row = _koota(dashakoota_extension(a, b), "Vedha")
        assert row["points"] == 0

    def test_non_vedha_pair_is_full_points(self):
        a = StubChart("A", "Ashwini")
        b = StubChart("B", "Bharani")
        row = _koota(dashakoota_extension(a, b), "Vedha")
        assert row["points"] == 2

    def test_stree_deergha_below_threshold_is_dosha(self):
        # Ashwini(0) -> Bharani(1): count = ((1-0)%27)+1 = 2, well below 13.
        groom = StubChart("groom", "Bharani")
        bride = StubChart("bride", "Ashwini")
        row = _koota(dashakoota_extension(groom, bride), "Stree Deergha")
        assert row["points"] == 0

    def test_stree_deergha_at_threshold_is_full_points(self):
        # Ashwini(0) -> Hasta(12): count = ((12-0)%27)+1 = 13 == threshold.
        groom = StubChart("groom", "Hasta")
        bride = StubChart("bride", "Ashwini")
        row = _koota(dashakoota_extension(groom, bride), "Stree Deergha")
        assert row["points"] == 2
        assert STREE_DEERGHA_MIN_COUNT == 13

    def test_stree_deergha_just_below_threshold_is_dosha(self):
        # Ashwini(0) -> Uttara Phalguni(11): count = 12, one below threshold.
        groom = StubChart("groom", "Uttara Phalguni")
        bride = StubChart("bride", "Ashwini")
        row = _koota(dashakoota_extension(groom, bride), "Stree Deergha")
        assert row["points"] == 0

    def test_total_and_max_match_three_kootas(self):
        a, b = StubChart("A", "Chitra"), StubChart("B", "Revati")
        out = dashakoota_extension(a, b)
        assert out["max"] == 6
        assert len(out["rows"]) == 3
        assert out["total"] == sum(r["points"] for r in out["rows"])

    def test_hard_blockers_lists_active_rajju_and_vedha_only(self):
        # Same Rajju group AND a Vedha pair simultaneously.
        a = StubChart("A", "Ashwini")   # Pada
        b = StubChart("B", "Jyeshtha")  # Pada, and Vedha-paired with Ashwini
        out = dashakoota_extension(a, b)
        assert set(out["hard_blockers"]) == {"Rajju", "Vedha"}

    def test_no_hard_blockers_when_neither_active(self):
        a = StubChart("A", "Rohini")
        b = StubChart("B", "Ashwini")
        out = dashakoota_extension(a, b)
        assert out["hard_blockers"] == []

    def test_gun_milan_carries_dashakoota_extension_additively(self):
        a = StubChart("A", "Rohini")
        b = StubChart("B", "Ashwini")
        full = gun_milan(a, b)
        assert "dashakoota_extension" in full
        assert full["total"] == pytest.approx(
            sum(r["points"] for r in full["rows"])
        )  # unchanged: dashakoota points never leak into the 36-point total

    def test_unavailable_nakshatra_degrades_gracefully(self):
        a = StubChart("A", "Not A Real Nakshatra")
        b = StubChart("B", "Ashwini")
        out = dashakoota_extension(a, b)
        for row in out["rows"]:
            assert row["points"] == 0
            assert row["verified"] is False
