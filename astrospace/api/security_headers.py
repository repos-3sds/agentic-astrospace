"""Baseline security headers on every response.

Deliberately no Content-Security-Policy: the Angular bundle's inline styles
and the Supabase/auth endpoints it talks to would need a policy verified
against the running SPA and the native WebView, and a wrong CSP fails as a
blank screen in production. These four are safe for any page and any API
response.
"""
from __future__ import annotations

from .auth import running_on_cloud_run

# 180 days, without includeSubDomains or preload: those are hard to undo once
# browsers have cached them, and sibling subdomains are not ours to decide for.
HSTS_VALUE = "max-age=15552000"


def security_headers(on_cloud_run: bool) -> list[tuple[bytes, bytes]]:
    headers = [
        (b"x-content-type-options", b"nosniff"),
        (b"referrer-policy", b"strict-origin-when-cross-origin"),
        (b"x-frame-options", b"DENY"),
    ]
    # Only where the service is actually served over HTTPS; on a developer's
    # http://localhost an HSTS header would be ignored at best.
    if on_cloud_run:
        headers.append((b"strict-transport-security", HSTS_VALUE.encode()))
    return headers


class SecurityHeadersMiddleware:
    """Pure ASGI, so streamed responses (SSE) are not buffered. A header the
    route already set wins."""

    def __init__(self, app, on_cloud_run: bool | None = None):
        self.app = app
        self.headers = security_headers(
            running_on_cloud_run() if on_cloud_run is None else on_cloud_run
        )

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                existing = {name.lower() for name, _ in message.get("headers", [])}
                extra = [(name, value) for name, value in self.headers if name not in existing]
                if extra:
                    message = {**message, "headers": [*message.get("headers", []), *extra]}
            await send(message)

        await self.app(scope, receive, send_with_headers)
