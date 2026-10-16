from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import time
from urllib.parse import parse_qsl, urlencode
from uuid import uuid4

from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware

from .client import AdminStorageError, get_admin_client

log = logging.getLogger(__name__)

# The audit write is a network call to Supabase on every mutating request.
# It used to run synchronously inside this async middleware with the admin
# client's 45 s timeout, which froze the whole instance — SSE streams
# included — whenever Supabase was slow. It now runs in the threadpool, and
# the request waits at most this long for it. Awaited rather than fired and
# forgotten because Cloud Run throttles CPU once the response is sent, so
# background work after it is not reliably run.
AUDIT_WRITE_TIMEOUT_SECONDS = 3.0

# Machine-to-machine endpoints with no signed-in actor. The RevenueCat webhook
# authenticates with a shared secret and writes its own audit rows for every
# applied event; RevenueCat retries anything slow or non-2xx, so nothing here
# may add latency to it. The email routes under /api/v1/email/ are the same
# kind (no actor: a Svix-signed webhook and signed unsubscribe links), and
# an unsubscribe link's token must not be copied into the audit table.
_UNAUDITED_PREFIXES = ("/api/v1/store/revenuecat/", "/api/v1/email/")

_RESOURCE_RE = re.compile(
    r"^/api/v1/(?P<resource>kundlis|readings|settings|ask|admin)"
    r"(?:/(?P<resource_id>[0-9a-f-]{8,}))?"
)

# Query parameters whose values must never reach the audit table. The native
# auth bridge (/api/v1/auth/native-callback?code=…) carries a one-time PKCE
# code, and Supabase's recovery/magic-link redirects carry tokens; until
# 2026-10-15 the first 500 characters of every query string were stored
# verbatim, which put those credentials in a table admins can read.
_SENSITIVE_QUERY_KEYS = frozenset({
    "code", "token", "access_token", "refresh_token", "id_token",
    "token_hash", "state", "code_verifier", "password", "api_key", "apikey",
})
_REDACTED = "[redacted]"


def pseudonymous_actor_id(user_id: str) -> str:
    """What a deleted account's `actor_id` becomes in app_request_audit_log.

    Stable, so an erased actor's requests still group together, and not
    reversible to the account id. The database only permits an update that
    sets exactly this value (md5 of the old id) and clears the email — see
    supabase/migrations/20261015130000_allow_request_audit_erasure.sql."""
    return "erased:" + hashlib.md5(user_id.encode()).hexdigest()


def redact_query(query: str, limit: int = 500) -> str:
    """Return the query string with credential-bearing values masked.

    Keys are compared case-insensitively; the key itself is kept so the log
    still shows *which* flow ran. Anything that fails to parse is dropped
    rather than stored as-is, because an unparsable string could still hold
    a token.
    """
    if not query:
        return ""
    try:
        pairs = parse_qsl(query, keep_blank_values=True)
    except ValueError:
        return _REDACTED
    masked = [
        (key, _REDACTED if key.lower() in _SENSITIVE_QUERY_KEYS else value)
        for key, value in pairs
    ]
    return urlencode(masked)[:limit]


class AppAuditMiddleware(BaseHTTPMiddleware):
    """Append a lightweight audit event for every mutating application request."""

    async def dispatch(self, request, call_next):
        started = time.monotonic()
        request_id = str(uuid4())
        response = await call_next(request)
        if (
            request.method in {"POST", "PUT", "PATCH", "DELETE"}
            and request.url.path.startswith("/api/v1/")
            and not request.url.path.startswith("/api/v1/admin/")
            and not request.url.path.startswith(_UNAUDITED_PREFIXES)
        ):
            match = _RESOURCE_RE.match(request.url.path)
            user = getattr(request.state, "auth_user", None)
            # Account deletion erases the caller's email from this log
            # (me_routes.delete_account); its own row must not write it back.
            erasing = request.method == "DELETE" and request.url.path.rstrip("/") == "/api/v1/me"
            actor_id = getattr(user, "id", None)
            payload = {
                "actor_id": pseudonymous_actor_id(actor_id) if erasing and actor_id else actor_id,
                "actor_email": None if erasing else getattr(user, "email", None),
                "method": request.method,
                "route": request.url.path,
                "status_code": response.status_code,
                "resource_type": match.group("resource") if match else None,
                "resource_id": match.group("resource_id") if match else None,
                "request_id": request_id,
                "duration_ms": round((time.monotonic() - started) * 1000),
                "metadata": {"query": redact_query(str(request.url.query))},
            }
            await write_audit_event(payload)
        response.headers["X-Request-ID"] = request_id
        return response


def _insert(payload: dict) -> None:
    try:
        client = get_admin_client()
    except AdminStorageError:
        return  # no audit storage configured (local development)
    client.insert(
        "app_request_audit_log", payload, timeout=AUDIT_WRITE_TIMEOUT_SECONDS,
    )


async def write_audit_event(payload: dict) -> None:
    """Off the event loop, bounded, and never raising: audit storage must not
    break or stall the user's primary workflow."""
    try:
        await asyncio.wait_for(run_in_threadpool(_insert, payload),
                               timeout=AUDIT_WRITE_TIMEOUT_SECONDS)
    except Exception:
        log.warning("request audit write failed (route=%s)", payload.get("route"),
                    exc_info=True)
