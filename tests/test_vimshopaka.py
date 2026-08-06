"""Tests for Vimshopaka Bala (T1.1, backend_astro_depth_checklist_2026-08-06.md).

Hand-verifiable vectors: weight-table self-consistency (each scheme must
sum to exactly 20 by construction) and direct dignity_in_varga checks
against known exaltation/own-sign placements, plus an end-to-end score
computed from a synthetic chart and checked against a hand-computed total.
"""
from __future__ import annotations

import pytest

from astrospace.core.vedic.strength import DIGNITY_SCORES
from astrospace.core.vedic.vimshopaka import (
    BAND_LABELS,
    SCORED_PLANETS,
    WEIGHTS,
    _band,
    all_schemes,
    dignity_in_varga,
    vimshopaka_bala,
)


def _positions(**lons):
    return {planet: {"lon": lon} for planet, lon in lons.items()}


class TestWeightTable:
    @pytest.mark.parametrize("scheme", sorted(WEIGHTS))
    def test_weights_sum_to_twenty(self, scheme):
        assert sum(WEIGHTS[scheme].values()) == pytest.approx(20.0)

    def test_shodashavarga_has_all_sixteen_vargas(self):
        assert set(WEIGHTS["shodashavarga"]) == {
            "D1", "D2", "D3", "D4", "D7", "D9", "D10", "D12", "D16",
            "D20", "D24", "D27", "D30", "D40", "D45", "D60",
        }

    def test_shadvarga_saptavarga_dashavarga_are_subsets_of_shodashavarga(self):
        shodasha = set(WEIGHTS["shodashavarga"])
        for scheme in ("shadvarga", "saptavarga", "dashavarga"):
            assert set(WEIGHTS[scheme]) <= shodasha


class TestDignityInVarga:
    def test_sun_exalted_in_aries_d1(self):
        positions = _positions(Sun=5.0)  # Aries 5° — Sun's D1 exaltation
        assert dignity_in_varga("Sun", "D1", positions) == "Exalted"

    def test_sun_own_sign_leo_d1(self):
        # Leo 25° — outside the 0-20° moolatrikona range, so plain Own.
        positions = _positions(Sun=145.0)
        assert dignity_in_varga("Sun", "D1", positions) == "Own"

    def test_sun_moolatrikona_leo_d1(self):
        # Leo 5° — inside the 0-20° moolatrikona range; distinct from Own.
        positions = _positions(Sun=125.0)
        assert dignity_in_varga("Sun", "D1", positions) == "Moolatrikona"

    def test_moon_debilitated_in_scorpio_d1(self):
        positions = _positions(Moon=215.0)  # Scorpio — Moon's debilitation sign
        assert dignity_in_varga("Moon", "D1", positions) == "Debilitated"

    def test_nodes_are_flat_neutral(self):
        positions = _positions(Rahu=100.0, Ketu=280.0)
        assert dignity_in_varga("Rahu", "D9", positions) == "Neutral"
        assert dignity_in_varga("Ketu", "D30", positions) == "Neutral"

    def test_relation_uses_dispositor_varga_position_not_d1(self):
        """The dispositor's dignity ladder position must be computed in the
        SAME division as the planet being judged, not the dispositor's D1
        sign — deliberately constructed so the two approaches disagree.

        Mercury at D1 lon=10.0 lands in Cancer in D9 (navamsha); Cancer's
        lord is the Moon, and Mercury's *natural* relation to the Moon is
        enemy. Moon is placed at D1 lon=100.0, whose D1 sign is ALSO Cancer
        (coincidentally, same as Mercury's D9 sign) but whose own D9 sign is
        Libra — 4 signs from Cancer, a temporal-friend distance.

        - Using the Moon's D9 sign (Libra, correct): temporal friend +
          natural enemy -> panchadha_relation resolves to "Neutral".
        - Using the Moon's D1 sign (Cancer, the shortcut this test guards
          against): temporal non-friend + natural enemy -> "Great Enemy".

        These disagree, so this is a real behavioral check, not just a
        smoke test — confirmed against vargas.d9() and
        strength.panchadha_relation() directly rather than by hand, since
        the varga/relation arithmetic is easy to get wrong by hand.
        """
        positions = _positions(Mercury=10.0, Moon=100.0)
        assert dignity_in_varga("Mercury", "D9", positions) == "Neutral"


class TestVimshopakaBala:
    POSITIONS = _positions(
        Sun=15.0, Moon=58.9, Mars=70.0, Mercury=98.0, Jupiter=140.0,
        Venus=192.0, Saturn=273.0, Rahu=185.0, Ketu=5.0,
    )

    def test_default_scheme_is_shodashavarga(self):
        out = vimshopaka_bala(self.POSITIONS)
        assert out["scheme"] == "shodashavarga"

    def test_every_present_planet_is_scored(self):
        out = vimshopaka_bala(self.POSITIONS)
        assert set(out["planets"]) == set(self.POSITIONS)

    def test_score_is_bounded_zero_to_twenty(self):
        for scheme in WEIGHTS:
            out = vimshopaka_bala(self.POSITIONS, scheme=scheme)
            for planet, result in out["planets"].items():
                assert 0.0 <= result["score"] <= 20.0, f"{scheme}/{planet} out of range"
                assert result["max"] == 20.0

    def test_breakdown_matches_scheme_vargas(self):
        out = vimshopaka_bala(self.POSITIONS, scheme="shadvarga")
        for result in out["planets"].values():
            assert {row["varga"] for row in result["breakdown"]} == set(WEIGHTS["shadvarga"])

    def test_breakdown_earned_never_exceeds_weight(self):
        for scheme in WEIGHTS:
            out = vimshopaka_bala(self.POSITIONS, scheme=scheme)
            for result in out["planets"].values():
                for row in result["breakdown"]:
                    assert row["earned"] <= row["weight"] + 1e-9

    def test_nodes_score_flat_neutral_total(self):
        """Rahu/Ketu are Neutral (score 50/100) in every division by
        convention, so their total is exactly half of 20 regardless of
        scheme or breakdown weights."""
        for scheme in WEIGHTS:
            out = vimshopaka_bala(self.POSITIONS, scheme=scheme)
            assert out["planets"]["Rahu"]["score"] == pytest.approx(10.0)
            assert out["planets"]["Ketu"]["score"] == pytest.approx(10.0)

    def test_exalted_planet_earns_full_weight_in_d1(self):
        """Sun exalted at Aries 10° (D1) must earn D1's full weight in every
        scheme that includes D1 — a clean, hand-computable upper-bound check
        independent of the dignity-fraction convention debate."""
        positions = {**self.POSITIONS, "Sun": {"lon": 10.0}}
        for scheme, weights in WEIGHTS.items():
            out = vimshopaka_bala(positions, scheme=scheme)
            d1_row = next(r for r in out["planets"]["Sun"]["breakdown"] if r["varga"] == "D1")
            assert d1_row["dignity"] == "Exalted"
            assert d1_row["earned"] == pytest.approx(weights["D1"])

    def test_unknown_scheme_raises(self):
        with pytest.raises(ValueError, match="Unknown Vimshopaka scheme"):
            vimshopaka_bala(self.POSITIONS, scheme="ashtavarga")

    def test_all_schemes_returns_all_four(self):
        out = all_schemes(self.POSITIONS)
        assert set(out) == set(WEIGHTS)
        for scheme, result in out.items():
            assert result["scheme"] == scheme


class TestBandLabels:
    def test_band_boundaries(self):
        assert _band(0.0) == "incapable of producing results"
        assert _band(4.99) == "incapable of producing results"
        assert _band(5.0) == "minimal results"
        assert _band(9.99) == "minimal results"
        assert _band(10.0) == "moderate results"
        assert _band(14.99) == "moderate results"
        assert _band(15.0) == "full results"
        assert _band(20.0) == "full results"

    def test_band_labels_cover_full_range(self):
        assert BAND_LABELS[-1][0] > 20.0


class TestDignityScoreConsistency:
    def test_exalted_is_max_dignity_score(self):
        assert DIGNITY_SCORES["Exalted"] == max(DIGNITY_SCORES.values())

    def test_debilitated_is_min_dignity_score(self):
        assert DIGNITY_SCORES["Debilitated"] == min(DIGNITY_SCORES.values())
