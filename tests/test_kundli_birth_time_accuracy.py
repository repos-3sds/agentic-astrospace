"""birth_time_accuracy travels through the kundli API instead of a notes hack."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from astrospace.api.kundli_routes import KundliCreate, KundliUpdate, _kundli_to_dict
from astrospace.db.models import Kundli


def _create(**overrides) -> KundliCreate:
    base = dict(name="A", birth_year=1990, birth_month=1, birth_day=1, birth_city="Hyderabad", birth_nation="IN")
    return KundliCreate(**{**base, **overrides})


def test_create_defaults_to_exact_and_accepts_the_three_values():
    assert _create().birth_time_accuracy == "exact"
    for value in ("exact", "approximate", "unknown"):
        assert _create(birth_time_accuracy=value).birth_time_accuracy == value


def test_create_rejects_other_values():
    with pytest.raises(ValidationError):
        _create(birth_time_accuracy="guess")


def test_update_is_optional_and_validated():
    assert KundliUpdate().birth_time_accuracy is None
    assert KundliUpdate(birth_time_accuracy="approximate").birth_time_accuracy == "approximate"
    with pytest.raises(ValidationError):
        KundliUpdate(birth_time_accuracy="precise")


def test_response_includes_accuracy_and_backfills_legacy_rows():
    row = Kundli(name="A", birth_year=1990, birth_month=1, birth_day=1, birth_hour=6, birth_minute=0,
                 birth_city="Hyderabad", birth_nation="IN", birth_time_accuracy="approximate")
    assert _kundli_to_dict(row)["birth_time_accuracy"] == "approximate"
    legacy = Kundli(name="B", birth_year=1990, birth_month=1, birth_day=1, birth_hour=6, birth_minute=0,
                    birth_city="Hyderabad", birth_nation="IN")
    legacy.birth_time_accuracy = None
    assert _kundli_to_dict(legacy)["birth_time_accuracy"] == "exact"
