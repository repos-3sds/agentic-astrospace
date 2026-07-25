from __future__ import annotations

import re
import time
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware

from .client import AdminStorageError, get_admin_client

_RESOURCE_RE = re.compile(
    r"^/api/v1/(?P<resource>kundlis|readings|settings|ask|admin)"
    r"(?:/(?P<resource_id>[0-9a-f-]{8,}))?"
)


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
                "metadata": {"query": str(request.url.query)[:500]},
            }
            try:
                get_admin_client().insert("app_request_audit_log", payload)
            except AdminStorageError:
                # Audit storage must not break the user's primary workflow.
                pass
        response.headers["X-Request-ID"] = request_id
        return response
