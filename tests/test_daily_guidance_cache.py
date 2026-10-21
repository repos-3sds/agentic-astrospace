"""The daily guidance cache actually hits (production audit 2026-10-15, P2).

Its key included `datetime.now()` to the microsecond, so no two requests
ever shared an entry.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from astrospace.context import daily_service
from astrospace.api.auth import AuthUser, current_user
from astrospace.db import crud, get_db
from astrospace.db.database import Base
from main import app

ME = "daily-reader"


def test_now_is_bucketed_to_the_quarter_hour(monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 10, 15, 6, 44, 59, 999999, tzinfo=tz)

    monkeypatch.setattr(daily_service, "datetime", Clock)
    bucket = daily_service.bucketed_now(ZoneInfo("Asia/Kolkata"))
    assert (bucket.hour, bucket.minute, bucket.second, bucket.microsecond) == (6, 30, 0, 0)


@pytest.fixture()
def client():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine)

    def override_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    with factory() as db:
        kundli = crud.create_kundli(db, {
            "user_id": ME, "name": "Reader", "relation": "self",
            "birth_year": 1991, "birth_month": 8, "birth_day": 14,
            "birth_hour": 6, "birth_minute": 12,
            "birth_city": "Vijayawada", "birth_nation": "IN",
        }).id
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[current_user] = lambda: AuthUser(id=ME, role="dev")
    try:
        yield TestClient(app), kundli
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(current_user, None)


def test_repeat_requests_share_one_computation(client, monkeypatch):
    test_client, kundli = client
    calls = []

    def fake_guidance(chart, relation=None, as_of=None, **kwargs):
        calls.append(as_of)
        return {"as_of": as_of.isoformat(), "provenance": {"place": {}}}

    monkeypatch.setattr(daily_service, "daily_guidance", fake_guidance)
    daily_service.cached_daily_guidance.cache_clear()
    first = test_client.get(f"/api/v1/context/{kundli}/daily")
    second = test_client.get(f"/api/v1/context/{kundli}/daily")
    assert first.status_code == second.status_code == 200
    assert len(calls) == 1
    assert calls[0].second == 0 and calls[0].microsecond == 0
    daily_service.cached_daily_guidance.cache_clear()
