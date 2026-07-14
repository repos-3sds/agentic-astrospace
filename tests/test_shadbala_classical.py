"""
Tests for the classical (BPHS, virupa-scaled) Shadbala section.

The legacy normalized payload is covered by tests/test_vedic.py; here we
check the classical formulas at their anchor points and the payload shape.
"""
import pytest

from astrospace.core.vedic.chart import VedicChart
from astrospace.core.vedic.constants import EXALTATION
from astrospace.core.vedic.strength import (
    CLASSICAL_SHADBALA_PLANETS,
    dig_bala_virupa,
    kendradi_bala,
    ojayugma_bala,
    sputa_drishti,
    uccha_bala,
)

DELHI = {"lat": 28.6139, "lng": 77.2090, "tz_str": "Asia/Kolkata"}


class TestUcchaBala:
    def test_deep_exaltation_gives_60(self):
        for planet, (sign, deg) in EXALTATION.items():
            lon = sign * 30.0 + deg
            assert uccha_bala(planet, lon) == pytest.approx(60.0)

    def test_deep_debilitation_gives_0(self):
        for planet, (sign, deg) in EXALTATION.items():
            lon = (sign * 30.0 + deg + 180.0) % 360.0
            assert uccha_bala(planet, lon) == pytest.approx(0.0)

    def test_quadrature_gives_30(self):
        # 90 degrees from both deep points.
        assert uccha_bala("Sun", 100.0) == pytest.approx(30.0)


class TestDigBala:
    def test_jupiter_on_ascendant_gives_60(self):
        assert dig_bala_virupa("Jupiter", 123.45, 123.45) == pytest.approx(60.0)

    def test_jupiter_on_seventh_cusp_gives_0(self):
        assert dig_bala_virupa("Jupiter", (123.45 + 180.0) % 360.0, 123.45) == pytest.approx(0.0)

    def test_saturn_on_seventh_cusp_gives_60(self):
        assert dig_bala_virupa("Saturn", (10.0 + 180.0) % 360.0, 10.0) == pytest.approx(60.0)

    def test_sun_on_tenth_cusp_gives_60(self):
        assert dig_bala_virupa("Sun", (10.0 + 270.0) % 360.0, 10.0) == pytest.approx(60.0)

    def test_moon_on_fourth_cusp_gives_60(self):
        assert dig_bala_virupa("Moon", (10.0 + 90.0) % 360.0, 10.0) == pytest.approx(60.0)


class TestKendradiBala:
    def test_kendra_panaphara_apoklima(self):
        lagna = 0.0  # Aries lagna
        assert kendradi_bala(5.0, lagna) == 60.0     # house 1 (kendra)
        assert kendradi_bala(95.0, lagna) == 60.0    # house 4
        assert kendradi_bala(35.0, lagna) == 30.0    # house 2 (panaphara)
        assert kendradi_bala(305.0, lagna) == 30.0   # house 11
        assert kendradi_bala(65.0, lagna) == 15.0    # house 3 (apoklima)
        assert kendradi_bala(335.0, lagna) == 15.0   # house 12


class TestOjayugmaBala:
    def test_moon_even_rashi_even_navamsha_gives_30(self):
        # 0 deg Taurus: even rashi; first navamsha is Capricorn (even).
        assert ojayugma_bala("Moon", 30.0) == 30.0

    def test_moon_even_rashi_odd_navamsha_gives_15(self):
        # 3.5 deg Taurus: even rashi; second navamsha is Aquarius (odd).
        assert ojayugma_bala("Moon", 33.5) == 15.0

    def test_sun_in_even_rashi_even_navamsha_gives_0(self):
        # Sun prefers odd; 0 deg Taurus scores nothing.
        assert ojayugma_bala("Sun", 30.0) == 0.0

    def test_sun_odd_rashi_odd_navamsha_gives_30(self):
        # 0 deg Aries: odd rashi; first navamsha is Aries (odd).
        assert ojayugma_bala("Sun", 0.0) == 30.0

    def test_bounds(self):
        for planet in CLASSICAL_SHADBALA_PLANETS:
            for lon in [0.0, 33.5, 61.0, 95.0, 123.0, 359.0]:
                assert ojayugma_bala(planet, lon) in (0.0, 15.0, 30.0)


class TestSputaDrishti:
    def test_anchor_points(self):
        # Values from the implemented continuous classical grading.
        assert sputa_drishti("Sun", 30.0) == pytest.approx(0.0)
        assert sputa_drishti("Sun", 45.0) == pytest.approx(7.5)
        assert sputa_drishti("Sun", 60.0) == pytest.approx(15.0)
        assert sputa_drishti("Sun", 90.0) == pytest.approx(45.0)
        assert sputa_drishti("Sun", 120.0) == pytest.approx(30.0)
        assert sputa_drishti("Sun", 150.0) == pytest.approx(0.0)
        assert sputa_drishti("Sun", 180.0) == pytest.approx(60.0)
        assert sputa_drishti("Sun", 240.0) == pytest.approx(30.0)
        assert sputa_drishti("Sun", 300.0) == pytest.approx(0.0)
        assert sputa_drishti("Sun", 15.0) == pytest.approx(0.0)

    def test_continuity_at_every_boundary(self):
        eps = 1e-6
        for boundary in [30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 300.0]:
            left = sputa_drishti("Sun", boundary - eps)
            right = sputa_drishti("Sun", boundary + eps)
            assert abs(left - right) < 1.0, f"discontinuity at {boundary}: {left} vs {right}"

    def test_saturn_third_aspect_override(self):
        assert sputa_drishti("Saturn", 75.0) == pytest.approx(60.0)
        assert sputa_drishti("Saturn", 285.0) == pytest.approx(60.0)

    def test_mars_and_jupiter_overrides(self):
        assert sputa_drishti("Mars", 100.0) == pytest.approx(60.0)
        assert sputa_drishti("Mars", 225.0) == pytest.approx(60.0)
        assert sputa_drishti("Jupiter", 130.0) == pytest.approx(60.0)
        assert sputa_drishti("Jupiter", 250.0) == pytest.approx(60.0)

    def test_non_special_planets_not_boosted(self):
        # Venus has no special aspect; 100 deg stays on the base curve.
        assert sputa_drishti("Venus", 100.0) == pytest.approx(40.0)


@pytest.fixture(scope="module")
def payload():
    chart = VedicChart("S", 1990, 1, 1, 12, 0, **DELHI)
    return chart.shadbala()


class TestClassicalPayload:
    def test_classical_section_exists(self, payload):
        classical = payload["classical"]
        assert classical is not None
        assert classical["system"] == "Shadbala (BPHS virupa)"
        assert set(classical["rows"]) == set(CLASSICAL_SHADBALA_PLANETS)

    def test_classical_rows_shape_and_ranges(self, payload):
        expected_components = {
            "sthana_bala", "dig_bala", "kala_bala",
            "cheshta_bala", "naisargika_bala", "drik_bala",
        }
        for planet, row in payload["classical"]["rows"].items():
            assert set(row["components"]) == expected_components
            assert 60.0 <= row["total_virupas"] <= 700.0, planet
            assert row["ratio"] > 0
            assert row["rupas"] == pytest.approx(row["total_virupas"] / 60.0, abs=0.01)
            assert row["required_rupas"] > 0
            assert isinstance(row["sufficient"], bool)

    def test_classical_ranking_sorted_by_ratio(self, payload):
        ranking = payload["classical"]["ranking"]
        assert len(ranking) == 7
        assert ranking == sorted(ranking, key=lambda r: r["ratio"], reverse=True)

    def test_legacy_keys_still_present(self, payload):
        assert "ranking" in payload
        assert "conditions" in payload
        for planet in CLASSICAL_SHADBALA_PLANETS:
            row = payload["rows"][planet]
            assert 0 <= row["total_score"] <= 100
            assert row["rank_band"] in {"strong", "moderate", "weak"}
            assert set(row["components"]) == {
                "sthana_bala", "dig_bala", "kala_bala",
                "cheshta_bala", "naisargika_bala", "drik_bala",
            }

    def test_legacy_score_derives_from_classical_ratio(self, payload):
        for planet in CLASSICAL_SHADBALA_PLANETS:
            ratio = payload["classical"]["rows"][planet]["ratio"]
            expected = round(max(0.0, min(100.0, ratio * 60.0)), 1)
            assert payload["rows"][planet]["total_score"] == pytest.approx(expected)

    def test_kala_bala_subcomponents_present(self, payload):
        expected = {"nathonnata", "paksha", "tribhaga", "abda", "masa",
                    "vara", "hora", "ayana", "yuddha"}
        for row in payload["classical"]["rows"].values():
            assert set(row["components"]["kala_bala"]["sub"]) == expected

    def test_sthana_bala_subcomponents_present(self, payload):
        expected = {"uccha", "saptavargaja", "ojayugma", "kendradi", "drekkana"}
        for row in payload["classical"]["rows"].values():
            assert set(row["components"]["sthana_bala"]["sub"]) == expected

    def test_without_moment_classical_is_absent_and_v1_intact(self):
        from astrospace.core.vedic.strength import shadbala
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
        assert result["classical"] is None
        for row in result["rows"].values():
            assert 0 <= row["total_score"] <= 100
