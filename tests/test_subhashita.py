"""Today's Subhashita: the corpus, the API and the daily push.

The verse for a date is fixed by its day count, so every surface (API,
push, widget) agrees without coordinating, and only today's is shown.
"""
import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from astrospace.core import subhashita
from astrospace.db import crud_mobile as cm
from astrospace.db.database import Base
from astrospace.db.models import NotificationJob
from astrospace.notifications.daily_subhashita import CATEGORY, schedule_daily_subhashita

ME = "user-me"
OTHER = "user-other"
IST = timezone(timedelta(hours=5, minutes=30))


class TestCorpus:
    def test_every_entry_is_complete_and_shareable(self):
        rows = subhashita.corpus()
        assert rows
        for row in rows:
            for field in ("id", "source", "ref", "sanskrit", "english", "meaning"):
                assert row[field].strip(), (row["id"], field)
            # Long enough to mean something, short enough for a status card.
            assert 20 <= len(row["english"]) <= 200, row["id"]
            # The meaning is one plain line under the verse, a full sentence.
            assert 15 <= len(row["meaning"]) <= 100, row["id"]
            assert row["meaning"][0].isupper() and row["meaning"].endswith("."), row["id"]
            # The Sanskrit is Devanagari, not a transliteration.
            assert any("ऀ" <= ch <= "ॿ" for ch in row["sanskrit"]), row["id"]

    def test_every_verse_is_keyed_from_a_public_domain_print(self):
        # D12: the Sanskrit is re-keyed from a print published before 1931,
        # and each entry links the scanned page it was read from.
        here = Path(subhashita.__file__).parent
        editions = json.loads((here / "editions.json").read_text(encoding="utf-8"))
        for edition in editions.values():
            assert edition["year"] < 1931 and edition["archive_id"], edition
        rows = json.loads((here / "subhashitas.json").read_text(encoding="utf-8"))
        assert len(rows) == len(subhashita.corpus())
        for row in rows:
            prov = row["provenance"]
            assert prov["edition"] in editions, row["id"]
            archive_id = editions[prov["edition"]]["archive_id"]
            assert prov["scan_page_url"].startswith(
                f"https://archive.org/details/{archive_id}/page/n"
            ), row["id"]

    def test_ids_are_unique(self):
        ids = [row["id"] for row in subhashita.corpus()]
        assert len(ids) == len(set(ids))

    def test_the_same_date_always_gives_the_same_verse(self):
        day = date(2026, 10, 17)
        assert subhashita.for_day(day) == subhashita.for_day(day)
        assert subhashita.for_day(day)["date"] == "2026-10-17"

    def test_rotation_walks_the_whole_corpus_before_repeating(self):
        rows = subhashita.corpus()
        start = date(2026, 10, 17)
        seen = [subhashita.for_day(start + timedelta(days=n))["id"] for n in range(len(rows))]
        assert len(set(seen)) == len(rows)
        assert subhashita.for_day(start + timedelta(days=len(rows)))["id"] == seen[0]

    def test_each_account_has_its_own_rotation(self):
        rows = subhashita.corpus()
        start = date(2026, 10, 17)
        readers = [f"reader-{n}" for n in range(20)]
        todays = {subhashita.for_day(start, r)["id"] for r in readers}
        assert len(todays) > 10  # not one verse for everyone
        assert subhashita.for_day(start, "reader-1") == subhashita.for_day(start, "reader-1")
        assert subhashita.for_day(start, None) == subhashita.for_day(start)
        seen = [subhashita.for_day(start + timedelta(days=n), "reader-1") for n in range(len(rows))]
        assert len({v["id"] for v in seen}) == len(rows)
        assert all(a["source"] != b["source"] for a, b in zip(seen, seen[1:]))


@pytest.fixture
def client():
    from main import app

    return TestClient(app)


class TestApi:
    def test_today_uses_the_readers_date(self, client):
        response = client.get("/api/v1/subhashita/today", params={"date": "2026-10-17"})
        assert response.status_code == 200
        body = response.json()
        assert body["date"] == "2026-10-17"
        assert body["title"] == "Today's Subhashita"
        assert body["id"] == subhashita.for_day(date(2026, 10, 17))["id"]

    def test_run_of_days_for_the_widget(self, client):
        response = client.get("/api/v1/subhashita", params={"start": "2026-10-17", "days": 3})
        assert response.status_code == 200
        assert [item["date"] for item in response.json()["items"]] == [
            "2026-10-17", "2026-10-18", "2026-10-19",
        ]

    def test_run_is_capped(self, client):
        assert client.get("/api/v1/subhashita", params={"days": 32}).status_code == 422

    def test_a_signed_in_reader_gets_their_own_verse(self, client):
        from astrospace.api.subhashita_routes import reader_id
        from main import app

        app.dependency_overrides[reader_id] = lambda: "reader-1"
        try:
            body = client.get("/api/v1/subhashita/today", params={"date": "2026-10-17"}).json()
            items = client.get("/api/v1/subhashita", params={"start": "2026-10-17", "days": 2}).json()["items"]
        finally:
            app.dependency_overrides.pop(reader_id, None)
        assert body["id"] == subhashita.for_day(date(2026, 10, 17), "reader-1")["id"]
        assert items[0]["id"] == body["id"]

    def test_a_bad_token_still_gets_a_verse(self, client, monkeypatch):
        monkeypatch.setattr("astrospace.api.subhashita_routes.supabase_configured", lambda: True)
        response = client.get("/api/v1/subhashita/today", params={"date": "2026-10-17"},
                              headers={"Authorization": "Bearer not-a-token"})
        assert response.status_code == 200
        assert response.json()["id"] == subhashita.for_day(date(2026, 10, 17))["id"]

    def test_no_sign_in_needed(self, client):
        assert client.get("/api/v1/subhashita/today").status_code == 200

    def test_out_of_range_dates_are_400_not_500(self, client):
        # 9999-12-25 plus a run of days used to overflow (D16).
        assert client.get("/api/v1/subhashita", params={"start": "9999-12-25"}).status_code == 400
        assert client.get("/api/v1/subhashita/today", params={"date": "0001-01-01"}).status_code == 400


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    cm.upsert_push_token(session, ME, "fcm", "tok-me", timezone="Asia/Kolkata")
    cm.upsert_push_token(session, OTHER, "fcm", "tok-other", timezone="Europe/London")
    # The push starts off (see test_off_by_default_until_the_scholar_review);
    # these readers turned it on.
    cm.set_notification_preference(session, ME, CATEGORY, enabled=True)
    cm.set_notification_preference(session, OTHER, CATEGORY, enabled=True)
    yield session
    session.close()


EARLY = datetime(2026, 10, 17, 6, 0, tzinfo=IST)


class TestPush:
    def test_one_push_per_reader_at_ten_local(self, db):
        jobs = schedule_daily_subhashita(db, now=EARLY)
        by_user = {j.user_id: j for j in jobs}
        assert set(by_user) == {ME, OTHER}
        # 10:00 IST is 04:30 UTC; 10:00 BST is 09:00 UTC.
        assert by_user[ME].scheduled_for == datetime(2026, 10, 17, 4, 30)
        assert by_user[OTHER].scheduled_for == datetime(2026, 10, 17, 9, 0)
        # Each reader's push carries their own verse, the one the app shows them.
        verse = subhashita.for_day(date(2026, 10, 17), ME)
        assert by_user[ME].payload["subhashita_id"] == verse["id"]
        assert by_user[OTHER].payload["subhashita_id"] == subhashita.for_day(date(2026, 10, 17), OTHER)["id"]
        assert by_user[ME].title == "Today's Subhashita"
        assert by_user[ME].body == f"{verse['english']} ({verse['source']} {verse['ref']})"
        assert by_user[ME].deep_link == "/m/subhashita"
        assert by_user[ME].category == CATEGORY

    def test_rerun_is_idempotent(self, db):
        first = schedule_daily_subhashita(db, now=EARLY)
        second = schedule_daily_subhashita(db, now=EARLY)
        assert {j.id for j in first} == {j.id for j in second}
        assert db.query(NotificationJob).count() == 2

    def test_readers_own_time_and_switch_are_respected(self, db):
        cm.set_notification_preference(db, ME, CATEGORY, preferred_time=time(8, 15))
        cm.set_notification_preference(db, OTHER, CATEGORY, enabled=False)
        jobs = schedule_daily_subhashita(db, now=EARLY)
        assert [(j.user_id, j.scheduled_for) for j in jobs] == [(ME, datetime(2026, 10, 17, 2, 45))]

    def test_nothing_is_queued_once_the_afternoon_has_passed(self, db):
        late = datetime(2026, 10, 17, 15, 0, tzinfo=IST)
        jobs = schedule_daily_subhashita(db, now=late)
        # India's day is over for the verse; London is still at 10:30 in the morning.
        assert [j.user_id for j in jobs] == [OTHER]

    def test_nobody_is_sent_one_without_turning_it_on(self, db):
        db.query(cm.NotificationPreference).delete()
        db.commit()
        assert schedule_daily_subhashita(db, now=EARLY) == []

    def test_off_by_default_until_the_scholar_review(self):
        # docs/subhashita_corpus.md "Before launch": flip this once it is done.
        assert cm.DEFAULT_NOTIFICATION_PREFS[CATEGORY]["enabled"] is False
