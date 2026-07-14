"""Tests for classical Moon-sign gochara with Vedha and Ashtakavarga transit weighting.

Synthetic transit positions prove the vedha logic (favourable house, obstruction,
classical Sun-Saturn and Moon-Mercury exemptions); a real chart proves the
Ashtakavarga transit rows (BAV bindus, SAV, kakshya) are wired into
transit_analysis.
"""
from datetime import datetime, timezone

from astrospace.core.vedic.chart import VedicChart
from astrospace.core.vedic.gocharam import (
    CLASSICAL_GOCHARA_VEDHA,
    classical_gochara_status,
)
from astrospace.core.vedic.gocharam.timeline import gochara_rules as gocharam_gochara_rules
from astrospace.core.vedic.transits import (
    KAKSHYA_LORDS,
    _bav_support,
    _effective_severity,
    _kakshya_of,
    _sav_support,
    classical_gochara,
    gochara_rules,
    transit_analysis,
)

ARIES = 0
DELHI = {"lat": 28.6139, "lng": 77.2090, "tz_str": "Asia/Kolkata"}


def _positions(**signs: int) -> dict:
    """Build a synthetic transit-position dict from planet -> sign index (0-11)."""
    return {
        planet: {"lon": sign * 30 + 15.0, "speed": 1.0, "retrograde": False}
        for planet, sign in signs.items()
    }


def _base_signs(**overrides: int) -> dict:
    """Nine planets placed so no favourable planet is obstructed (Moon = Aries).

    Houses from an Aries natal Moon equal sign_index + 1.
    """
    signs = {
        "Sun": 3,       # house 4 (not favourable for Sun)
        "Moon": 1,      # house 2 (not favourable for Moon)
        "Mars": 4,      # house 5 (not favourable for Mars)
        "Mercury": 2,   # house 3 (not favourable for Mercury)
        "Jupiter": 10,  # house 11 (favourable, vedha house 8 = sign 7, empty)
        "Venus": 5,     # house 6 (not favourable for Venus)
        "Saturn": 8,    # house 9 (not favourable for Saturn)
        "Rahu": 6,      # house 7
        "Ketu": 0,      # house 1
    }
    signs.update(overrides)
    return signs


class TestClassicalGocharaVedha:
    def test_jupiter_favourable_unobstructed(self):
        result = classical_gochara(_positions(**_base_signs()), ARIES)
        jupiter = result["Jupiter"]
        assert jupiter["house_from_moon"] == 11
        assert jupiter["favourable"] is True
        assert jupiter["vedha"] == {"obstructed": False, "by": None, "vedha_house": 8}
        assert jupiter["effective"] == "favourable"
        assert jupiter["source_status"] == "classical"

    def test_jupiter_obstructed_by_planet_in_vedha_sthana(self):
        # Mars moves into house 8 (sign 7), the vedha sthana for Jupiter's 11th.
        result = classical_gochara(_positions(**_base_signs(Mars=7)), ARIES)
        jupiter = result["Jupiter"]
        assert jupiter["favourable"] is True
        assert jupiter["vedha"]["obstructed"] is True
        assert jupiter["vedha"]["by"] == "Mars"
        assert jupiter["vedha"]["vedha_house"] == 8
        assert jupiter["effective"] == "obstructed"

    def test_unfavourable_house_reports_unfavourable(self):
        result = classical_gochara(_positions(**_base_signs()), ARIES)
        sun = result["Sun"]  # house 4 is not in Sun's favourable set {3, 6, 10, 11}
        assert sun["favourable"] is False
        assert sun["effective"] == "unfavourable"
        assert sun["vedha"] == {"obstructed": False, "by": None, "vedha_house": None}

    def test_sun_saturn_exception_no_vedha_between_them(self):
        # Sun in house 11 (favourable, vedha house 5 = sign 4); Saturn stands in
        # the vedha sthana but the father-son pair carries no vedha.
        signs = _base_signs(Sun=10, Jupiter=8, Saturn=4, Mars=6)
        result = classical_gochara(_positions(**signs), ARIES)
        sun = result["Sun"]
        assert sun["favourable"] is True
        assert sun["vedha"]["obstructed"] is False
        assert sun["effective"] == "favourable"
        # Control: a non-exempt planet in the same vedha house does obstruct.
        control = classical_gochara(_positions(**_base_signs(Sun=10, Jupiter=8, Mars=4)), ARIES)
        assert control["Sun"]["vedha"]["obstructed"] is True
        assert control["Sun"]["vedha"]["by"] == "Mars"

    def test_saturn_not_obstructed_by_sun(self):
        # Saturn in house 3 (favourable, vedha house 12 = sign 11); Sun in the
        # vedha sthana does not obstruct Saturn.
        signs = _base_signs(Saturn=2, Mercury=8, Sun=11)
        result = classical_gochara(_positions(**signs), ARIES)
        saturn = result["Saturn"]
        assert saturn["favourable"] is True
        assert saturn["house_from_moon"] == 3
        assert saturn["vedha"]["obstructed"] is False
        # Control: Moon in the same vedha sthana does obstruct Saturn.
        control = classical_gochara(
            _positions(**_base_signs(Saturn=2, Mercury=8, Moon=11)), ARIES
        )
        assert control["Saturn"]["vedha"]["obstructed"] is True
        assert control["Saturn"]["vedha"]["by"] == "Moon"

    def test_moon_mercury_exception(self):
        # Transit Moon in house 1 (favourable, vedha house 5 = sign 4);
        # Mercury in the vedha sthana does not obstruct the Moon.
        signs = _base_signs(Moon=0, Ketu=9, Mercury=4, Mars=5)
        result = classical_gochara(_positions(**signs), ARIES)
        moon = result["Moon"]
        assert moon["house_from_moon"] == 1
        assert moon["favourable"] is True
        assert moon["vedha"]["obstructed"] is False
        # And Mercury (house 5 is not favourable for Mercury) stays consistent
        # the other way: Mercury favourable in 2 with Moon in its vedha house 5.
        signs = _base_signs(Mercury=1, Moon=4, Mars=5)
        result = classical_gochara(_positions(**signs), ARIES)
        mercury = result["Mercury"]
        assert mercury["house_from_moon"] == 2
        assert mercury["favourable"] is True
        assert mercury["vedha"]["vedha_house"] == 5
        assert mercury["vedha"]["obstructed"] is False
        # Control: Venus in Mercury's vedha house does obstruct.
        control = classical_gochara(
            _positions(**_base_signs(Mercury=1, Venus=4, Mars=5)), ARIES
        )
        assert control["Mercury"]["vedha"]["obstructed"] is True
        assert control["Mercury"]["vedha"]["by"] == "Venus"

    def test_planet_cannot_obstruct_itself(self):
        # Only the favourable planet occupies signs; its own position never
        # counts as vedha even if favourable and vedha house coincide checks run.
        result = classical_gochara_status({"Jupiter": 11})
        assert result["Jupiter"]["favourable"] is True
        assert result["Jupiter"]["vedha"]["obstructed"] is False

    def test_nodes_follow_saturn_convention_and_are_flagged(self):
        signs = _base_signs(Rahu=2, Mercury=6, Ketu=5)
        result = classical_gochara(_positions(**signs), ARIES)
        assert result["Rahu"]["house_from_moon"] == 3
        assert result["Rahu"]["favourable"] is True
        assert result["Rahu"]["source_status"] == "convention_dependent"
        assert result["Ketu"]["house_from_moon"] == 6
        assert result["Ketu"]["favourable"] is True
        assert result["Ketu"]["source_status"] == "convention_dependent"
        assert CLASSICAL_GOCHARA_VEDHA["Rahu"] == CLASSICAL_GOCHARA_VEDHA["Saturn"]
        assert CLASSICAL_GOCHARA_VEDHA["Ketu"] == CLASSICAL_GOCHARA_VEDHA["Saturn"]

    def test_gochara_rules_payload_includes_classical_gochara(self):
        result = gochara_rules(_positions(**_base_signs()), ARIES, ARIES)
        assert "classical_gochara" in result
        assert result["classical_gochara"]["Jupiter"]["effective"] == "favourable"
        # Existing keys are untouched.
        for key in ("planets", "rules", "active_rules", "core_reading", "sade_sati"):
            assert key in result


class TestGocharamVedhaWiring:
    def test_supportive_rule_gains_obstructed_flag(self):
        # Jupiter in house 11 -> Guru Bala active; Mars in vedha house 8.
        obstructed = gocharam_gochara_rules(_positions(**_base_signs(Mars=7)), ARIES, ARIES)
        rule = next(r for r in obstructed["rules"] if r["id"] == "gochara_guru_moon_support")
        assert rule["active"] is True  # active semantics unchanged
        assert rule["obstructed"] is True
        assert "Vedha" in rule["note"]
        assert "Mars" in rule["note"]

        clear = gocharam_gochara_rules(_positions(**_base_signs()), ARIES, ARIES)
        rule = next(r for r in clear["rules"] if r["id"] == "gochara_guru_moon_support")
        assert rule["active"] is True
        assert rule["obstructed"] is False
        assert "Vedha" not in rule["note"]
        assert "classical_gochara" in clear


class TestAshtakavargaTransitSupport:
    def test_bav_and_sav_classification_thresholds(self):
        assert _bav_support(8) == "strong"
        assert _bav_support(5) == "strong"
        assert _bav_support(4) == "average"
        assert _bav_support(3) == "weak"
        assert _bav_support(0) == "weak"
        assert _sav_support(35) == "strong"
        assert _sav_support(30) == "strong"
        assert _sav_support(29) == "average"
        assert _sav_support(25) == "average"
        assert _sav_support(24) == "weak"

    def test_kakshya_boundaries(self):
        assert _kakshya_of(0.0) == (1, "Saturn")
        assert _kakshya_of(3.74) == (1, "Saturn")
        assert _kakshya_of(3.75) == (2, "Jupiter")
        assert _kakshya_of(15.0) == (5, "Venus")
        assert _kakshya_of(29.99) == (8, "Lagna")
        assert _kakshya_of(30.0) == (1, "Saturn")  # next sign wraps to kakshya 1

    def test_effective_severity_softening_and_dilution(self):
        assert _effective_severity("high", True, "strong") == "medium"
        assert _effective_severity("medium", True, "strong") == "low"
        assert _effective_severity("supportive", True, "weak") == "diluted"
        # No adjustment cases: booleans and base severity stay untouched.
        assert _effective_severity("high", True, "weak") == "high"
        assert _effective_severity("high", True, "average") == "high"
        assert _effective_severity("supportive", True, "strong") == "supportive"
        assert _effective_severity("high", False, "strong") == "high"
        assert _effective_severity("supportive", True, None) == "supportive"

    def test_transit_analysis_reports_av_rows_and_av_context(self):
        chart = VedicChart("T", 1990, 1, 1, 12, 0, **DELHI)
        result = transit_analysis(
            chart.positions,
            chart.lagna_lon,
            datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc),
            chart.ayanamsha,
            chart.node_type,
        )
        av = result["ashtakavarga_transit"]
        assert av["note"]
        rows = av["planets"]
        assert set(rows) == {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"}
        for row in rows.values():
            assert 0 <= row["bindus"] <= 8
            assert 0 <= row["sav"] <= 56
            assert row["bav_support"] in {"strong", "average", "weak"}
            assert row["sav_support"] in {"strong", "average", "weak"}
            assert 1 <= row["kakshya"]["kakshya_index"] <= 8
            assert row["kakshya"]["kakshya_lord"] in KAKSHYA_LORDS
            assert isinstance(row["kakshya"]["bindu_given"], bool)

        # Every gochara rule row gains av_context and effective_severity.
        for rule in result["gochara"]["rules"]:
            assert "av_context" in rule
            assert "effective_severity" in rule
            assert "obstructed" in rule
            if rule["planet"] in rows:
                assert rule["av_context"]["bindus"] == rows[rule["planet"]]["bindus"]
                assert rule["av_context"]["sav"] == rows[rule["planet"]]["sav"]
            else:
                assert rule["av_context"] is None
                assert rule["effective_severity"] == rule["severity"]
        assert "classical_gochara" in result["gochara"]
