"""Transports that hand one notification to one device token.

Only FCM (Firebase Cloud Messaging, HTTP v1) is implemented. Android tokens
are FCM tokens. iOS tokens from @capacitor/push-notifications are raw APNs
tokens; APNs direct needs HTTP/2 plus an ES256 provider token, and neither
h2 nor a JWT library is in requirements.txt, so an `apns` row is reported as
`not configured` rather than silently dropped (see the deferred backlog in
docs/backend_astro_depth_checklist_2026-08-06.md). The clean route for iOS is
to register the app with Firebase too, at which point the token the plugin
hands out is an FCM token and this transport covers both platforms.

Configuration is environment-only, never read from the repo:

    FCM_SERVICE_ACCOUNT_FILE   path to a Firebase service-account JSON
    FCM_PROJECT_ID             optional; defaults to the file's project_id
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
    transports["apns"] = NotConfiguredTransport(
        "apns", "apns transport not configured (register iOS with Firebase, or build an HTTP/2 APNs client)",
    )
    transports["web"] = NotConfiguredTransport("web")
    return transports
