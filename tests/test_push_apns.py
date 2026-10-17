"""APNs direct transport (iOS push): payload, auth headers, sandbox fallback."""
from __future__ import annotations

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from astrospace.notifications.push import (
    ApnsTransport,
    NotConfiguredTransport,
    PushMessage,
    transports_from_env,
)


class FakeResponse:
    def __init__(self, status_code=200, body=None, headers=None):
        self.status_code = status_code
        self._body = body
        self.headers = headers or {}

    def json(self):
        if self._body is None:
            raise ValueError("no body")
        return self._body


class FakeHttp:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, json=None, headers=None):
        self.calls.append({"url": url, "json": json, "headers": headers})
        return self.responses.pop(0)


@pytest.fixture
def key(tmp_path):
    private = ec.generate_private_key(ec.SECP256R1())
    path = tmp_path / "AuthKey_ABC123DEFG.p8"
    path.write_bytes(private.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ))
    return path, private.public_key()


def transport(key, http, clock=lambda: 1_000_000.0):
    return ApnsTransport(str(key[0]), "ABC123DEFG", "TEAM123456", http=http, clock=clock)


def test_send_posts_alert_with_signed_provider_token(key):
    http = FakeHttp(FakeResponse(200, headers={"apns-id": "id-1"}))
    result = transport(key, http).send(
        "a" * 64, PushMessage("Your day", "Steady morning", deep_link="/m/today", category="morning_brief"),
    )
    assert result.ok and result.provider_message_id == "id-1"
    call = http.calls[0]
    assert call["url"] == "https://api.push.apple.com/3/device/" + "a" * 64
    assert call["headers"]["apns-topic"] == "app.asksiddha.mobile"
    assert call["headers"]["apns-push-type"] == "alert"
    assert call["json"]["aps"]["alert"] == {"title": "Your day", "body": "Steady morning"}
    assert call["json"]["deep_link"] == "/m/today"
    assert call["json"]["category"] == "morning_brief"
    token = call["headers"]["authorization"].removeprefix("bearer ")
    assert jwt.get_unverified_header(token)["kid"] == "ABC123DEFG"
    claims = jwt.decode(token, key[1], algorithms=["ES256"], options={"verify_iat": False})
    assert claims == {"iss": "TEAM123456", "iat": 1_000_000}


def test_data_cannot_overwrite_aps(key):
    http = FakeHttp(FakeResponse(200))
    transport(key, http).send("t", PushMessage("Hi", data={"aps": "x", "kind": "brief"}))
    assert isinstance(http.calls[0]["json"]["aps"], dict)
    assert http.calls[0]["json"]["kind"] == "brief"


def test_provider_token_is_reused_then_refreshed(key):
    now = [1_000_000.0]
    http = FakeHttp(*[FakeResponse(200) for _ in range(3)])
    t = transport(key, http, clock=lambda: now[0])
    t.send("t", PushMessage("1"))
    now[0] += 60
    t.send("t", PushMessage("2"))
    now[0] += 3600
    t.send("t", PushMessage("3"))
    auth = [c["headers"]["authorization"] for c in http.calls]
    assert auth[0] == auth[1] != auth[2]


def test_xcode_build_token_falls_back_to_sandbox(key):
    http = FakeHttp(FakeResponse(400, {"reason": "BadDeviceToken"}), FakeResponse(200))
    result = transport(key, http).send("t", PushMessage("Hi"))
    assert result.ok
    assert http.calls[1]["url"].startswith("https://api.sandbox.push.apple.com/")


def test_token_rejected_by_both_hosts_is_dead(key):
    http = FakeHttp(FakeResponse(400, {"reason": "BadDeviceToken"}),
                    FakeResponse(400, {"reason": "BadDeviceToken"}))
    result = transport(key, http).send("t", PushMessage("Hi"))
    assert not result.ok and result.token_dead
    assert "BadDeviceToken" in result.error


def test_unregistered_is_dead_without_sandbox_retry(key):
    http = FakeHttp(FakeResponse(410, {"reason": "Unregistered"}))
    result = transport(key, http).send("t", PushMessage("Hi"))
    assert result.token_dead and len(http.calls) == 1


def test_auth_error_is_retryable_not_dead(key):
    http = FakeHttp(FakeResponse(403, {"reason": "InvalidProviderToken"}))
    result = transport(key, http).send("t", PushMessage("Hi"))
    assert not result.ok and not result.token_dead and len(http.calls) == 1


def test_network_error_is_reported(key):
    class Boom:
        def post(self, *a, **k):
            raise OSError("connection reset")
    result = transport(key, Boom()).send("t", PushMessage("Hi"))
    assert not result.ok and "connection reset" in result.error


def test_transports_from_env_builds_apns_when_configured(key):
    env = {"APNS_KEY_FILE": str(key[0]), "APNS_KEY_ID": "ABC123DEFG", "APNS_TEAM_ID": "TEAM123456"}
    apns = transports_from_env(env)["apns"]
    assert isinstance(apns, ApnsTransport) and apns.topic == "app.asksiddha.mobile"


def test_transports_from_env_needs_every_apns_setting(key):
    env = {"APNS_KEY_FILE": str(key[0]), "APNS_KEY_ID": "ABC123DEFG"}
    apns = transports_from_env(env)["apns"]
    assert isinstance(apns, NotConfiguredTransport)
    assert "APNS_TEAM_ID" in apns.reason
