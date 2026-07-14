from pathlib import Path
import json

import pytest

from astrospace.core.vedic.chart import VedicChart


FIXTURE = Path(__file__).with_name("golden_charts.json")


def _charts():
    payload = json.loads(FIXTURE.read_text())
    return payload["charts"]


@pytest.mark.parametrize("case", _charts(), ids=lambda row: row["id"])
def test_golden_chart_basics(case):
    birth = case["birth"]
    conventions = case.get("conventions", {})
    chart = VedicChart(
        birth["name"],
        birth["year"],
        birth["month"],
        birth["day"],
        birth["hour"],
        birth["minute"],
        birth["city"],
        birth["nation"],
        ayanamsha=conventions.get("ayanamsha", "lahiri"),
        node_type=conventions.get("node_type", "mean"),
    )
    expected = case["expected"]
    details = chart.planet_details()
    moon = details["Moon"]
    dashas = chart.dashas()

    assert chart.lagna_details()["sign"] == expected["lagna_sign"]
    assert moon["sign"] == expected["moon"]["sign"]
    assert moon["nakshatra"] == expected["moon"]["nakshatra"]
    assert moon["nakshatra_pada"] == expected["moon"]["pada"]
    assert chart.panchanga["vara"]["name"] == expected["panchanga"]["vara"]
    assert dashas["birth_nakshatra"]["lord"] == expected["dasha"]["birth_nakshatra_lord"]

    # Optional extras, asserted only where the external source states them.
    for planet, sign in expected.get("planet_signs", {}).items():
        assert details[planet]["sign"] == sign, planet
    for planet, flag in expected.get("retrograde", {}).items():
        assert details[planet]["retrograde"] is flag, planet


def test_golden_fixture_marks_non_authoritative_cases():
    for case in _charts():
        if case["status"] != "verified_external":
            assert "replace with externally verified chart" in case["source"].lower()
