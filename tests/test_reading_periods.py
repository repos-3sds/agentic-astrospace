"""Which period a reading belongs to, and how often one gets written.

Pins the fixes for the reading-card findings of the production audit
(2026-10-15, section 2):

- R1: a weekly reading was labelled "Week of <today>", so the label changed
  every day, the cache lookup missed, and each day wrote another "Version 1".
- R2: the list endpoint could not say which rows belong to the current
  period, so three different weeks showed as "Version 1 / 1 / 1".
- R6: nothing stopped two concurrent "New version" taps from paying for two
  generations, and nothing capped regenerations.
"""
import threading
import time
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from astrospace.agents.period_agent import PeriodAgent
from astrospace.api import reading_routes
from astrospace.api.auth import AuthUser, current_user
from astrospace.api.reading_routes import _period_label, _period_window
from astrospace.db import crud, get_db
from astrospace.db.database import Base

ME = "55555555-5555-4555-8555-555555555555"
IST = ZoneInfo("Asia/Kolkata")

READING = """## Overall theme
Jupiter transits your 10th house from the Moon, which supports visible progress at work.

## Guidance
- Focus on finishing open work rather than starting new projects this week.
"""


def ist(day: int, hour: int = 10, month: int = 10) -> datetime:
    return datetime(2026, month, day, hour, 0, tzinfo=IST)


class TestPeriodLabel:
    @pytest.mark.parametrize("day", [12, 13, 15, 18])
    def test_every_day_of_a_week_shares_its_monday_label(self, day):
        # Mon Oct 12 .. Sun Oct 18 2026
        assert _period_label("weekly", ist(day)) == "Week of Oct 12, 2026"

    def test_the_next_monday_starts_a_new_week(self):
        assert _period_label("weekly", ist(19)) == "Week of Oct 19, 2026"

    def test_week_label_crosses_months(self):
        # Thu Oct 1 2026 belongs to the week starting Mon Sep 28.
        assert _period_label("weekly", ist(1)) == "Week of Sep 28, 2026"

    def test_label_follows_the_kundli_local_date(self):
        # 20:00 UTC on Sunday Oct 18 is already Monday Oct 19 in India.
        utc_sunday = datetime(2026, 10, 18, 20, 0, tzinfo=ZoneInfo("UTC"))
        assert _period_label("weekly", utc_sunday) == "Week of Oct 12, 2026"
        assert _period_label("weekly", utc_sunday.astimezone(IST)) == "Week of Oct 19, 2026"
        assert _period_label("daily", utc_sunday.astimezone(IST)) == "2026-10-19"

    def test_other_periods(self):
        assert _period_label("daily", ist(15)) == "2026-10-15"
        assert _period_label("monthly", ist(15)) == "October 2026"
        assert _period_label("quarterly", ist(15)) == "Q4 2026"
        assert _period_label("yearly", ist(15)) == "2026"

    def test_window_is_the_whole_calendar_period(self):
        assert _period_window("weekly", ist(15)) == ("2026-10-12", "2026-10-18")
        assert _period_window("daily", ist(15)) == ("2026-10-15", "2026-10-15")
        assert _period_window("monthly", ist(15)) == ("2026-10-01", "2026-10-31")
        assert _period_window("quarterly", ist(15)) == ("2026-10-01", "2026-12-31")
        assert _period_window("yearly", ist(15)) == ("2026-01-01", "2026-12-31")


@pytest.fixture()
def env():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    db = Session()
    kundli = crud.create_kundli(db, {
        "user_id": ME, "name": "Mine", "relation": "self",
        "birth_year": 1990, "birth_month": 3, "birth_day": 15,
        "birth_hour": 8, "birth_minute": 30,
        "birth_city": "Hyderabad", "birth_nation": "IN",
    }).id
    db.close()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[current_user] = lambda: AuthUser(id=ME, email="me@astrospace.dev", role="dev")
    try:
        yield {"client": TestClient(app), "kundli": kundli}
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(current_user, None)


def _at(when: datetime):
    return patch.object(reading_routes, "_kundli_now", return_value=when)


def _generate(env, period="weekly", force=False):
    return env["client"].post(
        f"/api/v1/readings/{env['kundli']}/generate", json={"period": period, "force_refresh": force},
    )


def test_a_weekly_reading_is_reused_for_the_whole_week(env):
    with patch.object(PeriodAgent, "run", return_value=READING) as run:
        with _at(ist(13)):
            first = _generate(env).json()
        with _at(ist(17)):
            again = _generate(env).json()
    assert run.call_count == 1, "Friday reuses Tuesday's reading instead of writing a new one"
    assert again["cached"] is True and again["id"] == first["id"]
    assert first["period_label"] == "Week of Oct 12, 2026"
    assert (first["period_start"], first["period_end"]) == ("2026-10-12", "2026-10-18")
    assert first["is_current_period"] is True


def test_claims_cover_the_calendar_week(env):
    with patch.object(PeriodAgent, "run", return_value=READING), _at(ist(15)):
        _generate(env)
        claims = env["client"].get(f"/api/v1/readings/{env['kundli']}/claims").json()
    assert claims
    assert {(c["target_start_date"], c["target_end_date"]) for c in claims} == {("2026-10-12", "2026-10-18")}


def test_list_marks_which_rows_are_this_period(env):
    with patch.object(PeriodAgent, "run", return_value=READING):
        with _at(ist(7)):
            last_week = _generate(env).json()
        with _at(ist(14)):
            this_week = _generate(env).json()
            this_week_v2 = _generate(env, force=True).json()
        with _at(ist(15)):
            rows = env["client"].get(f"/api/v1/readings/{env['kundli']}?period=weekly").json()

    by_id = {r["id"]: r for r in rows}
    assert by_id[this_week["id"]]["is_current_period"] is True
    assert by_id[this_week_v2["id"]]["is_current_period"] is True
    assert by_id[last_week["id"]]["is_current_period"] is False
    # Versions count within a label, so last week's only reading is version 1
    # and this week's second one is version 2.
    assert by_id[last_week["id"]]["version"] == 1
    assert by_id[this_week_v2["id"]]["version"] == 2
    assert by_id[last_week["id"]]["period_start"] == "2026-10-05"
    assert by_id[last_week["id"]]["period_end"] == "2026-10-11"


def test_a_concurrent_new_version_joins_the_one_in_flight(env):
    started, release = threading.Event(), threading.Event()
    calls = []

    def slow_run(self, prompt):
        calls.append(prompt)
        started.set()
        assert release.wait(10)
        return READING

    results = {}

    def post(name):
        results[name] = _generate(env, force=True)

    with patch.object(PeriodAgent, "run", slow_run), _at(ist(15)):
        first = threading.Thread(target=post, args=("first",))
        first.start()
        assert started.wait(10)
        second = threading.Thread(target=post, args=("second",))
        second.start()
        # Release the first only once the second is waiting on it.
        key = (env["kundli"], "weekly", "Week of Oct 12, 2026")
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            entry = reading_routes._IN_FLIGHT.get(key)
            if entry is not None and entry.waiters >= 1:
                break
            time.sleep(0.01)
        release.set()
        first.join(10)
        second.join(10)

    assert len(calls) == 1, "the second tap must not pay for a second generation"
    a, b = results["first"], results["second"]
    assert a.status_code == 200 and b.status_code == 200
    assert a.json()["id"] == b.json()["id"]
    assert b.json()["cached"] is True
    assert reading_routes._IN_FLIGHT == {}


def test_new_versions_are_capped_per_day(env):
    with patch.object(PeriodAgent, "run", return_value=READING) as run, _at(ist(15)):
        assert _generate(env).status_code == 200  # the first reading is not counted
        for _ in range(reading_routes.MAX_NEW_VERSIONS_PER_DAY):
            assert _generate(env, force=True).status_code == 200
        calls = run.call_count
        refused = _generate(env, force=True)
        assert run.call_count == calls, "a refused request must not call the model"
        # Reading what is there is never capped.
        assert _generate(env).status_code == 200
    assert refused.status_code == 429
    assert "tomorrow" in refused.json()["detail"]

    # The next local day has a fresh allowance.
    with patch.object(PeriodAgent, "run", return_value=READING), _at(ist(16)):
        assert _generate(env, force=True).status_code == 200


def test_a_failed_generation_releases_the_guard(env):
    with patch.object(PeriodAgent, "run", side_effect=RuntimeError("provider down")), _at(ist(15)):
        assert _generate(env, force=True).status_code == 503
    assert reading_routes._IN_FLIGHT == {}
    with patch.object(PeriodAgent, "run", return_value=READING), _at(ist(15)):
        assert _generate(env, force=True).status_code == 200
