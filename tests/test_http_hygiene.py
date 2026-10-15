"""HTTP hygiene (production audit 2026-10-15, section 3 P1/P2).

Unknown /api paths, public docs on Cloud Run, missing security headers,
dev CORS origins in production, the local-workspace claim in production,
raw exception text in responses, and unbounded free-text fields.
"""
import importlib

import pytest
import requests
from fastapi import FastAPI
from fastapi.testclient import TestClient

from astrospace.api import auth as auth_module
from astrospace.api.auth import AuthUser, current_user


@pytest.fixture()
def reload_main(monkeypatch):
    """Re-import main under the given environment; restore it afterwards so
    the rest of the suite finds the app it expects (see test_cors_origins)."""
    import main

    def _reload(cloud_run: bool, allowed_origins: str | None = None):
        if cloud_run:
            monkeypatch.setenv("K_SERVICE", "astrospace")
        else:
            monkeypatch.delenv("K_SERVICE", raising=False)
        if allowed_origins is None:
            monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
        else:
            monkeypatch.setenv("ALLOWED_ORIGINS", allowed_origins)
        return importlib.reload(main)

    yield _reload
    monkeypatch.delenv("K_SERVICE", raising=False)
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    importlib.reload(main)


def _cors_origins(app) -> list[str]:
    for middleware in app.user_middleware:
        if "CORS" in str(middleware):
            return list(middleware.kwargs.get("allow_origins") or [])
    pytest.fail("CORS middleware is not installed")


# ── Unknown /api paths ───────────────────────────────────────────────────────

def _spa_app(tmp_path):
    import main

    (tmp_path / "index.html").write_text("<!doctype html><app-root></app-root>")
    app = FastAPI()
    app.mount("/", main.SPAStaticFiles(directory=str(tmp_path), html=True), name="spa")
    return TestClient(app)


def test_unknown_api_path_is_a_json_404_not_the_spa(tmp_path):
    client = _spa_app(tmp_path)
    for method in ("get", "post"):
        response = getattr(client, method)("/api/v1/no-such-route")
        assert response.status_code == 404
        assert response.headers["content-type"].startswith("application/json")
        assert response.json() == {"detail": "Not Found"}
    assert client.get("/api").status_code == 404


def test_client_side_routes_still_fall_back_to_index(tmp_path):
    client = _spa_app(tmp_path)
    response = client.get("/kundli/123")
    assert response.status_code == 200
    assert "<app-root>" in response.text
    # A page route that merely starts with "api" is not an API path.
    assert client.get("/apiary").status_code == 200


def test_unknown_api_path_on_the_real_app_is_json():
    import main

    response = TestClient(main.app).get("/api/v1/definitely-not-a-route")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


# ── Docs, CORS and headers by environment ────────────────────────────────────

def test_docs_are_served_locally(reload_main):
    client = TestClient(reload_main(cloud_run=False).app)
    assert client.get("/openapi.json").status_code == 200
    assert client.get("/docs").status_code == 200


def test_docs_are_off_on_cloud_run(reload_main):
    client = TestClient(reload_main(cloud_run=True).app)
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404, path


def test_security_headers_locally_without_hsts(reload_main):
    response = TestClient(reload_main(cloud_run=False).app).get("/api/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "strict-transport-security" not in response.headers


def test_security_headers_on_cloud_run_include_hsts(reload_main):
    response = TestClient(reload_main(cloud_run=True).app).get("/api/health")
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["strict-transport-security"].startswith("max-age=")
    assert "preload" not in response.headers["strict-transport-security"]


def test_no_dev_origins_on_cloud_run_without_an_allowlist(reload_main):
    origins = _cors_origins(reload_main(cloud_run=True).app)
    assert "http://localhost:4200" not in origins
    assert "http://localhost:8000" not in origins
    # The native WebView origins are still always present.
    assert {"https://localhost", "capacitor://localhost"} <= set(origins)


def test_dev_origins_remain_locally(reload_main):
    assert "http://localhost:4200" in _cors_origins(reload_main(cloud_run=False).app)


# ── Local workspace claim ────────────────────────────────────────────────────

@pytest.fixture()
def signed_in():
    import main

    main.app.dependency_overrides[current_user] = lambda: AuthUser(
        id="real-user", email="r@example.com", role="authenticated", auth_enabled=True,
    )
    yield TestClient(main.app)
    main.app.dependency_overrides.pop(current_user, None)


def test_local_claim_is_404_on_cloud_run(signed_in, monkeypatch):
    monkeypatch.setenv("K_SERVICE", "astrospace")
    assert signed_in.post("/api/v1/auth/migration/local/claim").status_code == 404
    status = signed_in.get("/api/v1/auth/migration/local").json()
    assert status["available"] is False and status["local_kundlis"] == 0


# ── Raw exception text ───────────────────────────────────────────────────────

def test_supabase_outage_does_not_echo_exception_text(monkeypatch):
    import main

    monkeypatch.setenv("SUPABASE_URL", "https://secret-project.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon")
    monkeypatch.delenv("ASTROSPACE_DEV_AUTH_BYPASS", raising=False)

    def boom(*args, **kwargs):
        raise requests.ConnectionError("HTTPSConnectionPool(host='secret-project.supabase.co')")

    monkeypatch.setattr(auth_module.requests, "get", boom)
    response = TestClient(main.app).get(
        "/api/v1/kundlis", headers={"Authorization": "Bearer t"},
    )
    assert response.status_code == 503
    assert "secret-project" not in response.text


# ── Length limits ────────────────────────────────────────────────────────────

_KUNDLI = {
    "name": "Reader", "birth_year": 1991, "birth_month": 8, "birth_day": 14,
    "birth_hour": 6, "birth_minute": 12, "birth_city": "Vijayawada", "birth_nation": "IN",
}


@pytest.mark.parametrize("field,size", [("name", 101), ("birth_city", 121), ("notes", 2001)])
def test_kundli_free_text_is_bounded(field, size):
    from astrospace.api.kundli_routes import KundliCreate, KundliUpdate
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        KundliCreate(**{**_KUNDLI, field: "x" * size})
    with pytest.raises(ValidationError):
        KundliUpdate(**{field: "x" * size})
    KundliCreate(**{**_KUNDLI, field: "x" * (size - 1)})


def test_oversized_kundli_name_is_a_422_at_the_edge(signed_in):
    response = signed_in.post("/api/v1/kundlis", json={**_KUNDLI, "name": "x" * 5000})
    assert response.status_code == 422


def test_ask_history_is_trimmed_and_capped():
    from pydantic import ValidationError

    from astrospace.api.ask_routes import MAX_HISTORY, MAX_HISTORY_ACCEPTED, AskRequest

    turns = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"t{i}"}
             for i in range(40)]
    trimmed = AskRequest(question="q", history=turns).history
    assert len(trimmed) == MAX_HISTORY
    assert trimmed[-1].content == "t39"
    with pytest.raises(ValidationError):
        AskRequest(question="q", history=[{"role": "user", "content": "x"}]
                   * (MAX_HISTORY_ACCEPTED + 1))
