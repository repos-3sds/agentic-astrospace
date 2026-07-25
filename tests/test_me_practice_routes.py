"""API tests for the /me and /practice surfaces.

The interesting assertions are the negative ones. Several CRUD helpers
underneath take a bare row id with no ownership filter, because the delivery
worker calls them too — so every one of those is exercised here with a second
user's row to prove the route layer refuses it. A green test on the happy path
would not catch that.
"""
from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from astrospace.api.auth import AuthUser, current_user
from astrospace.db import crud, crud_mobile as cm, get_db
from astrospace.db.database import Base

ME = "test-user-me"
OTHER = "test-user-other"


@pytest.fixture(scope="module")
def env():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
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

    def kundli_for(user_id, name):
        return crud.create_kundli(db, {
            "user_id": user_id, "name": name, "relation": "self",
            "birth_year": 1991, "birth_month": 8, "birth_day": 14,
            "birth_hour": 6, "birth_minute": 12,
            "birth_city": "Vijayawada", "birth_nation": "IN",
        }).id

    db = Session()
    mine = kundli_for(ME, "Mine")
    partner = kundli_for(ME, "Partner")
    theirs = kundli_for(OTHER, "Theirs")

    # A remedy and a live activity belonging to the *other* user, so the
    # ownership checks have something real to refuse.
    foreign_remedy = cm.start_user_remedy(db, OTHER, theirs, "remedy-x").id
    foreign_activity = cm.start_live_activity(
        db, OTHER, "window", datetime.utcnow(),
        datetime.utcnow() + timedelta(hours=1),
    ).id
    foreign_token = cm.upsert_push_token(db, OTHER, "apns", "foreign-token").token
    db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[current_user] = override_current_user
    try:
        yield {
            "client": TestClient(app),
            "kundli": mine,
            "partner": partner,
            "foreign_kundli": theirs,
            "foreign_remedy": foreign_remedy,
            "foreign_activity": foreign_activity,
            "foreign_token": foreign_token,
        }
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(current_user, None)


@pytest.fixture(scope="module")
def client(env):
    return env["client"]


# ── Profile & devices ────────────────────────────────────────────────────────

class TestProfile:
    def test_profile_is_created_on_first_read(self, client):
        body = client.get("/api/v1/me").json()
        assert body["user_id"] == ME

    def test_patch_updates_fields(self, client):
        body = client.patch("/api/v1/me", json={
            "display_name": "Vikram", "timezone": "Asia/Kolkata",
        }).json()
        assert body["display_name"] == "Vikram"
        assert body["timezone"] == "Asia/Kolkata"
        # persisted, not just echoed
        assert client.get("/api/v1/me").json()["display_name"] == "Vikram"

    def test_empty_patch_400(self, client):
        assert client.patch("/api/v1/me", json={}).status_code == 400

    def test_device_registration_is_idempotent(self, client):
        payload = {"device_id": "device-1", "platform": "ios", "model": "iPhone15,2"}
        first = client.put("/api/v1/me/devices", json=payload).json()
        second = client.put("/api/v1/me/devices", json=payload).json()
        assert first["id"] == second["id"]

    def test_bad_platform_422(self, client):
        r = client.put("/api/v1/me/devices",
                       json={"device_id": "d2", "platform": "blackberry"})
        assert r.status_code == 422


# ── Push tokens ──────────────────────────────────────────────────────────────

class TestPushTokens:
    def test_register_and_revoke(self, client):
        r = client.put("/api/v1/me/push-tokens",
                       json={"provider": "apns", "token": "tok-mine"})
        assert r.status_code == 200
        assert client.post("/api/v1/me/push-tokens/revoke",
                           json={"provider": "apns", "token": "tok-mine"}
                           ).json() == {"revoked": True}

    def test_cannot_revoke_another_users_token(self, client, env):
        """revoke_push_token() filters on (provider, token) only — the route
        must not let a caller silence someone else's device."""
        r = client.post("/api/v1/me/push-tokens/revoke",
                        json={"provider": "apns", "token": env["foreign_token"]})
        assert r.status_code == 404

    def test_unknown_token_404(self, client):
        r = client.post("/api/v1/me/push-tokens/revoke",
                        json={"provider": "apns", "token": "never-seen"})
        assert r.status_code == 404


# ── Notification preferences ─────────────────────────────────────────────────

class TestNotificationPreferences:
    def test_defaults_always_resolve(self, client):
        prefs = client.get("/api/v1/me/notification-preferences").json()["preferences"]
        assert set(prefs) == set(cm.DEFAULT_NOTIFICATION_PREFS)
        assert prefs["remedy_reminder"]["enabled"] is False

    def test_set_and_read_back(self, client):
        body = client.put("/api/v1/me/notification-preferences/remedy_reminder",
                          json={"enabled": True, "preferred_time": "07:30"}).json()
        assert body["preferences"]["remedy_reminder"]["enabled"] is True
        again = client.get("/api/v1/me/notification-preferences").json()
        assert again["preferences"]["remedy_reminder"]["preferred_time"] == "07:30"

    def test_unknown_category_404(self, client):
        r = client.put("/api/v1/me/notification-preferences/nope",
                       json={"enabled": True})
        assert r.status_code == 404

    def test_malformed_time_422(self, client):
        r = client.put("/api/v1/me/notification-preferences/morning_brief",
                       json={"preferred_time": "7am"})
        assert r.status_code == 422


# ── Alerts ───────────────────────────────────────────────────────────────────

class TestAlerts:
    @pytest.fixture(scope="class")
    def alert_id(self, env):
        # Alerts are created by the backend, not by clients, so seed directly.
        from astrospace.db.database import Base  # noqa: F401
        db = next(app.dependency_overrides[get_db]())
        alert = cm.create_alert(db, ME, "window_alert", "Amrit Kalam soon")
        foreign = cm.create_alert(db, OTHER, "system", "Not yours")
        return alert.id, foreign.id

    def test_list_and_unread_count(self, client, alert_id):
        body = client.get("/api/v1/me/alerts").json()
        assert body["unread_count"] >= 1
        assert all(a["severity"] in {"info", "attention"} for a in body["alerts"])

    def test_only_my_alerts_are_listed(self, client, alert_id):
        _, foreign = alert_id
        ids = {a["id"] for a in client.get("/api/v1/me/alerts").json()["alerts"]}
        assert foreign not in ids

    def test_mark_read_drops_unread_count(self, client, alert_id):
        mine, _ = alert_id
        before = client.get("/api/v1/me/alerts").json()["unread_count"]
        body = client.post(f"/api/v1/me/alerts/{mine}/read").json()
        assert body["unread_count"] == before - 1

    def test_dismiss_removes_from_list(self, client, alert_id):
        mine, _ = alert_id
        client.post(f"/api/v1/me/alerts/{mine}/dismiss")
        ids = {a["id"] for a in client.get("/api/v1/me/alerts").json()["alerts"]}
        assert mine not in ids

    def test_cannot_touch_another_users_alert(self, client, alert_id):
        _, foreign = alert_id
        assert client.post(f"/api/v1/me/alerts/{foreign}/read").status_code == 404
        assert client.post(f"/api/v1/me/alerts/{foreign}/dismiss").status_code == 404


# ── Live activities & widgets ────────────────────────────────────────────────

class TestNativeSurfaces:
    def test_start_list_and_end(self, client):
        now = datetime.utcnow()
        created = client.post("/api/v1/me/live-activities", json={
            "kind": "window",
            "starts_at": now.isoformat(),
            "ends_at": (now + timedelta(hours=2)).isoformat(),
        }).json()
        listed = client.get("/api/v1/me/live-activities").json()
        assert created["id"] in {a["id"] for a in listed["activities"]}
        assert client.post(
            f"/api/v1/me/live-activities/{created['id']}/end"
        ).json()["ended"] is True

    def test_inverted_window_400(self, client):
        now = datetime.utcnow()
        r = client.post("/api/v1/me/live-activities", json={
            "kind": "window",
            "starts_at": now.isoformat(),
            "ends_at": (now - timedelta(hours=1)).isoformat(),
        })
        assert r.status_code == 400

    def test_cannot_end_another_users_activity(self, client, env):
        """end_live_activity() looks up by id alone — the route guards it."""
        r = client.post(f"/api/v1/me/live-activities/{env['foreign_activity']}/end")
        assert r.status_code == 404

    def test_widget_install(self, client, env):
        body = client.post("/api/v1/me/widgets", json={
            "kind": "today", "family": "systemSmall", "kundli_id": env["kundli"],
        }).json()
        assert body["kind"] == "today"


# ── Practice: remedies ───────────────────────────────────────────────────────

class TestPracticeRemedies:
    @pytest.fixture(scope="class")
    def started(self, client, env):
        return client.post("/api/v1/practice/remedies", json={
            "kundli_id": env["kundli"], "remedy_id": "sun-mantra",
            "cadence": "daily", "target_count": 108,
        }).json()

    def test_start_returns_a_zero_streak(self, started):
        assert started["status"] == "active"
        assert started["streak"] == 0

    def test_start_requires_an_owned_kundli(self, client, env):
        r = client.post("/api/v1/practice/remedies", json={
            "kundli_id": env["foreign_kundli"], "remedy_id": "sun-mantra",
        })
        assert r.status_code == 404

    def test_list_includes_streaks(self, client, started):
        body = client.get("/api/v1/practice/remedies").json()
        row = next(r for r in body["remedies"] if r["id"] == started["id"])
        assert "streak" in row

    def test_bad_status_filter_400(self, client):
        r = client.get("/api/v1/practice/remedies", params={"status": "nonsense"})
        assert r.status_code == 400

    def test_logging_two_days_gives_a_streak_of_two(self, client, started):
        today = date.today()
        for day in (today - timedelta(days=1), today):
            body = client.post(
                f"/api/v1/practice/remedies/{started['id']}/completions",
                json={"occurred_on": day.isoformat()},
            ).json()
        assert body["streak"] == 2

    def test_logging_twice_in_a_day_increments_the_count(self, client, started):
        first = client.post(
            f"/api/v1/practice/remedies/{started['id']}/completions", json={},
        ).json()
        second = client.post(
            f"/api/v1/practice/remedies/{started['id']}/completions", json={},
        ).json()
        assert second["count"] == first["count"] + 1
        assert second["occurred_on"] == date.today().isoformat()

    def test_future_completion_400(self, client, started):
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        r = client.post(f"/api/v1/practice/remedies/{started['id']}/completions",
                        json={"occurred_on": tomorrow})
        assert r.status_code == 400

    def test_pause_then_read_back(self, client, started):
        body = client.patch(f"/api/v1/practice/remedies/{started['id']}",
                            json={"status": "paused"}).json()
        assert body["status"] == "paused"
        client.patch(f"/api/v1/practice/remedies/{started['id']}",
                     json={"status": "active"})

    def test_bad_status_patch_400(self, client, started):
        r = client.patch(f"/api/v1/practice/remedies/{started['id']}",
                         json={"status": "exploded"})
        assert r.status_code == 400

    @pytest.mark.parametrize("method,suffix,body", [
        ("patch", "", {"status": "paused"}),
        ("post", "/completions", {}),
        ("get", "/streak", None),
    ])
    def test_another_users_remedy_is_never_reachable(
        self, client, env, method, suffix, body
    ):
        """log_remedy_completion/get_remedy_streak take a bare id."""
        url = f"/api/v1/practice/remedies/{env['foreign_remedy']}{suffix}"
        call = getattr(client, method)
        r = call(url) if body is None else call(url, json=body)
        assert r.status_code == 404


# ── Practice: observances, muhurtas, compatibility ───────────────────────────

class TestPracticeSaved:
    def test_observance_upserts_per_date(self, client, env):
        payload = {"festival_id": "fest-diwali", "occurs_on": "2026-11-08",
                   "status": "planned", "kundli_id": env["kundli"]}
        first = client.put("/api/v1/practice/observances", json=payload).json()
        payload["status"] = "observed"
        second = client.put("/api/v1/practice/observances", json=payload).json()
        assert first["id"] == second["id"]
        assert second["status"] == "observed"

    def test_bad_observance_status_400(self, client):
        r = client.put("/api/v1/practice/observances", json={
            "festival_id": "f", "occurs_on": "2026-11-08", "status": "maybe",
        })
        assert r.status_code == 400

    def test_save_and_list_muhurtas(self, client, env):
        start = datetime.utcnow() + timedelta(days=1)
        created = client.post("/api/v1/practice/saved-muhurtas", json={
            "kundli_id": env["kundli"], "goal_slug": "sign_contract",
            "starts_at": start.isoformat(),
            "ends_at": (start + timedelta(minutes=48)).isoformat(),
            "quality": "best",
        }).json()
        listed = client.get("/api/v1/practice/saved-muhurtas").json()
        assert created["id"] in {m["id"] for m in listed["muhurtas"]}

    def test_inverted_muhurta_400(self, client, env):
        start = datetime.utcnow()
        r = client.post("/api/v1/practice/saved-muhurtas", json={
            "kundli_id": env["kundli"],
            "starts_at": start.isoformat(),
            "ends_at": (start - timedelta(minutes=1)).isoformat(),
        })
        assert r.status_code == 400

    def test_compatibility_check_keeps_dosha_flags(self, client, env):
        """Doshas are surfaced as flags, never quietly dropped."""
        client.post("/api/v1/practice/compatibility-checks", json={
            "kundli_id": env["kundli"], "partner_kundli_id": env["partner"],
            "total_score": 27.5, "verdict": "workable",
            "dosha_flags": {"manglik": {"active": True, "cancelled": False}},
        })
        rows = client.get("/api/v1/practice/compatibility-checks").json()["checks"]
        assert rows[0]["dosha_flags"]["manglik"]["active"] is True

    def test_compatibility_requires_both_kundlis_owned(self, client, env):
        r = client.post("/api/v1/practice/compatibility-checks", json={
            "kundli_id": env["kundli"],
            "partner_kundli_id": env["foreign_kundli"],
        })
        assert r.status_code == 404
