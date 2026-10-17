"""Transports that hand one notification to one device token.

Two providers are implemented:

- FCM (Firebase Cloud Messaging, HTTP v1) for Android, whose tokens are FCM
  tokens.
- APNs direct for iOS. @capacitor/push-notifications hands iOS a raw APNs
  device token, so the worker talks to Apple itself: HTTP/2 to
  api.push.apple.com, authenticated by an ES256 provider token signed with
  the team's .p8 key. No Firebase iOS SDK is linked into the app.

Configuration is environment-only, never read from the repo:

    FCM_SERVICE_ACCOUNT_FILE   path to a Firebase service-account JSON
    FCM_PROJECT_ID             optional; defaults to the file's project_id

    APNS_KEY_FILE              path to the AuthKey_XXXXXXXXXX.p8 from the
                               Apple Developer account (Keys > APNs)
    APNS_KEY_ID                the key's 10-character id
    APNS_TEAM_ID               the 10-character Apple team id
    APNS_TOPIC                 optional; the app's bundle id
                               (default app.asksiddha.mobile)
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Protocol

FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
FCM_ENDPOINT = "https://fcm.googleapis.com/v1/projects/{project}/messages:send"

# FCM error codes that mean the token will never work again. The worker
# revokes those rows so the next run does not keep paying for them.
# Android notification channel with the temple-bell sound, created by the app
# (ui/android/.../MainActivity.java). Unknown channel ids fall back to the
# app's default, so an older build still shows the push.
ANDROID_CHANNEL_ID = "siddha_bell"
FCM_DEAD_TOKEN_CODES = {"UNREGISTERED", "INVALID_ARGUMENT"}


@dataclass(frozen=True)
class PushMessage:
    title: str
    body: str | None = None
    deep_link: str | None = None
    data: dict | None = None
    category: str | None = None


@dataclass(frozen=True)
class PushResult:
    ok: bool
    provider_message_id: str | None = None
    error: str | None = None
    # True when the provider says the token is gone for good.
    token_dead: bool = False
    receipt: dict | None = None


class PushTransport(Protocol):
    provider: str

    def send(self, token: str, message: PushMessage) -> PushResult: ...


class NotConfiguredTransport:
    """Stands in for any provider with no credentials. Every send fails with
    a stable, greppable reason and the job stays retryable, so configuring
    the provider later drains the backlog without any code change."""

    def __init__(self, provider: str, reason: str | None = None):
        self.provider = provider
        self.reason = reason or f"{provider} transport not configured"

    def send(self, token: str, message: PushMessage) -> PushResult:
        return PushResult(ok=False, error=self.reason)


class FcmTransport:
    provider = "fcm"

    def __init__(self, service_account_file: str, project_id: str | None = None,
                 http=None):
        from google.oauth2 import service_account  # google-auth ships with google-genai

        self._credentials = service_account.Credentials.from_service_account_file(
            service_account_file, scopes=[FCM_SCOPE],
        )
        if not project_id:
            with open(service_account_file, encoding="utf-8") as fh:
                project_id = json.load(fh).get("project_id")
        if not project_id:
            raise ValueError("FCM_PROJECT_ID is unset and the service-account file has no project_id")
        self.project_id = project_id
        self._http = http

    def _access_token(self) -> str:
        from google.auth.transport.requests import Request

        if not self._credentials.valid:
            self._credentials.refresh(Request())
        return self._credentials.token

    def _client(self):
        if self._http is None:
            import httpx

            self._http = httpx.Client(timeout=10.0)
        return self._http

    def send(self, token: str, message: PushMessage) -> PushResult:
        data = {str(k): str(v) for k, v in (message.data or {}).items()}
        if message.deep_link:
            data["deep_link"] = message.deep_link
        if message.category:
            data["category"] = message.category
        payload = {
            "message": {
                "token": token,
                "notification": {"title": message.title, "body": message.body or ""},
                "data": data,
                "android": {
                    "priority": "normal",
                    "notification": {"channel_id": ANDROID_CHANNEL_ID},
                },
            }
        }
        try:
            response = self._client().post(
                FCM_ENDPOINT.format(project=self.project_id),
                json=payload,
                headers={"Authorization": f"Bearer {self._access_token()}"},
            )
        except Exception as exc:  # network, auth refresh
            return PushResult(ok=False, error=f"fcm: {exc}")

        try:
            body = response.json()
        except ValueError:
            body = {"raw": response.text[:500]}
        if response.status_code == 200:
            return PushResult(ok=True, provider_message_id=body.get("name"), receipt=body)
        error = body.get("error", {}) if isinstance(body, dict) else {}
        code = error.get("status") or str(response.status_code)
        details = error.get("details") or []
        fcm_code = next(
            (d.get("errorCode") for d in details if isinstance(d, dict) and d.get("errorCode")),
            None,
        )
        dead = (fcm_code in FCM_DEAD_TOKEN_CODES) or (response.status_code == 404)
        return PushResult(
            ok=False,
            error=f"fcm {code}: {error.get('message') or response.text[:200]}",
            token_dead=dead,
            receipt=body if isinstance(body, dict) else None,
        )


APNS_DEFAULT_TOPIC = "app.asksiddha.mobile"
APNS_HOSTS = {
    "production": "https://api.push.apple.com",
    "sandbox": "https://api.sandbox.push.apple.com",
}
# Apple rejects a provider token older than an hour and throttles one that is
# re-signed more often than every 20 minutes.
APNS_TOKEN_TTL_SECONDS = 50 * 60
# Reasons that mean the device token will never work again on that host.
APNS_DEAD_TOKEN_REASONS = {"BadDeviceToken", "Unregistered", "DeviceTokenNotForTopic"}


class ApnsTransport:
    """APNs over HTTP/2 with token (JWT) authentication.

    TestFlight and App Store builds get production tokens; a build run from
    Xcode gets sandbox tokens, and the app cannot tell which it is. A token
    is tried on production first and, on BadDeviceToken, on sandbox; it is
    only reported dead when both reject it.
    """

    provider = "apns"

    def __init__(self, key_file: str, key_id: str, team_id: str,
                 topic: str = APNS_DEFAULT_TOPIC, http=None, clock=None):
        with open(key_file, encoding="utf-8") as fh:
            self._key = fh.read()
        self.key_id = key_id
        self.team_id = team_id
        self.topic = topic
        self._http = http
        self._clock = clock
        self._jwt: str | None = None
        self._jwt_issued = 0.0

    def _now(self) -> float:
        if self._clock is not None:
            return self._clock()
        import time

        return time.time()

    def _provider_token(self) -> str:
        now = self._now()
        if self._jwt is None or now - self._jwt_issued > APNS_TOKEN_TTL_SECONDS:
            import jwt  # PyJWT[crypto]

            self._jwt = jwt.encode(
                {"iss": self.team_id, "iat": int(now)}, self._key,
                algorithm="ES256", headers={"kid": self.key_id},
            )
            self._jwt_issued = now
        return self._jwt

    def _client(self):
        if self._http is None:
            import httpx

            self._http = httpx.Client(http2=True, timeout=10.0)
        return self._http

    def payload(self, message: PushMessage) -> dict:
        body: dict = {
            "aps": {
                "alert": {"title": message.title, "body": message.body or ""},
                "sound": "default",
            },
        }
        for key, value in (message.data or {}).items():
            if str(key) != "aps":
                body[str(key)] = str(value)
        if message.deep_link:
            body["deep_link"] = message.deep_link
        if message.category:
            body["category"] = message.category
        return body

    def _post(self, host: str, token: str, body: dict):
        return self._client().post(
            f"{APNS_HOSTS[host]}/3/device/{token}",
            json=body,
            headers={
                "authorization": f"bearer {self._provider_token()}",
                "apns-topic": self.topic,
                "apns-push-type": "alert",
                # 5 = deliver when power allows; a morning brief is not urgent.
                "apns-priority": "5",
            },
        )

    def send(self, token: str, message: PushMessage) -> PushResult:
        body = self.payload(message)
        reason = None
        for host in ("production", "sandbox"):
            try:
                response = self._post(host, token, body)
            except Exception as exc:  # network, key parsing
                return PushResult(ok=False, error=f"apns: {exc}")
            if response.status_code == 200:
                apns_id = response.headers.get("apns-id")
                return PushResult(ok=True, provider_message_id=apns_id,
                                  receipt={"apns_id": apns_id, "host": host})
            try:
                reason = (response.json() or {}).get("reason")
            except ValueError:
                reason = None
            reason = reason or str(response.status_code)
            # Only a token from the other environment is worth a second try.
            if reason != "BadDeviceToken":
                break
        dead = reason in APNS_DEAD_TOKEN_REASONS or response.status_code == 410
        return PushResult(ok=False, error=f"apns {response.status_code}: {reason}",
                          token_dead=dead, receipt={"reason": reason})


def transports_from_env(environ: dict | None = None) -> dict[str, PushTransport]:
    """One transport per provider the API accepts (me_routes.PushTokenRegistration)."""
    env = os.environ if environ is None else environ
    transports: dict[str, PushTransport] = {}
    sa_file = env.get("FCM_SERVICE_ACCOUNT_FILE")
    if sa_file and os.path.exists(sa_file):
        transports["fcm"] = FcmTransport(sa_file, env.get("FCM_PROJECT_ID"))
    else:
        transports["fcm"] = NotConfiguredTransport(
            "fcm", "fcm transport not configured (set FCM_SERVICE_ACCOUNT_FILE)",
        )
    key_file = env.get("APNS_KEY_FILE")
    key_id, team_id = env.get("APNS_KEY_ID"), env.get("APNS_TEAM_ID")
    if key_file and os.path.exists(key_file) and key_id and team_id:
        transports["apns"] = ApnsTransport(
            key_file, key_id, team_id, env.get("APNS_TOPIC") or APNS_DEFAULT_TOPIC,
        )
    else:
        transports["apns"] = NotConfiguredTransport(
            "apns", "apns transport not configured (set APNS_KEY_FILE, APNS_KEY_ID and APNS_TEAM_ID)",
        )
    transports["web"] = NotConfiguredTransport("web")
    return transports
