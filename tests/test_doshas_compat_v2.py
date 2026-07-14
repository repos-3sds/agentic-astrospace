"""Tests for gandanta/grahan doshas, manglik exceptions, and the
classical yoni/vashya matrices plus nadi/bhakoot cancellations."""
from __future__ import annotations

import pytest

from astrospace.core.vedic.compatibility import (
    VASHYA_GROUPS,
    VASHYA_MATRIX,
    YONI_ENEMY_PAIRS,
    YONI_MATRIX,
    YONI_ORDER,
    gun_milan,
)
from astrospace.core.vedic.doshas import (
    dosha_summary,
    gandanta_dosha,
    grahan_dosha,
    manglik_dosha,
)


class StubChart:
    """Compatibility stub mirroring tests/test_vedic.py TestCompatibility."""

    def __init__(self, name: str, av: dict, moon_nakshatra: str = "Ashwini",
                 moon_sign: str = "Aries", moon_pada: int = 1):
        self.name = name
        self._av = av
        self._moon_nakshatra = moon_nakshatra
        self._moon_sign = moon_sign
        self._moon_pada = moon_pada

    def avkahada(self):
        return self._av

    def planet_details(self):
        return {"Moon": {
            "nakshatra": self._moon_nakshatra,
            "sign": self._moon_sign,
            "nakshatra_pada": self._moon_pada,
        }}


BASE_AV = {
    "varna": "Brahmin", "vashya": "Manava", "yoni": "Horse (M)",
    "rashi_lord": "Mars", "gana": "Deva", "nadi": "Aadi",
}


def _koota(result: dict, label: str) -> dict:
    return next(row for row in result["rows"] if row["label"] == label)


def _stub_pair(av_a: dict = None, av_b: dict = None, **kwargs_pairs) -> tuple:
    a_kwargs = {k[:-2]: v for k, v in kwargs_pairs.items() if k.endswith("_a")}
    b_kwargs = {k[:-2]: v for k, v in kwargs_pairs.items() if k.endswith("_b")}
    a = StubChart("A", {**BASE_AV, **(av_a or {})}, **a_kwargs)
    b = StubChart("B", {**BASE_AV, **(av_b or {})}, **b_kwargs)
    return a, b


# ── Task 1: Gandanta ─────────────────────────────────────────────────────────

class TestGandantaDosha:
    def test_moon_in_early_magha_is_severe_gandanta(self):
        positions = {"Moon": {"lon": 120.5}, "Sun": {"lon": 50.0}}
        result = gandanta_dosha(positions, lagna_lon=200.0)
        assert result["active"]
        assert result["severity"] == "severe"
        assert result["rule_id"] == "gandanta_dosha"
        assert result["verified"] is False  # convention_dependent status
        hits = result["hits"]
        assert len(hits) == 1
        hit = hits[0]
        assert hit["body"] == "Moon"
        assert hit["junction"] == "Ashlesha–Magha"
        assert hit["side"].startswith("fire")
        assert hit["degrees_from_junction"] == pytest.approx(0.5)

    def test_moon_at_end_of_jyeshtha_is_moderate_abhukta_mula(self):
        positions = {"Moon": {"lon": 238.5}, "Sun": {"lon": 50.0}}
        result = gandanta_dosha(positions, lagna_lon=200.0)
        hit = result["hits"][0]
        assert hit["junction"] == "Jyeshtha–Moola"
        assert hit["severity"] == "moderate"
        assert hit["side"].startswith("water")
        assert hit["abhukta_mula"] is True
        assert any("Abhukta Mula" in note for note in result["notes"])

    def test_revati_side_mild_and_zero_wraparound(self):
        positions = {"Moon": {"lon": 357.0}, "Sun": {"lon": 50.0}}
        result = gandanta_dosha(positions, lagna_lon=200.0)
        hit = result["hits"][0]
        assert hit["junction"] == "Revati–Ashwini"
        assert hit["severity"] == "mild"
        assert hit["degrees_from_junction"] == pytest.approx(3.0)

    def test_lagna_is_also_checked(self):
        positions = {"Moon": {"lon": 45.0}, "Sun": {"lon": 50.0}}
        result = gandanta_dosha(positions, lagna_lon=0.5)
        assert result["active"]
        assert result["hits"][0]["body"] == "Lagna"
        assert result["hits"][0]["severity"] == "severe"

    def test_no_gandanta_away_from_junctions(self):
        # Gemini→Cancer (90°) is an air→water junction, NOT gandanta.
        positions = {"Moon": {"lon": 45.0}, "Sun": {"lon": 90.5}}
        result = gandanta_dosha(positions, lagna_lon=200.0)
        assert not result["active"]
        assert result["severity"] == "none"
        assert result["hits"] == []

    def test_zone_boundary_is_one_pada(self):
        inside = gandanta_dosha({"Moon": {"lon": 120.0 + 10.0 / 3.0 - 0.01}}, 200.0)
        outside = gandanta_dosha({"Moon": {"lon": 120.0 + 10.0 / 3.0 + 0.01}}, 200.0)
        assert inside["active"]
        assert not outside["active"]


# ── Task 2: Grahan ───────────────────────────────────────────────────────────

class TestGrahanDosha:
    def _positions(self, **lons):
        base = {"Sun": 100.0, "Moon": 200.0, "Rahu": 310.0, "Ketu": 130.0}
        base.update(lons)
        return {planet: {"lon": lon} for planet, lon in base.items()}

    def test_sun_rahu_tight_conjunction_is_strong(self):
        result = grahan_dosha(self._positions(Sun=10.0, Rahu=12.0, Ketu=192.0))
        assert result["active"]
        assert result["severity"] == "strong"
        assert result["rule_id"] == "grahan_dosha"
        assert result["verified"] is False
        hit = result["hits"][0]
        assert (hit["luminary"], hit["node"]) == ("Sun", "Rahu")
        assert hit["orb"] == pytest.approx(2.0)

    def test_moon_ketu_moderate_orb(self):
        result = grahan_dosha(self._positions(Moon=95.0, Ketu=103.0, Rahu=283.0, Sun=50.0))
        hit = result["hits"][0]
        assert (hit["luminary"], hit["node"]) == ("Moon", "Ketu")
        assert hit["severity"] == "moderate"
        assert hit["orb"] == pytest.approx(8.0)

    def test_same_sign_wide_orb_is_mild(self):
        result = grahan_dosha(self._positions(Sun=91.0, Ketu=102.0, Rahu=282.0))
        hit = result["hits"][0]
        assert hit["severity"] == "mild"
        assert hit["orb"] == pytest.approx(11.0)

    def test_no_grahan_when_signs_differ(self):
        result = grahan_dosha(self._positions(Sun=10.0, Rahu=40.0, Ketu=220.0))
        assert not result["active"]
        assert result["severity"] == "none"


# ── Task 3: Manglik exceptions ───────────────────────────────────────────────

class TestManglikExceptions:
    def test_backward_compatible_keys_preserved(self):
        positions = {"Mars": {"lon": 0.0}, "Moon": {"lon": 330.0}, "Venus": {"lon": 180.0}}
        dosha = manglik_dosha(positions, 0.0)
        for key in ("checks", "severity", "active_references", "exceptions", "net_severity"):
            assert key in dosha
        assert dosha["severity"] == "strong"  # raw severity unchanged
        assert dosha["source_status"] == "verified_common"

    def test_mars_own_sign_exception_downgrades_one_step(self):
        # Mars at 0° Aries (own sign): raw strong -> net moderate.
        positions = {"Mars": {"lon": 0.0}, "Moon": {"lon": 330.0}, "Venus": {"lon": 180.0}}
        dosha = manglik_dosha(positions, 0.0)
        own_sign = next(e for e in dosha["exceptions"] if "own sign" in e["rule"])
        assert own_sign["applies"]
        assert own_sign["source_status"] == "convention_dependent"
        assert dosha["severity"] == "strong"
        assert dosha["net_severity"] == "moderate"

    def test_jupiter_drishti_exception(self):
        # Mars Taurus, Jupiter Virgo: Mars is 9th from Jupiter -> drishti.
        positions = {
            "Mars": {"lon": 35.0}, "Moon": {"lon": 65.0},
            "Venus": {"lon": 95.0}, "Jupiter": {"lon": 155.0},
        }
        dosha = manglik_dosha(positions, 0.0)
        drishti = next(e for e in dosha["exceptions"] if "drishti" in e["rule"])
        assert drishti["applies"]
        assert dosha["severity"] == "moderate"
        assert dosha["net_severity"] == "mild"

    def test_no_exception_keeps_net_severity_equal(self):
        # Mars Taurus, Jupiter conjunct Mars (house 1, no 5/7/9 drishti),
        # Moon and Venus elsewhere: nothing applies.
        positions = {
            "Mars": {"lon": 35.0}, "Moon": {"lon": 65.0},
            "Venus": {"lon": 95.0}, "Jupiter": {"lon": 40.0},
        }
        dosha = manglik_dosha(positions, 0.0)
        assert not any(e["applies"] for e in dosha["exceptions"])
        assert dosha["net_severity"] == dosha["severity"] == "moderate"

    def test_downgrade_never_below_mild_while_active(self):
        # Mars Scorpio (own sign exception) with exactly one active reference.
        positions = {"Mars": {"lon": 215.0}, "Moon": {"lon": 275.0}, "Venus": {"lon": 75.0}}
        dosha = manglik_dosha(positions, 0.0)
        assert dosha["active_references"] == ["Lagna"]
        assert dosha["severity"] == "mild"
        assert dosha["net_severity"] == "mild"

    def test_mars_moon_conjunction_exception(self):
        # Mars and Moon both in Cancer.
        positions = {"Mars": {"lon": 100.0}, "Moon": {"lon": 110.0}, "Venus": {"lon": 180.0}}
        dosha = manglik_dosha(positions, 0.0)
        conj = next(e for e in dosha["exceptions"] if "conjunct Moon" in e["rule"])
        assert conj["applies"]
        assert dosha["net_severity"] != dosha["severity"] or dosha["severity"] in ("mild", "none")

    def test_dosha_summary_includes_new_doshas(self):
        positions = {
            "Sun": {"lon": 10.0}, "Moon": {"lon": 120.5}, "Mars": {"lon": 0.0},
            "Venus": {"lon": 180.0}, "Rahu": {"lon": 12.0}, "Ketu": {"lon": 192.0},
        }
        summary = dosha_summary(positions, 0.0)
        assert set(summary) == {"manglik", "gandanta", "grahan"}
        assert summary["gandanta"]["active"]
        assert summary["grahan"]["active"]


# ── Task 4: Yoni matrix ──────────────────────────────────────────────────────

class TestYoniMatrix:
    def test_matrix_shape_and_value_range(self):
        assert len(YONI_ORDER) == 14
        assert set(YONI_MATRIX) == set(YONI_ORDER)
        for row in YONI_MATRIX.values():
            assert set(row) == set(YONI_ORDER)
            assert all(points in {0, 1, 2, 3, 4} for points in row.values())

    def test_matrix_is_symmetric(self):
        for a in YONI_ORDER:
            for b in YONI_ORDER:
                assert YONI_MATRIX[a][b] == YONI_MATRIX[b][a], (a, b)

    def test_diagonal_is_four(self):
        for animal in YONI_ORDER:
            assert YONI_MATRIX[animal][animal] == 4

    def test_sworn_enemy_pairs_are_zero(self):
        assert len(YONI_ENEMY_PAIRS) == 7
        for pair in YONI_ENEMY_PAIRS:
            a, b = tuple(pair)
            assert YONI_MATRIX[a][b] == 0
            assert YONI_MATRIX[b][a] == 0

    def test_zeros_only_on_enemy_pairs(self):
        for a in YONI_ORDER:
            for b in YONI_ORDER:
                if YONI_MATRIX[a][b] == 0:
                    assert frozenset((a, b)) in YONI_ENEMY_PAIRS

    def test_graded_pair_through_gun_milan(self):
        # Horse–Serpent is a friendly (3-point) pair in the standard matrix.
        a, b = _stub_pair(av_a={"yoni": "Horse (M)"},
                          av_b={"yoni": "Serpent (F)", "nadi": "Madhya"},
                          moon_nakshatra_b="Bharani")
        row = _koota(gun_milan(a, b), "Yoni")
        assert row["points"] == 3
        assert row["verified"] is False  # intermediate grades pending validation

    def test_same_and_enemy_yoni_are_verified(self):
        same_a, same_b = _stub_pair(av_b={"nadi": "Madhya"}, moon_nakshatra_b="Bharani")
        same = _koota(gun_milan(same_a, same_b), "Yoni")
        assert same["points"] == 4 and same["verified"] is True

        enemy_a, enemy_b = _stub_pair(
            av_a={"yoni": "Cow (M)"},
            av_b={"yoni": "Tiger (F)", "nadi": "Madhya"},
            moon_nakshatra_b="Bharani",
        )
        enemy = _koota(gun_milan(enemy_a, enemy_b), "Yoni")
        assert enemy["points"] == 0 and enemy["verified"] is True


# ── Task 5: Vashya matrix ────────────────────────────────────────────────────

class TestVashyaMatrix:
    def test_five_groups_with_full_rows(self):
        assert VASHYA_GROUPS == ["Chatushpada", "Manava", "Jalachara", "Vanachara", "Keeta"]
        assert set(VASHYA_MATRIX) == set(VASHYA_GROUPS)
        for row in VASHYA_MATRIX.values():
            assert set(row) == set(VASHYA_GROUPS)
            assert all(points in {0, 0.5, 1, 2} for points in row.values())

    def test_same_group_scores_two_and_manava_vanachara_zero(self):
        for group in VASHYA_GROUPS:
            assert VASHYA_MATRIX[group][group] == 2
        assert VASHYA_MATRIX["Manava"]["Vanachara"] == 0

    def test_directional_lookup_uses_person1_as_groom_row(self):
        a, b = _stub_pair(
            av_a={"vashya": "Manava"},
            av_b={"vashya": "Vanachara", "nadi": "Madhya"},
            moon_nakshatra_b="Bharani",
        )
        row = _koota(gun_milan(a, b), "Vashya")
        assert row["points"] == VASHYA_MATRIX["Manava"]["Vanachara"] == 0
        assert "groom" in row["note"]
        assert row["verified"] is False

    def test_graded_vashya_pair(self):
        a, b = _stub_pair(
            av_a={"vashya": "Chatushpada"},
            av_b={"vashya": "Vanachara", "nadi": "Madhya"},
            moon_nakshatra_b="Bharani",
        )
        row = _koota(gun_milan(a, b), "Vashya")
        assert row["points"] == 0.5


# ── Task 6: Nadi & Bhakoot cancellations ─────────────────────────────────────

class TestNadiCancellation:
    def test_same_rashi_different_nakshatra_cancels_nadi_dosha(self):
        # Ardra and Punarvasu (pada 1) both fall in Gemini and share Aadi nadi.
        a = StubChart("A", BASE_AV, moon_nakshatra="Ardra", moon_sign="Gemini", moon_pada=2)
        b = StubChart("B", BASE_AV, moon_nakshatra="Punarvasu", moon_sign="Gemini", moon_pada=1)
        row = _koota(gun_milan(a, b), "Nadi")
        assert row["points"] == 8
        assert "nadi dosha cancelled: same rashi, different nakshatras" in row["note"]
        assert row["verified"] is False

    def test_same_nakshatra_different_rashi_cancels(self):
        # Punarvasu spans Gemini (padas 1-3) and Cancer (pada 4).
        a = StubChart("A", BASE_AV, moon_nakshatra="Punarvasu", moon_sign="Gemini", moon_pada=2)
        b = StubChart("B", BASE_AV, moon_nakshatra="Punarvasu", moon_sign="Cancer", moon_pada=4)
        row = _koota(gun_milan(a, b), "Nadi")
        assert row["points"] == 8
        assert "same nakshatra, different rashis" in row["note"]

    def test_same_nakshatra_different_pada_cancels(self):
        a = StubChart("A", BASE_AV, moon_nakshatra="Ashwini", moon_sign="Aries", moon_pada=1)
        b = StubChart("B", BASE_AV, moon_nakshatra="Ashwini", moon_sign="Aries", moon_pada=3)
        row = _koota(gun_milan(a, b), "Nadi")
        assert row["points"] == 8
        assert "same nakshatra, different padas" in row["note"]

    def test_identical_moons_keep_nadi_dosha(self):
        a = StubChart("A", BASE_AV, moon_nakshatra="Ashwini", moon_sign="Aries", moon_pada=1)
        b = StubChart("B", BASE_AV, moon_nakshatra="Ashwini", moon_sign="Aries", moon_pada=1)
        row = _koota(gun_milan(a, b), "Nadi")
        assert row["points"] == 0
        assert "nadi dosha" in row["note"]

    def test_different_nadi_scores_full_and_verified(self):
        a, b = _stub_pair(av_b={"nadi": "Madhya"})
        row = _koota(gun_milan(a, b), "Nadi")
        assert row["points"] == 8
        assert row["verified"] is True


class TestBhakootCancellation:
    def test_same_lord_cancels_bhakoot_dosha(self):
        # Aries/Scorpio is a 6/8 pair, but both are Mars-ruled.
        a = StubChart("A", BASE_AV, moon_nakshatra="Ashwini", moon_sign="Aries")
        b = StubChart("B", {**BASE_AV, "nadi": "Madhya"},
                      moon_nakshatra="Anuradha", moon_sign="Scorpio")
        row = _koota(gun_milan(a, b), "Bhakoot")
        assert row["points"] == 7
        assert "bhakoot dosha cancelled" in row["note"]
        assert "Mars" in row["note"]
        assert row["verified"] is False

    def test_mutual_friend_lords_cancel(self):
        # Leo/Sagittarius is a 5/9 pair; Sun and Jupiter are mutual friends.
        a = StubChart("A", BASE_AV, moon_nakshatra="Magha", moon_sign="Leo")
        b = StubChart("B", {**BASE_AV, "nadi": "Madhya"},
                      moon_nakshatra="Moola", moon_sign="Sagittarius")
        row = _koota(gun_milan(a, b), "Bhakoot")
        assert row["points"] == 7
        assert "mutual natural friends" in row["note"]
        assert row["verified"] is False

    def test_unfriendly_lords_keep_bhakoot_dosha(self):
        # Cancer/Aquarius is a 6/8 pair; Saturn counts Moon as an enemy.
        a = StubChart("A", BASE_AV, moon_nakshatra="Pushya", moon_sign="Cancer")
        b = StubChart("B", {**BASE_AV, "nadi": "Madhya"},
                      moon_nakshatra="Dhanishta", moon_sign="Aquarius")
        row = _koota(gun_milan(a, b), "Bhakoot")
        assert row["points"] == 0
        assert "bhakoot dosha" in row["note"]

    def test_non_dosha_pair_scores_full(self):
        # Aries/Gemini is 3/11 — not a bhakoot dosha pair.
        a = StubChart("A", BASE_AV, moon_nakshatra="Ashwini", moon_sign="Aries")
        b = StubChart("B", {**BASE_AV, "nadi": "Madhya"},
                      moon_nakshatra="Ardra", moon_sign="Gemini")
        row = _koota(gun_milan(a, b), "Bhakoot")
        assert row["points"] == 7
        assert "cancelled" not in row["note"]
        assert row["verified"] is True
