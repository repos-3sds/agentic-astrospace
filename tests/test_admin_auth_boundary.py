"""The fail-open chain from disabled app auth into full admin.

`current_user` returning a fixed dev identity when Supabase isn't configured
is intentional and load-bearing: the local debug server runs with no
Supabase keys at all, and the browser verification loop for every mobile
screen depends on unauthenticated requests still being served. That part
must never change.

What must not follow from it is `current_admin` treating "auth is off"
as "grant admin" unconditionally — because auth ends up off in production
either by an explicit (and documented) dev-only flag, or by nothing more
than a missing SUPABASE_ANON_KEY while SUPABASE_URL and the service-role key
are both present, which is exactly what the "required configuration" section
of docs/admin_console.md used to describe. Either way, an unauthenticated
request became a full admin session with no token.

The fix keys the refusal off Cloud Run's own K_SERVICE marker rather than a
manually-set flag, so it can't be forgotten in a deploy — see
`running_on_cloud_run` in astrospace/api/auth.py.
"""
import types

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from astrospace.admin.security import current_admin
from astrospace.api.auth import AuthUser, current_user, supabase_configured
from astrospace.db import crud
from astrospace.db.database import Base

DEV_USER_ID = "local-dev-user"


def _fake_request():
    request = types.SimpleNamespace()
    request.state = types.SimpleNamespace()
    return request


def _clear_supabase_env(monkeypatch):
    for var in ("SUPABASE_URL", "SUPABASE_ANON_KEY", "ASTROSPACE_DEV_AUTH_BYPASS", "K_SERVICE"):
        monkeypatch.delenv(var, raising=False)


class TestDevAuthStaysOpenLocally:
    """Proof (a): no Supabase keys, no K_SERVICE — the dev loop is intact."""

    def test_unauthenticated_request_is_served_as_dev_user(self, monkeypatch):
        _clear_supabase_env(monkeypatch)
        assert supabase_configured() is False

        user = current_user(_fake_request(), authorization=None)

        assert user.id == DEV_USER_ID
        assert user.auth_enabled is False

    def test_admin_console_still_works_for_local_dev(self, monkeypatch):
        """Unchanged from before the fix: no K_SERVICE means this is someone's
        machine, and the console needs to be reachable there to develop it."""
        _clear_supabase_env(monkeypatch)
        dev_user = AuthUser(id=DEV_USER_ID, email="local@astrospace.dev",
                            role="dev", auth_enabled=False)

        admin = current_admin(dev_user)

        assert admin.role == "admin"


class TestAdminRefusesToFailOpenOnCloudRun:
    """Proof (b): same "no keys" config, but with K_SERVICE set — admin is refused."""

    def test_missing_anon_key_on_cloud_run_refuses_admin(self, monkeypatch):
        """The scenario the vulnerable doc invited: SUPABASE_URL and the
        service-role key are set (an operator believes auth is configured),
        SUPABASE_ANON_KEY is not, and K_SERVICE marks this as Cloud Run."""
        _clear_supabase_env(monkeypatch)
        monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-value")
        monkeypatch.setenv("K_SERVICE", "astrospace-prod")
        assert supabase_configured() is False  # anon key still missing

        dev_user = current_user(_fake_request(), authorization=None)
        assert dev_user.auth_enabled is False  # unauthenticated request still resolves...

        with pytest.raises(HTTPException) as exc:
            current_admin(dev_user)  # ...but no longer reaches admin.

        assert exc.value.status_code == 503

    def test_dev_bypass_flag_has_no_effect_on_cloud_run(self, monkeypatch):
        """The documented dev-only flag, set on a fully-configured deploy."""
        _clear_supabase_env(monkeypatch)
        monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
        monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key-value")
        monkeypatch.setenv("ASTROSPACE_DEV_AUTH_BYPASS", "true")
        monkeypatch.setenv("K_SERVICE", "astrospace-prod")

        assert supabase_configured() is True  # bypass flag is ignored here

        with pytest.raises(HTTPException) as exc:
            current_user(_fake_request(), authorization=None)  # a token is now required
        assert exc.value.status_code == 401

    def test_dev_bypass_flag_still_works_off_cloud_run(self, monkeypatch):
        """Unchanged: the documented local-only QA shortcut keeps working when
        K_SERVICE isn't set, which is the debug-server-on-8010 workflow."""
        _clear_supabase_env(monkeypatch)
        monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
        monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key-value")
        monkeypatch.setenv("ASTROSPACE_DEV_AUTH_BYPASS", "true")

        assert supabase_configured() is False

        user = current_user(_fake_request(), authorization=None)
        assert user.id == DEV_USER_ID


class TestEndToEndOverHttp:
    """Same two scenarios, through the real request path rather than calling
    the dependency functions directly."""

    @pytest.fixture
    def client(self):
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        from main import app
        from astrospace.db import get_db

        def override_get_db():
            db = session_factory()
            try:
                yield db
            finally:
                db.close()

        db = session_factory()
        crud.create_kundli(db, {
            "user_id": DEV_USER_ID,
            "name": "Auth Boundary Test",
            "relation": "self",
            "birth_year": 1990, "birth_month": 5, "birth_day": 17,
            "birth_hour": 14, "birth_minute": 30,
            "birth_city": "Chennai", "birth_nation": "IN",
        })
        db.close()

        app.dependency_overrides[get_db] = override_get_db
        try:
            # Not `with TestClient(app) as client:` — that fires the real
            # startup event (init_db() against the live DATABASE_URL from
            # .env), same as every other test file in this suite avoids.
            yield TestClient(app)
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_kundlis_and_daily_guidance_serve_unauthenticated_with_no_keys(
        self, client, monkeypatch,
    ):
        """Proof (a) end to end: :8010 with no Supabase keys still serves
        /api/v1/kundlis and /context/{id}/daily with no Authorization header."""
        _clear_supabase_env(monkeypatch)

        kundlis = client.get("/api/v1/kundlis")
        assert kundlis.status_code == 200
        kundli_id = kundlis.json()[0]["id"]

        daily = client.get(f"/api/v1/context/{kundli_id}/daily")
        assert daily.status_code == 200

    def test_admin_route_refuses_when_cloud_run_and_anon_key_missing(
        self, client, monkeypatch,
    ):
        """Proof (b) end to end: the exact request that used to return every
        user's data with no token now gets a 503, not a 200."""
        _clear_supabase_env(monkeypatch)
        monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-value")
        monkeypatch.setenv("K_SERVICE", "astrospace-prod")

        response = client.get("/api/v1/admin/users")

        assert response.status_code == 503
