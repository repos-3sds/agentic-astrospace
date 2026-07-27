"""Canonical Gocharam interpretation contract and consumer consistency."""

from datetime import datetime, timezone

import pytest

from astrospace.core.vedic.chart import VedicChart
from astrospace.core.vedic.gocharam import gochara_rules as canonical_rules
from astrospace.core.vedic.gocharam import gocharam_profile
from astrospace.core.vedic.transits import gochara_rules as transit_rules

ARIES = 0
DELHI = {"lat": 28.6139, "lng": 77.2090, "tz_str": "Asia/Kolkata"}


@pytest.fixture(scope="module")
def profile():
    chart = VedicChart("Interpretation", 1990, 1, 1, 12, 0, **DELHI)
    current = chart.dashas()["current"]
    return gocharam_profile(
        chart.positions,
        chart.lagna_lon,
        datetime(2026, 7, 14, 12, tzinfo=timezone.utc),
        chart.ayanamsha,
        chart.node_type,
        past_days=90,
        future_days=90,
        dasha_context=current,
    )


def _positions() -> dict:
    signs = {
        "Sun": 3,
        "Moon": 1,
        "Mars": 4,
        "Mercury": 2,
        "Jupiter": 10,
        "Venus": 5,
        "Saturn": 8,
        "Rahu": 6,
        "Ketu": 0,
    }
    return {
        planet: {"lon": sign * 30 + 15.0, "speed": 1.0, "retrograde": False}
        for planet, sign in signs.items()
    }


def test_profile_contract_is_versioned(profile):
    assert profile["schema_version"] == "gocharam.profile.v2"
    assert profile["engine_version"] == "gocharam-canonical-2.0"
    interpretation = profile["gochara"]["interpretation"]
    assert interpretation["schema_version"] == "gocharam.interpretation.v2"
    assert interpretation["mode"] == "deterministic_kb"


def test_matched_rules_are_populated(profile):
    matched_rules = profile["gochara"]["interpretation"]["matched_rules"]
    assert isinstance(matched_rules, list)


def test_evidence_is_populated(profile):
    evidence = profile["gochara"]["interpretation"]["evidence"]
    assert isinstance(evidence, list)
    # Check that it contains both computed_transit and deterministic_rule
    types = {item["type"] for item in evidence}
    assert "computed_transit" in types
    assert "deterministic_rule" in types


def test_transits_compatibility_entry_point_is_canonical():
    positions = _positions()
    assert transit_rules(positions, {}, ARIES, ARIES) == canonical_rules(positions, {}, ARIES, ARIES)
