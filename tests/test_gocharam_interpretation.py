"""Canonical Gocharam interpretation contract and consumer consistency."""

from datetime import datetime, timezone

import pytest

from astrospace.core.vedic.chart import VedicChart
from astrospace.core.vedic.gocharam import gochara_rules as canonical_rules
from astrospace.core.vedic.gocharam import gocharam_profile
from astrospace.core.vedic.gocharam.build_content_kb import PLANETS, build, validate
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
    assert interpretation["schema_version"] == "gocharam.interpretation.v3"
    assert interpretation["mode"] == "deterministic_cited_kb"
    assert interpretation["library_version"] == "astrospace-gocharam-kb-2026.07.1"
    assert interpretation["sources"]


def test_matched_rules_are_populated(profile):
    matched_rules = profile["gochara"]["interpretation"]["matched_rules"]
    baseline = [row for row in matched_rules if row["kind"] == "baseline_placement"]
    assert len(baseline) == 9
    assert {row["planet"] for row in baseline} == set(PLANETS)
    assert all(row["modifiers"] for row in baseline)
    assert profile["gochara"]["interpretation"]["synthesis"]["counts"]


def test_domain_readings_are_evidence_bearing(profile):
    interpretation = profile["gochara"]["interpretation"]
    domains = interpretation["domains"]
    assert {row["id"] for row in domains} == {
        "career",
        "money",
        "relationships",
        "health_energy",
        "learning_travel",
        "inner_life",
    }
    assert all(row["reading"] and row["rationale"] for row in domains)
    assert all(row["evidence_ids"] for row in domains)
    assert all(row["range_outlook"]["days"] == 90 for row in domains)


def test_range_outlook_changes_with_requested_horizon():
    chart = VedicChart("Range-specific", 1990, 1, 1, 12, 0, **DELHI)
    selected = datetime(2026, 7, 14, 12, tzinfo=timezone.utc)
    short = chart.gocharam(scan_days=30, as_of=selected)["gochara"]["interpretation"]["range_outlook"]
    long = chart.gocharam(scan_days=365, as_of=selected)["gochara"]["interpretation"]["range_outlook"]
    assert short["days"] == 30
    assert long["days"] == 365
    assert short["title"] != long["title"]
    assert short["reading"] != long["reading"]
    assert long["event_count"] >= short["event_count"]


def test_knowledge_base_has_every_planet_house_once():
    kb = build()
    validate(kb)
    baseline = [row for row in kb["rules"] if row["kind"] == "baseline_placement"]
    assert len(baseline) == 108
    assert {
        (row["planet"], row["houses"][0])
        for row in baseline
    } == {(planet, house) for planet in PLANETS for house in range(1, 13)}
    assert all(row["source_id"] for row in baseline)
    assert all(row["claim_status"] == "classical_verdict_with_editorial_synthesis" for row in baseline)


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
