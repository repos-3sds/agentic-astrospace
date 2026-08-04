"""Canonical Gocharam interpretation contract and consumer consistency."""

import json
import re
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
    assert interpretation["library_version"] == "astrospace-gocharam-kb-2026.07.2"
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


# ── Content-quality guardrails (US-GOC-021) ─────────────────────────────────
#
# These exist to catch a regression back to the pre-revamp content library,
# where 94 of 108 baseline placements were interchangeable mad-libs sentences
# with the planet name and a keyword swapped in (including an "1th/2th/3th
# house" ordinal bug). They must fail red against that library and pass once
# US-GOC-017/018/019 land.

def test_no_ordinal_typos_in_content_kb():
    kb = build()
    text = json.dumps(kb)
    bad = set(re.findall(r"\b(?:1th|2th|3th)\b", text))
    assert not bad, f"bad ordinals found in content_kb: {bad}"


def test_content_is_not_templated_boilerplate():
    kb = build()
    text = json.dumps(kb)
    # Fingerprints of the old mad-libs generator: identical sentences reused
    # verbatim across dozens of unrelated planet/house placements. A little
    # incidental reuse is fine; wholesale reuse means the generator regressed.
    boilerplate_markers = [
        "align harmoniously with the bhava, promoting growth",
        "Remedial measures (Shanti) and checking for beneficial aspects or "
        "high SAV bindus are recommended to mitigate the dosha",
    ]
    for marker in boilerplate_markers:
        count = text.count(marker)
        assert count <= 2, f"boilerplate marker appears {count} times: {marker!r}"


def test_computed_special_aspect_houses_are_correct():
    from astrospace.core.vedic.gocharam.rules import special_aspect_houses

    # Mars: special drishti on 4th/7th/8th from its transit house.
    assert special_aspect_houses("Mars", 5) == [8, 11, 12]
    # Jupiter: special drishti on 5th/7th/9th.
    assert special_aspect_houses("Jupiter", 2) == [6, 8, 10]
    # Saturn: special drishti on 3rd/7th/10th.
    assert special_aspect_houses("Saturn", 3) == [5, 9, 12]
    # Everyone else: ordinary 7th-house aspect only.
    assert special_aspect_houses("Sun", 1) == [7]
    assert special_aspect_houses("Rahu", 9) == [3]


def test_kantaka_ardhashtama_shani_name_matches_across_subsystems():
    from astrospace.core.vedic.gocharam.rules import RULE_BY_ID

    engine_name = RULE_BY_ID["gochara_kantaka_shani"].name
    kb = build()
    kb_rule = next(r for r in kb["rules"] if r["id"] == "special_ardhashtama_shani")
    assert engine_name == kb_rule["rule_name"] == "Ardhashtama Shani (Kantaka Shani)"


def test_saturn_multi_pass_detects_2022_capricorn_retrograde_return():
    """Regression fixture for US-GOC-025, anchored to a real, verifiable
    transit: Saturn (sidereal/Lahiri) entered Aquarius ~2022-04-30, then
    retrograded back into Capricorn by ~2022-07-13, and made its final entry
    into Aquarius ~2023-01-18 — confirmed directly against this app's own
    ephemeris before writing this test, not from memory.

    For a Pisces-Moon native, Sade Sati's active houses (12th/1st/2nd from
    Moon) are exactly {Aquarius, Pisces, Aries}, so this Aquarius<->Capricorn
    boundary crossing must surface as two passes — a first_entry followed by
    a retrograde_return — instead of one truncated continuous window (the
    pre-US-GOC-025 behaviour, which would only report whichever of the two
    windows touches ``as_of``).
    """
    from astrospace.core.vedic.gocharam.timeline import _label_passes, _rule_active_runs

    PISCES = 11
    as_of = datetime(2023, 3, 1, tzinfo=timezone.utc)
    runs = _rule_active_runs(as_of, "gochara_sade_sati", {}, PISCES, PISCES, "lahiri", "mean")
    passes = _label_passes(runs)

    assert len(passes) == 2
    assert passes[0]["entry_type"] == "first_entry"
    assert passes[0]["start"] == "2022-04-30"
    assert passes[0]["end"] == "2022-07-13"
    assert passes[1]["entry_type"] == "retrograde_return"
    assert passes[1]["start"] == "2023-01-18"
    assert passes[1]["end"] is None
    # Chronological order.
    assert passes[0]["end"] < passes[1]["start"]


def test_multi_pass_only_computed_for_saturn_long_cycle_rules():
    from astrospace.core.vedic.gocharam.timeline import _rule_passes

    as_of = datetime(2026, 7, 14, 12, tzinfo=timezone.utc)
    assert _rule_passes(as_of, "gochara_guru_moon_support", {}, 0, 0, "lahiri", "mean") is None
    result = _rule_passes(as_of, "gochara_sade_sati", {}, 0, 0, "lahiri", "mean")
    assert result is None or isinstance(result, list)


def test_baseline_rules_carry_computed_evidence_and_content_status():
    kb = build()
    assert kb.get("content_status") == "ai_authored_pending_astrologer_review"
    baseline = [row for row in kb["rules"] if row["kind"] == "baseline_placement"]
    for row in baseline:
        aspects = row.get("computed_evidence", {}).get("special_aspect_houses")
        assert aspects, f"missing computed_evidence.special_aspect_houses for {row['id']}"
        expected_len = 3 if row["planet"] in {"Mars", "Jupiter", "Saturn"} else 1
        assert len(aspects) == expected_len, row["id"]
