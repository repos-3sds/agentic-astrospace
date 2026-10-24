"""Vimshottari variants for Practitioner: Tribhagi, Tara starts, Lagna starts."""
from datetime import datetime, timedelta

import pytest

from astrospace.core.vedic.constants import NAKSHATRA_SPAN
from astrospace.core.vedic.dasha_variants import (
    VARIANTS,
    varga_lagna_longitude,
    variant_catalog,
    vimshottari_variant,
)
from astrospace.core.vedic.dashas import vimshottari_dasha
from astrospace.core.vedic.vargas import VARGA_FUNCTIONS
from astrospace.entitlements.registry import capability_registry

BIRTH = datetime(1990, 1, 1, 6, 0)
AS_OF = datetime(2026, 10, 24)


def _lords(payload, n=9):
    return [p["lord"] for p in payload["mahadashas"][:n]]


def test_standard_vimshottari_unchanged_by_the_scale_parameter():
    d = vimshottari_dasha(10.0, BIRTH, AS_OF)
    assert d["system"] == "Vimshottari"
    assert d["cycle_years"] == 120
    assert len(d["mahadashas"]) == 18  # two cycles, the first starting part-way


def test_tribhagi_is_a_third_of_each_period_and_still_spans_a_life():
    moon = NAKSHATRA_SPAN / 2  # half way through Ashwini: Ketu balance 3.5 years
    d = vimshottari_variant("tribhagi", moon, 0.0, BIRTH, AS_OF)
    assert d["cycle_years"] == 40
    first, venus = d["mahadashas"][0], d["mahadashas"][1]
    assert first["lord"] == "Ketu" and first["years"] == pytest.approx(3.5 / 3)
    assert venus["lord"] == "Venus" and venus["years"] == pytest.approx(20 / 3)
    end = datetime.fromisoformat(d["mahadashas"][-1]["end"])
    assert end - BIRTH >= timedelta(days=120 * 365.25)
    # sub-periods keep their Vimshottari shares of the shorter parent
    assert sum(a["years"] for a in venus["antardashas"]) == pytest.approx(venus["years"])


@pytest.mark.parametrize("variant,steps", [("kshema", 3), ("utpanna", 4), ("adhana", 7)])
def test_tara_starts_count_from_the_birth_star(variant, steps):
    moon = 0.25 * NAKSHATRA_SPAN  # Ashwini, a quarter gone
    d = vimshottari_variant(variant, moon, 0.0, BIRTH, AS_OF)
    expected = vimshottari_dasha(moon + steps * NAKSHATRA_SPAN, BIRTH, AS_OF)
    assert _lords(d) == _lords(expected)
    # Kshema = Rohini (Moon), Utpanna = Mrigashira (Mars), Adhana = Pushya (Saturn)
    assert d["mahadashas"][0]["lord"] == {"kshema": "Moon", "utpanna": "Mars", "adhana": "Saturn"}[variant]
    assert d["birth_nakshatra"]["elapsed_fraction"] == pytest.approx(0.25)


def test_lagna_starts_seed_from_the_varga_lagna():
    lagna = 47.3  # Taurus 17°18'
    d1 = vimshottari_variant("d1_lagna", 0.0, lagna, BIRTH, AS_OF)
    assert d1["seed"] == {"point": "D1 Lagna", "longitude": 47.3}
    d9 = vimshottari_variant("d9_lagna", 0.0, lagna, BIRTH, AS_OF)
    assert d9["seed"]["longitude"] == pytest.approx((lagna * 9) % 360)
    d10 = vimshottari_variant("d10_lagna", 0.0, lagna, BIRTH, AS_OF)
    assert _lords(d10) == _lords(vimshottari_dasha(varga_lagna_longitude(lagna, "D10"), BIRTH, AS_OF))


@pytest.mark.parametrize("varga", ["D1", "D9", "D10"])
def test_varga_longitude_lands_in_the_varga_sign(varga):
    for lon in [0.0, 3.3, 47.3, 123.45, 200.1, 299.99, 359.9]:
        assert int(varga_lagna_longitude(lon, varga) // 30) == VARGA_FUNCTIONS[varga](lon)


def test_every_variant_says_it_is_convention_dependent():
    for key in VARIANTS:
        d = vimshottari_variant(key, 100.0, 200.0, BIRTH, AS_OF)
        assert d["is_convention_dependent"] is True
        assert d["observance_note"]
        assert d["variant"] == key
    assert [row["key"] for row in variant_catalog()] == list(VARIANTS)


def test_unknown_variant_is_refused():
    with pytest.raises(ValueError):
        vimshottari_variant("d9_sun", 0.0, 0.0, BIRTH, AS_OF)


def test_variants_are_practitioner_only():
    flag = capability_registry["dashas.variants"]
    assert [flag.value_for(t) for t in ("free", "plus", "pro")] == [False, False, True]
