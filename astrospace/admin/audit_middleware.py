from __future__ import annotations

import re
import time
from urllib.parse import parse_qsl, urlencode
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware

from .client import AdminStorageError, get_admin_client

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
        ):
            match = _RESOURCE_RE.match(request.url.path)
            user = getattr(request.state, "auth_user", None)
            payload = {
                "actor_id": getattr(user, "id", None),
                "actor_email": getattr(user, "email", None),
                "method": request.method,
                "route": request.url.path,
                "status_code": response.status_code,
                "resource_type": match.group("resource") if match else None,
                "resource_id": match.group("resource_id") if match else None,
                "request_id": request_id,
                "duration_ms": round((time.monotonic() - started) * 1000),
                "metadata": {"query": redact_query(str(request.url.query))},
            }
            try:
                get_admin_client().insert("app_request_audit_log", payload)
            except AdminStorageError:
                # Audit storage must not break the user's primary workflow.
                pass
        response.headers["X-Request-ID"] = request_id
        return response
