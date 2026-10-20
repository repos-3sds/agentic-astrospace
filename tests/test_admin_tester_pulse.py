"""Tester pulse in the admin console: counts and times, never question text."""
from datetime import datetime, timezone

from astrospace.admin.tester_pulse import tester_pulse as build_pulse
from astrospace.api import admin_routes

# 09:30 UTC is 15:00 in India.
NOW = datetime(2026, 10, 20, 9, 30, tzinfo=timezone.utc)

USERS = [
    {"id": "u1", "email": "dhanvi@example.com", "created_at": "2026-10-20 08:47:52+00",
     "last_sign_in_at": "2026-10-20T09:02:00Z", "user_metadata": {"full_name": "D V"}},
    {"id": "u2", "email": "lalitha@example.com", "created_at": "2026-07-18T11:50:00Z",
     "last_sign_in_at": "2026-10-19T10:00:00Z", "user_metadata": {}},
    {"id": "u3", "email": "quiet@example.com", "created_at": "2026-10-17T07:00:00Z",
     "last_sign_in_at": None, "user_metadata": {}},
]
KUNDLIS = [
    {"id": "k1", "user_id": "u1", "kind": "profile", "relation": "self", "name": "Dhanvi", "archived_at": None},
    {"id": "k2", "user_id": "u1", "kind": "profile", "relation": "mother", "name": "Amma", "archived_at": None},
    {"id": "k3", "user_id": "u2", "kind": "profile", "relation": "self", "name": "Lalitha", "archived_at": None},
    {"id": "k4", "user_id": "u2", "kind": "prospect", "relation": "friend", "name": "X", "archived_at": None},
    {"id": "k5", "user_id": "u2", "kind": "profile", "relation": "friend", "name": "Y",
     "archived_at": "2026-10-01T00:00:00Z"},
]
THREADS = [{"id": "t1", "user_id": "u2"}]
QUESTIONS = [
    {"thread_id": "t1", "created_at": "2026-10-19T10:05:00Z"},
    {"thread_id": "t1", "created_at": "2026-10-20T09:10:00Z"},
]


def _pulse():
    return build_pulse(USERS, KUNDLIS, THREADS, QUESTIONS, now=NOW)


def test_people_are_named_by_their_own_chart_and_counted():
    people = {p["id"]: p for p in _pulse()["people"]}
    assert people["u1"]["name"] == "Dhanvi"
    assert people["u1"]["charts"] == 2
    assert people["u2"]["charts"] == 1  # prospects and archived charts are not counted
    assert people["u2"]["questions"] == 2
    assert people["u3"]["name"] is None


def test_today_is_an_india_day():
    pulse = _pulse()
    people = {p["id"]: p for p in pulse["people"]}
    assert people["u1"]["joined_today"] and not people["u2"]["joined_today"]
    assert people["u2"]["active_today"]  # asked today, though last signed in yesterday
    assert not people["u3"]["active_today"]
    summary = pulse["summary"]
    assert summary == {"accounts": 3, "joined_today": 1, "active_today": 2, "asked_ever": 1,
                       "first_question_today": 0, "questions_today": 1, "never_asked": 2}


def test_fourteen_days_end_today():
    daily = _pulse()["daily"]
    assert len(daily) == 14 and daily[-1]["day"] == "2026-10-20"
    assert daily[-1] == {"day": "2026-10-20", "new_accounts": 1, "questions": 1}
    assert daily[-2]["questions"] == 1


def test_newest_sign_in_first_and_no_question_text():
    pulse = _pulse()
    assert [p["id"] for p in pulse["people"]][:2] == ["u1", "u2"]
    assert "content" not in str(pulse)


def test_route_is_for_full_administrators_only():
    from typing import get_type_hints

    from astrospace.admin.security import FullAdminUser

    assert get_type_hints(admin_routes.tester_activity, include_extras=True)["user"] == FullAdminUser
