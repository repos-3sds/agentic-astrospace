"""Window alerts: one push shortly before each named timing window.

The ephemeris is stubbed except in the last test, which checks the real
windows engine feeds the scheduler the names the reader asked for.
"""
from datetime import date, datetime, time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from astrospace.db import crud, crud_mobile as cm
from astrospace.db.database import Base
from astrospace.db.models import NotificationJob
from astrospace.notifications.window_alerts import schedule_window_alerts, windows_for

ME = "user-me"
# 2026-10-16 in Asia/Kolkata (+05:30). 03:30 UTC is 09:00 IST.
NOW = datetime(2026, 10, 16, 3, 30)


def w(name, start, end, kind="inauspicious", note=None):
    out = {
        "name": name, "kind": kind, "start": start[11:16], "end": end[11:16],
        "start_iso": start, "end_iso": end,
    }
    if note:
        out["note"] = note
    return out


def fake_windows(kundli, day, tz_name):
    if day != date(2026, 10, 16):
        return [w("Brahma Muhurta", "2026-10-17T04:40:00+05:30", "2026-10-17T05:28:00+05:30", "auspicious")]
    return [
        w("Rahu Kalam", "2026-10-16T10:30:00+05:30", "2026-10-16T12:00:00+05:30"),
        w("Yamaganda", "2026-10-16T15:00:00+05:30", "2026-10-16T16:30:00+05:30"),
        w("Durmuhurta", "2026-10-16T08:40:00+05:30", "2026-10-16T09:28:00+05:30"),  # already begun
        w("Gulika Kalam", "2026-10-16T09:20:00+05:30", "2026-10-16T10:50:00+05:30"),  # lead time passed
        w("Abhijit Muhurta", "2026-10-16T11:45:00+05:30", "2026-10-16T12:33:00+05:30", "auspicious",
          note="Not observed on Wednesday"),
    ]


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    crud.create_kundli(session, {
        "user_id": ME, "name": "Me", "relation": "self",
        "birth_year": 1991, "birth_month": 8, "birth_day": 14,
        "birth_hour": 6, "birth_minute": 12,
        "birth_city": "Vijayawada", "birth_nation": "IN",
    })
    cm.upsert_push_token(session, ME, "fcm", "tok-me", timezone="Asia/Kolkata")
    yield session
    session.close()


def by_name(jobs):
    return {j.payload["window"]: j for j in jobs}


def test_one_alert_per_upcoming_window_at_lead_time(db):
    jobs = by_name(schedule_window_alerts(db, now=NOW, windows=fake_windows))
    assert set(jobs) == {"Rahu Kalam", "Yamaganda", "Gulika Kalam", "Abhijit Muhurta", "Brahma Muhurta"}
    # 10:30 IST minus the default 45 minutes is 09:45 IST, 04:15 UTC.
    assert jobs["Rahu Kalam"].scheduled_for == datetime(2026, 10, 16, 4, 15)
    # Lead time already passed but the window has not begun: send now.
    assert jobs["Gulika Kalam"].scheduled_for == NOW
    # Tomorrow's pre-dawn window is queued today.
    assert jobs["Brahma Muhurta"].scheduled_for == datetime(2026, 10, 16, 22, 25)


def test_copy_states_the_window_without_fear(db):
    jobs = by_name(schedule_window_alerts(db, now=NOW, windows=fake_windows))
    assert jobs["Rahu Kalam"].title == "Rahu Kalam at 10:30"
    assert jobs["Rahu Kalam"].body == "Rahu Kalam runs 10:30–12:00."
    assert jobs["Abhijit Muhurta"].body.endswith("Not observed on Wednesday.")
    assert all(j.deep_link == "/m/today" for j in jobs.values())


def test_rerun_is_idempotent(db):
    first = schedule_window_alerts(db, now=NOW, windows=fake_windows)
    second = schedule_window_alerts(db, now=NOW, windows=fake_windows)
    assert {j.id for j in first} == {j.id for j in second}
    assert db.query(NotificationJob).count() == 5


def test_lead_time_preference_is_used(db):
    cm.set_notification_preference(db, ME, "window_alert", lead_time_minutes=15)
    jobs = by_name(schedule_window_alerts(db, now=NOW, windows=fake_windows))
    assert jobs["Rahu Kalam"].scheduled_for == datetime(2026, 10, 16, 4, 45)


def test_disabled_preference_is_respected(db):
    cm.set_notification_preference(db, ME, "window_alert", enabled=False)
    assert schedule_window_alerts(db, now=NOW, windows=fake_windows) == []


def test_quiet_hours_drop_alerts_inside_them(db):
    cm.set_notification_preference(db, ME, "window_alert",
                                   quiet_hours_start=time(22, 0), quiet_hours_end=time(6, 0))
    jobs = by_name(schedule_window_alerts(db, now=NOW, windows=fake_windows))
    assert "Brahma Muhurta" not in jobs
    assert "Rahu Kalam" in jobs


def test_window_engine_failure_skips_only_that_day(db):
    def broken(kundli, day, tz_name):
        raise ValueError("City not in offline database")
    assert schedule_window_alerts(db, now=NOW, windows=broken) == []


def test_real_windows_include_every_named_kind(db):
    kundli = crud.list_kundlis(db, ME)[0]
    names = {w["name"] for w in windows_for(kundli, date(2026, 10, 16), "Asia/Kolkata")}
    assert {"Rahu Kalam", "Yamaganda", "Gulika Kalam", "Durmuhurta",
            "Brahma Muhurta", "Abhijit Muhurta"} <= names


def test_city_change_cancels_the_old_place_and_queues_the_new(db):
    """Retest of build 487: after switching to London, alerts queued for the
    old place still went out on the old clock."""
    schedule_window_alerts(db, now=NOW, windows=fake_windows)
    crud.upsert_user_settings(db, ME, {
        "timezone_mode": "panchanga_place",
        "panchanga_place": {"city": "London", "nation": "GB", "timezone": "Europe/London"},
    })
    seen = {}

    def london(kundli, day, tz_name, city=None, nation=None):
        seen.update(city=city, nation=nation, tz=tz_name)
        return [w("Rahu Kalam", "2026-10-16T13:30:00+01:00", "2026-10-16T15:00:00+01:00")]

    jobs = schedule_window_alerts(db, now=NOW, windows=london)
    assert seen == {"city": "London", "nation": "GB", "tz": "Europe/London"}
    assert [j.payload["start"] for j in jobs] == ["2026-10-16T13:30:00+01:00"] * 2
    pending = db.query(NotificationJob).filter(NotificationJob.status == "pending").all()
    assert {j.payload["start"] for j in pending} == {"2026-10-16T13:30:00+01:00"}


def test_a_failed_day_cancels_nothing(db):
    schedule_window_alerts(db, now=NOW, windows=fake_windows)

    def broken_tomorrow(kundli, day, tz_name):
        if day != date(2026, 10, 16):
            raise ValueError("no ephemeris")
        return fake_windows(kundli, day, tz_name)

    schedule_window_alerts(db, now=NOW, windows=broken_tomorrow)
    names = {j.payload["window"] for j in db.query(NotificationJob).filter(NotificationJob.status == "pending")}
    assert "Brahma Muhurta" in names
