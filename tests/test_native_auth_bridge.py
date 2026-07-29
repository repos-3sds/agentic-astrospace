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
        "app.astrospace.mobile://auth/callback?code=abc123&state=provider-state"
    )
