"""Clock change notices: one calm push the evening before daylight saving
moves a reader's clock, and the timings that follow the change on their own."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from astrospace.db import crud_mobile as cm
from astrospace.db.database import Base
from astrospace.db.models import NotificationJob
from astrospace.notifications.clock_change import (
    copy_for, next_change, schedule_clock_change_notices,
)

TORONTO = "user-toronto"
LA = "user-la"
INDIA = "user-india"
# Thu 29 Oct 2026, 12:00 UTC. US and Canada fall back at 2 am on Sun 1 Nov.
THURSDAY = datetime(2026, 10, 29, 12, 0)
# Sat 31 Oct 2026, 15:00 UTC: 11 am in Toronto, 8 am in Los Angeles.
SATURDAY = datetime(2026, 10, 31, 15, 0)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    cm.upsert_push_token(session, TORONTO, "fcm", "tok-to", timezone="America/Toronto")
    cm.upsert_push_token(session, LA, "apns", "tok-la", timezone="America/Los_Angeles")
    cm.upsert_push_token(session, INDIA, "fcm", "tok-in", timezone="Asia/Kolkata")
    yield session
    session.close()


def _by_user(jobs):
    return {j.user_id: j for j in jobs}


def test_finds_the_us_fall_back():
    change = next_change(ZoneInfo("America/New_York"), datetime(2026, 10, 31, 12, tzinfo=ZoneInfo("UTC")))
    assert change["at"] == datetime(2026, 11, 1, 6, 0, tzinfo=ZoneInfo("UTC"))
    assert change["shift_minutes"] == -60
    assert change["old_wall"] == datetime(2026, 11, 1, 2, 0)
    assert change["new_wall"] == datetime(2026, 11, 1, 1, 0)


def test_india_never_changes():
    assert next_change(ZoneInfo("Asia/Kolkata"), datetime(2026, 10, 31, tzinfo=ZoneInfo("UTC")),
                       within=timedelta(days=366)) is None


def test_copy_is_plain_and_names_the_clock_both_ways():
    back = next_change(ZoneInfo("America/Toronto"), datetime(2026, 10, 31, 12, tzinfo=ZoneInfo("UTC")))
    assert copy_for(back) == (
        "Clocks go back one hour tonight",
        "At 2 am it becomes 1 am. Your Rahu Kalam, sunrise and alarms will follow the new time on their own.",
    )
    forward = next_change(ZoneInfo("Europe/London"), datetime(2027, 3, 27, 12, tzinfo=ZoneInfo("UTC")))
    assert copy_for(forward)[0] == "Clocks go forward one hour tonight"
    assert copy_for(forward)[1].startswith("At 1 am it becomes 2 am.")
    lord_howe = next_change(ZoneInfo("Australia/Lord_Howe"), datetime(2027, 4, 3, 0, tzinfo=ZoneInfo("UTC")))
    assert copy_for(lord_howe)[0] == "Clocks go back 30 minutes tonight"


def test_queued_for_six_pm_the_evening_before_in_each_zone(db):
    jobs = _by_user(schedule_clock_change_notices(db, now=SATURDAY, environ={}))
    assert set(jobs) == {TORONTO, LA}
    # 18:00 Sat in Toronto (EDT, -4) and Los Angeles (PDT, -7).
    assert jobs[TORONTO].scheduled_for == datetime(2026, 10, 31, 22, 0)
    assert jobs[LA].scheduled_for == datetime(2026, 11, 1, 1, 0)
    assert jobs[TORONTO].title == "Clocks go back one hour tonight"
    assert jobs[TORONTO].deep_link == "/m/today"


def test_nothing_queued_days_ahead_and_runs_are_idempotent(db):
    assert schedule_clock_change_notices(db, now=THURSDAY, environ={}) == []
    schedule_clock_change_notices(db, now=SATURDAY, environ={})
    schedule_clock_change_notices(db, now=SATURDAY + timedelta(minutes=15), environ={})
    assert db.query(NotificationJob).count() == 2


def test_late_runs_send_now_but_never_overnight(db):
    # 7:30 pm in Toronto: sends at once.
    jobs = _by_user(schedule_clock_change_notices(db, now=datetime(2026, 10, 31, 23, 30), environ={}))
    assert jobs[TORONTO].scheduled_for == datetime(2026, 10, 31, 23, 30)
    # 11:30 pm in Toronto: too late to ring a phone for it.
    db.query(NotificationJob).delete()
    db.commit()
    jobs = _by_user(schedule_clock_change_notices(db, now=datetime(2026, 11, 1, 3, 30), environ={}))
    assert TORONTO not in jobs


def test_respects_settings(db):
    for cat in ("morning_brief", "window_alert", "festival_reminder", "remedy_reminder"):
        cm.set_notification_preference(db, TORONTO, cat, enabled=False)
    # Window alerts off alone (the phone's own alarms took them over) still hears it.
    cm.set_notification_preference(db, LA, "window_alert", enabled=False)
    jobs = _by_user(schedule_clock_change_notices(db, now=SATURDAY, environ={}))
    assert set(jobs) == {LA}


def test_switch_off_sends_nothing(db):
    assert schedule_clock_change_notices(db, now=SATURDAY, environ={"CLOCK_CHANGE_NOTICES": "off"}) == []


def test_phone_last_used_sets_the_clock(db):
    # A reader with an old Indian token and a newer phone in Toronto.
    cm.upsert_push_token(db, INDIA, "apns", "tok-in-2", timezone="America/Toronto")
    token = db.query(cm.PushToken).filter_by(token="tok-in-2").one()
    token.last_seen_at = datetime.utcnow() + timedelta(days=1)
    db.commit()
    assert INDIA in _by_user(schedule_clock_change_notices(db, now=SATURDAY, environ={}))


def test_email_only_for_readers_without_a_phone(db):
    for user, tz in ((TORONTO, "America/Toronto"), ("user-email-only", "America/Toronto")):
        cm.upsert_email_recipient(db, user, f"{user}@example.com", timezone=tz)
        cm.set_notification_preference(db, user, "daily_email", enabled=True, channels=["email"])
    jobs = schedule_clock_change_notices(db, now=SATURDAY, environ={})
    emails = [j for j in jobs if (j.payload or {}).get("channel") == "email"]
    assert [j.user_id for j in emails] == ["user-email-only"]
    assert emails[0].category == "daily_email"
    assert emails[0].scheduled_for == datetime(2026, 10, 31, 22, 0)


@pytest.mark.parametrize("city,nation,lat,lng,tz,day", [
    ("New York", "US", 40.7128, -74.006, "America/New_York", date(2026, 11, 1)),
    ("Toronto", "CA", 43.65, -79.38, "America/Toronto", date(2026, 11, 1)),
    ("Sydney", "AU", -33.87, 151.21, "Australia/Sydney", date(2027, 4, 4)),
])
def test_timings_follow_the_change(city, nation, lat, lng, tz, day):
    """What the copy promises: every time the phone's alarms are built from
    carries the offset in force at that moment, so they ring on the new clock."""
    from astrospace.core.vedic.panchanga_day import daily_panchanga

    zone = ZoneInfo(tz)
    for offset in (-1, 0, 1):
        d = day + timedelta(days=offset)
        p = daily_panchanga(d.year, d.month, d.day, city, nation, lat, lng, tz)
        isos = [p["sunrise_iso"], p["sunset_iso"]]
        for w in p["windows"]["inauspicious"] + p["windows"]["auspicious"]:
            isos += [w["start_iso"], w["end_iso"]]
        for iso in isos:
            t = datetime.fromisoformat(iso)
            assert t.utcoffset() == t.astimezone(zone).utcoffset(), (d, iso)
