"""The worker builds Today's payload without reaching into the API (audit I8).

daily_briefs.py used to import `_daily_payload` from api/context_routes.py,
and four notification jobs took the timing-place rule from api/, so a
worker run loaded FastAPI routers and caught HTTPExceptions. Both now live
in astrospace/context/ and raise domain errors the routers map to 422.
"""
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from astrospace.context.daily_service import DailyGuidanceError, daily_payload
from astrospace.context.timing_place import PlaceNotFound, resolve_timing_place

NOTIFICATIONS = Path(__file__).resolve().parents[1] / "astrospace" / "notifications"


def _kundli(**overrides):
    base = dict(id="k1", name="Reader", relation="self", birth_year=1991, birth_month=8,
                birth_day=14, birth_hour=6, birth_minute=12,
                birth_city="Vijayawada", birth_nation="IN")
    return SimpleNamespace(**{**base, **overrides})


def test_no_notification_job_imports_the_api_package():
    offenders = [path.name for path in NOTIFICATIONS.glob("*.py")
                 if re.search(r"from \.\.api[ .]|import astrospace\.api", path.read_text())]
    assert offenders == []


def test_unknown_city_is_a_domain_error_not_an_http_one():
    with pytest.raises(PlaceNotFound):
        resolve_timing_place(_kundli(), city="Atlantis", nation="IN")
    with pytest.raises(DailyGuidanceError):
        daily_payload(_kundli(), "lahiri", "mean", None, None, "Atlantis", "IN")


def test_bad_birth_details_are_a_domain_error():
    with pytest.raises(DailyGuidanceError):
        daily_payload(_kundli(birth_city="Nowhere-on-earth"), "lahiri", "mean", None, None, None, None)
