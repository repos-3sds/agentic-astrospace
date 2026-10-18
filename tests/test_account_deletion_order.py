"""Account deletion order and erasure (production audit 2026-10-15, P1
"Account deletion").

The Supabase auth user used to be deleted before the database commit, so a
failed commit left a person unable to sign in with all their data still
stored. Now the data is committed first, the auth user is deleted with one
retry, and the request audit log loses the person's email.
"""
import pytest
import requests
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from astrospace.admin import audit_middleware
from astrospace.admin.audit_middleware import pseudonymous_actor_id
from astrospace.api import me_routes
from astrospace.api.auth import AuthUser, current_user
from astrospace.db import crud, get_db
from astrospace.db.database import Base
from astrospace.db.models import Kundli, UserProfile
from main import app

USER = "delete-me"


@pytest.fixture()
def env(monkeypatch):
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
        db.add(UserProfile(user_id=USER, display_name="Delete Me"))
        db.commit()
        crud.create_kundli(db, {
            "user_id": USER, "name": "Mine", "relation": "self",
            "birth_year": 1991, "birth_month": 8, "birth_day": 14,
            "birth_hour": 6, "birth_minute": 12,
            "birth_city": "Vijayawada", "birth_nation": "IN",
        })

    monkeypatch.setenv("SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role")
    patches = []

    class FakeAdmin:
        def patch(self, table, *, params, payload):
            patches.append((table, params, payload))
            return []

    monkeypatch.setattr(me_routes, "get_admin_client", lambda: FakeAdmin())

    class NoAudit:  # SUPABASE_URL is set above; keep the audit write offline
        def insert(self, *args, **kwargs):
            return []

    monkeypatch.setattr(audit_middleware, "get_admin_client", lambda: NoAudit())
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[current_user] = lambda: AuthUser(
        id=USER, email="delete@example.com", role="authenticated", auth_enabled=True,
    )
    try:
        yield TestClient(app), factory, patches
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(current_user, None)


def _delete(client):
    return client.request("DELETE", "/api/v1/me", json={"confirmation": "DELETE"})


class _Response:
    def __init__(self, status_code):
        self.status_code = status_code


def test_db_is_committed_before_the_auth_user_is_deleted(env, monkeypatch):
    client, factory, patches = env
    seen = []

    def fake_delete(url, headers, timeout):
        # Read through a separate session: only committed data is visible.
        with factory() as db:
            seen.append(db.query(Kundli).filter(Kundli.user_id == USER).count())
        return _Response(204)

    monkeypatch.setattr(me_routes.requests, "delete", fake_delete)
    response = _delete(client)
    assert response.status_code == 200
    assert seen == [0]


def test_auth_deletion_is_retried_once(env, monkeypatch):
    client, _factory, _patches = env
    attempts = []

    def flaky(url, headers, timeout):
        attempts.append(url)
        if len(attempts) == 1:
            raise requests.ConnectionError("reset by peer")
        return _Response(200)

    monkeypatch.setattr(me_routes.requests, "delete", flaky)
    assert _delete(client).status_code == 200
    assert len(attempts) == 2


def test_auth_failure_keeps_the_data_deleted_and_is_retryable(env, monkeypatch):
    client, factory, _patches = env
    attempts = []

    def down(url, headers, timeout):
        attempts.append(url)
        return _Response(500)

    monkeypatch.setattr(me_routes.requests, "delete", down)
    response = _delete(client)
    assert response.status_code == 502
    assert "500" not in response.json()["detail"]
    assert len(attempts) == me_routes.AUTH_DELETE_ATTEMPTS
    with factory() as db:
        assert db.get(UserProfile, USER) is None
        assert db.query(Kundli).filter(Kundli.user_id == USER).count() == 0

    # Calling again finishes the job; an already-removed auth user is a 404.
    monkeypatch.setattr(me_routes.requests, "delete", lambda url, headers, timeout: _Response(404))
    assert _delete(client).status_code == 200


def test_request_audit_rows_are_pseudonymised(env, monkeypatch):
    client, _factory, patches = env
    monkeypatch.setattr(me_routes.requests, "delete", lambda url, headers, timeout: _Response(204))
    assert _delete(client).status_code == 200
    assert patches == [(
        "app_request_audit_log",
        {"actor_id": f"eq.{USER}"},
        {"actor_email": None, "actor_id": pseudonymous_actor_id(USER)},
    )]


def test_audit_erasure_failure_does_not_block_deletion(env, monkeypatch):
    client, factory, _patches = env

    class BrokenAdmin:
        def patch(self, *args, **kwargs):
            raise RuntimeError("audit store down")

    monkeypatch.setattr(me_routes, "get_admin_client", lambda: BrokenAdmin())
    monkeypatch.setattr(me_routes.requests, "delete", lambda url, headers, timeout: _Response(204))
    assert _delete(client).status_code == 200
    with factory() as db:
        assert db.get(UserProfile, USER) is None


def test_store_customer_is_deleted_when_revenuecat_is_set_up(env, monkeypatch):
    client, _factory, _patches = env
    monkeypatch.setenv("REVENUECAT_SECRET_API_KEY", "sk_test")
    calls = []

    def fake_delete(url, headers, timeout):
        calls.append(url)
        return _Response(200)

    monkeypatch.setattr(me_routes.requests, "delete", fake_delete)
    assert _delete(client).status_code == 200
    assert f"https://api.revenuecat.com/v1/subscribers/{USER}" in calls


def test_store_outage_does_not_block_deletion(env, monkeypatch):
    client, factory, _patches = env
    monkeypatch.setenv("REVENUECAT_SECRET_API_KEY", "sk_test")

    def fake_delete(url, headers, timeout):
        if "revenuecat" in url:
            raise requests.ConnectionError("store down")
        return _Response(204)

    monkeypatch.setattr(me_routes.requests, "delete", fake_delete)
    assert _delete(client).status_code == 200
    with factory() as db:
        assert db.get(UserProfile, USER) is None
