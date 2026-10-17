"""Calendar Day, Today, personal panchanga and Muhurta resolve "where and
in whose clock" with one rule (api/timing_place.py). Before this, Calendar
Day took a city in the viewer's timezone and rendered its windows in the
viewer's clock, while Muhurta took the birth city in its own clock, so one
build showed Brahma Muhurta at 23:00 on one screen and 04:35 on the other.
Windows are now always in the place's clock, and every payload says which
place and why.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from astrospace.api.auth import AuthUser, current_user
from astrospace.api.timing_place import resolve_timing_place
from astrospace.db import crud, get_db
from astrospace.db.database import Base

ME = "44444444-4444-4444-8444-444444444444"


@pytest.fixture(scope="module")
def env():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    def override_current_user():
        return AuthUser(id=ME, email="me@astrospace.dev", role="dev")

    db = Session()
    kundli = crud.create_kundli(db, {
        "user_id": ME, "name": "Mine", "relation": "self",
        "birth_year": 1991, "birth_month": 8, "birth_day": 14,
        "birth_hour": 6, "birth_minute": 12,
        "birth_city": "Hyderabad", "birth_nation": "IN",
    })
    db.close()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[current_user] = override_current_user
    try:
        yield {"client": TestClient(app), "kundli": kundli}
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(current_user, None)


def _places(client, kundli_id, **params):
    """What each timing endpoint computed for: calendar intelligence, the
    personal panchanga day, muhurta search and Today's daily guidance."""
    calendar = client.get(f"/api/v1/vedic/{kundli_id}/calendar-intelligence",
                          params={"days": 3, "as_of": "2026-07-07", **params})
    today = client.get(f"/api/v1/panchanga/{kundli_id}/today",
                       params={"date": "2026-07-07", **params})
    muhurta = client.get(f"/api/v1/muhurta/{kundli_id}",
                         params={"goal": "start_journey", "date_from": "2026-07-07",
                                 "date_to": "2026-07-20", **params})
    daily = client.get(f"/api/v1/context/{kundli_id}/daily",
                       params={"as_of": "2026-07-07T09:00:00", **params})
    for res in (calendar, today, muhurta, daily):
        assert res.status_code == 200, res.text
    return calendar.json(), today.json(), muhurta.json(), daily.json()


class TestResolver:
    def test_explicit_city_wins(self, env):
        place = resolve_timing_place(env["kundli"], "America/New_York", "Chennai", "IN")
        assert (place.city, place.source) == ("Chennai", "selected")
        assert place.tz_str == "Asia/Kolkata"
        assert place.viewer_tz == "America/New_York"
        assert place.today_tz == "America/New_York"

    def test_viewer_timezone_picks_a_city_in_it(self, env):
        place = resolve_timing_place(env["kundli"], "America/New_York")
        assert (place.city, place.nation, place.source) == ("New York", "US", "viewer_timezone")
        assert place.tz_str == place.viewer_tz == "America/New_York"

    def test_timezone_without_a_listed_city_falls_back_to_birth_city(self, env):
        place = resolve_timing_place(env["kundli"], "UTC")
        assert (place.city, place.source) == ("Hyderabad", "birth_city")
        assert place.tz_str == "Asia/Kolkata"
        assert place.viewer_tz == "UTC"

    def test_nothing_given_is_the_birth_city_in_its_own_clock(self, env):
        place = resolve_timing_place(env["kundli"])
        assert (place.city, place.source, place.viewer_tz) == ("Hyderabad", "birth_city", None)
        assert place.today_tz == "Asia/Kolkata"

    def test_unknown_timezone_is_a_400(self, env):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            resolve_timing_place(env["kundli"], "Mars/Olympus")
        assert exc.value.status_code == 400


class TestEndpointsAgree:
    @pytest.mark.parametrize("params, city, source, tz", [
        ({}, "Hyderabad", "birth_city", "Asia/Kolkata"),
        ({"timezone": "UTC"}, "Hyderabad", "birth_city", "Asia/Kolkata"),
        ({"timezone": "America/New_York"}, "New York", "viewer_timezone", "America/New_York"),
        ({"timezone": "America/New_York", "city": "Chennai", "nation": "IN"}, "Chennai", "selected", "Asia/Kolkata"),
    ])
    def test_all_four_report_the_same_place(self, env, params, city, source, tz):
        calendar, today, muhurta, daily = _places(env["client"], env["kundli"].id, **params)
        for place in (calendar["place"], today["place"], muhurta["place"], daily["provenance"]["place"]):
            assert place["city"] == city
            assert place["source"] == source
            assert place["timezone"] == tz
            assert place["viewer_timezone"] == params.get("timezone")
        assert calendar["timezone"] == tz
        assert calendar["provenance"]["panchanga_place"]["source"] == source

    def test_windows_are_always_in_the_place_clock(self, env):
        """A viewer on UTC still sees Hyderabad's Brahma Muhurta at the hour
        it happens in Hyderabad. Before, Calendar Day showed 23:00 and
        Muhurta 04:35 for the same window."""
        ist = _places(env["client"], env["kundli"].id)
        utc = _places(env["client"], env["kundli"].id, timezone="UTC")
        for a, b in zip(ist, utc):
            assert a.get("results", a.get("windows")) == b.get("results", b.get("windows"))
        _, today, muhurta, _ = utc
        assert muhurta["results"]
        assert muhurta["results"][0]["start_iso"].endswith("+05:30")
        assert all(w["start_iso"].endswith("+05:30")
                   for kind in today["windows"].values() for w in kind)

    def test_calendar_day_windows_match_the_panchanga_day(self, env):
        """The Calendar Day summary and the personal panchanga for the same
        date carry identical window clocks."""
        calendar, today, _, _ = _places(env["client"], env["kundli"].id, timezone="UTC")
        day = next(d for d in calendar["panchanga_days"] if d["date"] == "2026-07-07")
        summary = {(w["name"], w["start"], w["end"]) for kind in day["windows"].values() for w in kind}
        full = {(w["name"], w["start"], w["end"]) for kind in today["windows"].values() for w in kind}
        assert summary and summary <= full
        assert today["place"]["calculation_timezone"] == "Asia/Kolkata"


def test_calendar_is_computed_once_per_window_and_stays_unshared(env):
    """The app asks for the same calendar window on every open and retry;
    on Cloud Run each one cost tens of seconds of CPU (2026-10-17 logs)."""
    from astrospace.api import vedic_routes

    client, kundli_id = env["client"], env["kundli"].id
    vedic_routes._cached_calendar.cache_clear()
    params = {"days": 2, "as_of": "2026-07-09"}
    first = client.get(f"/api/v1/vedic/{kundli_id}/calendar-intelligence", params=params)
    second = client.get(f"/api/v1/vedic/{kundli_id}/calendar-intelligence", params=params)
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    info = vedic_routes._cached_calendar.cache_info()
    assert (info.misses, info.hits) == (1, 1)
