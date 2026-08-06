"""Tests for the Sripati (Bhava Chalit) house system (T3.3,
docs/backend_astro_depth_checklist_2026-08-06.md) — an opt-in alternate
lens, additive only.
"""
from __future__ import annotations

import pytest
import swisseph as swe

from astrospace.core.vedic.bhava_chalit import (
    bhava_chalit,
    house_of,
    sripati_cusps,
    sripati_madhyas,
)
from astrospace.core.vedic.positions import (
    sidereal_lagna,
    sidereal_mc,
    sidereal_positions,
)


class TestSripatiMadhyas:
    def test_first_and_tenth_madhya_are_lagna_and_mc(self):
        madhyas = sripati_madhyas(lagna_lon=100.0, mc_lon=10.0)
        assert madhyas[1] == pytest.approx(100.0)
        assert madhyas[10] == pytest.approx(10.0)

    def test_fourth_and_seventh_are_opposite_ic_and_descendant(self):
        madhyas = sripati_madhyas(lagna_lon=100.0, mc_lon=10.0)
        assert madhyas[4] == pytest.approx((10.0 + 180.0) % 360.0)
        assert madhyas[7] == pytest.approx((100.0 + 180.0) % 360.0)

    def test_trisection_lands_evenly_when_quadrant_is_ninety_degrees(self):
        # Idealized chart: MC at 0, Lagna at 90 (a clean 90-degree quadrant).
        madhyas = sripati_madhyas(lagna_lon=90.0, mc_lon=0.0)
        assert madhyas[11] == pytest.approx(30.0)
        assert madhyas[12] == pytest.approx(60.0)
        assert madhyas[2] == pytest.approx(120.0)
        assert madhyas[3] == pytest.approx(150.0)
        assert madhyas[4] == pytest.approx(180.0)
        assert madhyas[5] == pytest.approx(210.0)
        assert madhyas[6] == pytest.approx(240.0)
        assert madhyas[7] == pytest.approx(270.0)
        assert madhyas[8] == pytest.approx(300.0)
        assert madhyas[9] == pytest.approx(330.0)

    def test_all_twelve_madhyas_present_and_in_range(self):
        madhyas = sripati_madhyas(lagna_lon=222.0, mc_lon=137.0)
        assert set(madhyas) == set(range(1, 13))
        for lon in madhyas.values():
            assert 0.0 <= lon < 360.0


class TestSripatiCusps:
    def test_idealized_ninety_degree_chart_gives_thirty_degree_houses(self):
        layout = sripati_cusps(lagna_lon=90.0, mc_lon=0.0)
        for h in range(1, 13):
            assert layout["widths"][h] == pytest.approx(30.0)

    def test_cusp_widths_sum_to_full_circle(self):
        layout = sripati_cusps(lagna_lon=222.0, mc_lon=137.0)
        assert sum(layout["widths"].values()) == pytest.approx(360.0)

    def test_house_one_cusp_is_between_madhya_twelve_and_madhya_one(self):
        layout = sripati_cusps(lagna_lon=100.0, mc_lon=10.0)
        m12, m1 = layout["madhyas"][12], layout["madhyas"][1]
        arc = (m1 - m12) % 360.0
        expected = (m12 + arc / 2.0) % 360.0
        assert layout["cusps"][1] == pytest.approx(expected)

    def test_cusps_are_forward_monotonic_around_the_circle(self):
        """Each house's arc (to the next house's cusp) must be positive and
        the twelve arcs must exactly partition 360 degrees — a chart with a
        badly-ordered quadrant would show up as a zero or negative arc."""
        layout = sripati_cusps(lagna_lon=310.0, mc_lon=40.0)
        for h in range(1, 13):
            assert 0.0 < layout["widths"][h] < 360.0


class TestHouseOf:
    def test_planet_at_a_madhya_falls_in_that_house(self):
        layout = sripati_cusps(lagna_lon=90.0, mc_lon=0.0)
        for h, madhya_lon in layout["madhyas"].items():
            assert house_of(madhya_lon, layout["cusps"]) == h

    def test_planet_just_after_a_cusp_falls_in_that_house(self):
        layout = sripati_cusps(lagna_lon=90.0, mc_lon=0.0)
        for h in range(1, 13):
            just_inside = (layout["cusps"][h] + 0.01) % 360.0
            assert house_of(just_inside, layout["cusps"]) == h

    def test_planet_just_before_a_cusp_falls_in_the_previous_house(self):
        layout = sripati_cusps(lagna_lon=90.0, mc_lon=0.0)
        for h in range(1, 13):
            prev_h = 12 if h == 1 else h - 1
            just_outside = (layout["cusps"][h] - 0.01) % 360.0
            assert house_of(just_outside, layout["cusps"]) == prev_h

    def test_every_longitude_maps_to_exactly_one_house(self):
        layout = sripati_cusps(lagna_lon=222.0, mc_lon=137.0)
        for tenths in range(0, 3600):
            lon = tenths / 10.0
            h = house_of(lon, layout["cusps"])
            assert 1 <= h <= 12


class TestBhavaChalitIntegration:
    BIRTH_JD = swe.julday(1991, 8, 14, 6 - 5.5 + 12 / 60)
    LAT, LNG = 16.51, 80.63

    def test_real_ephemeris_chart_is_internally_consistent(self):
        lagna = sidereal_lagna(self.BIRTH_JD, self.LAT, self.LNG)
        mc = sidereal_mc(self.BIRTH_JD, self.LAT, self.LNG)
        positions = sidereal_positions(self.BIRTH_JD)
        out = bhava_chalit(lagna, mc, positions)

        assert out["madhyas"][1] == pytest.approx(lagna)
        assert out["madhyas"][10] == pytest.approx(mc)
        assert sum(out["widths"].values()) == pytest.approx(360.0)
        for planet, row in out["planets"].items():
            assert 1 <= row["house"] <= 12

    def test_mc_and_lagna_are_generally_distinct_points(self):
        """Sanity: MC should not equal the Ascendant for an ordinary birth
        (they coincide only in degenerate cases at the poles)."""
        lagna = sidereal_lagna(self.BIRTH_JD, self.LAT, self.LNG)
        mc = sidereal_mc(self.BIRTH_JD, self.LAT, self.LNG)
        assert abs(((lagna - mc + 180) % 360) - 180) > 1.0

    def test_does_not_mutate_or_depend_on_whole_sign_house_state(self):
        """Additive-only guarantee: calling bhava_chalit() must not change
        what sign-index-based whole-sign house lookups return for the same
        positions — this system is a separate, opt-in lens."""
        from astrospace.core.vedic.positions import house_from_lagna, sign_index

        lagna = sidereal_lagna(self.BIRTH_JD, self.LAT, self.LNG)
        mc = sidereal_mc(self.BIRTH_JD, self.LAT, self.LNG)
        positions = sidereal_positions(self.BIRTH_JD)
        lagna_sign = sign_index(lagna)
        before = {
            p: house_from_lagna(sign_index(d["lon"]), lagna_sign)
            for p, d in positions.items()
        }
        bhava_chalit(lagna, mc, positions)
        after = {
            p: house_from_lagna(sign_index(d["lon"]), lagna_sign)
            for p, d in positions.items()
        }
        assert before == after
