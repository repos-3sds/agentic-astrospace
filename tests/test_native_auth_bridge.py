from fastapi.testclient import TestClient

from main import app


def test_native_auth_bridge_preserves_pkce_code():
    client = TestClient(app)

    response = client.get(
        "/api/v1/auth/native-callback",
        params={"code": "abc123", "state": "provider-state"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["location"] == (
        "app.asksiddha.mobile://auth/callback?code=abc123&state=provider-state"
    )


def _config(monkeypatch, **env):
    from astrospace.api.auth import auth_config

    for key in ("GOOGLE_OAUTH_WEB_CLIENT_ID", "GOOGLE_OAUTH_IOS_CLIENT_ID"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    auth_config.cache_clear()
    try:
        return TestClient(app).get("/api/v1/auth/config").json()
    finally:
        auth_config.cache_clear()


def test_auth_config_sends_google_client_ids_for_native_sign_in(monkeypatch):
    body = _config(
        monkeypatch,
        GOOGLE_OAUTH_WEB_CLIENT_ID="123-web.apps.googleusercontent.com",
        GOOGLE_OAUTH_IOS_CLIENT_ID="123-ios.apps.googleusercontent.com",
    )
    assert body["google_web_client_id"] == "123-web.apps.googleusercontent.com"
    assert body["google_ios_client_id"] == "123-ios.apps.googleusercontent.com"


def test_auth_config_without_google_ids_keeps_the_browser_flow(monkeypatch):
    body = _config(monkeypatch)
    assert body["google_web_client_id"] is None
    assert body["google_ios_client_id"] is None
