"""Baseline security headers on every response.

The Content-Security-Policy ships as *Report-Only* (security audit S13): a
wrong enforced CSP fails as a blank screen in production, so violations are
reported to the browser console first and the policy is enforced only once
it has run clean. The inline theme script in index.html is allowed by its
hash, computed from the built file, so it stays right when the script
changes. The other four headers are safe for any page and any API response.
"""
from __future__ import annotations

import base64
import hashlib
import re
from pathlib import Path

from .auth import running_on_cloud_run

# 180 days, without includeSubDomains or preload: those are hard to undo once
# browsers have cached them, and sibling subdomains are not ours to decide for.
HSTS_VALUE = "max-age=15552000"


_INLINE_SCRIPT = re.compile(r"<script>(.*?)</script>", re.S)
# Angular's critical-CSS inlining loads the full stylesheet with
# onload="this.media='all'"; an event handler needs 'unsafe-hashes'.
_INLINE_HANDLER = re.compile(r"\son[a-z]+=\"([^\"]*)\"")


def _sha256(text: str) -> str:
    return "'sha256-" + base64.b64encode(hashlib.sha256(text.encode()).digest()).decode() + "'"


def content_security_policy(index_html: str | None = None) -> str:
    hashes = [_sha256(body) for body in _INLINE_SCRIPT.findall(index_html or "")]
    handlers = sorted({_sha256(body) for body in _INLINE_HANDLER.findall(index_html or "")})
    if handlers:
        hashes += ["'unsafe-hashes'", *handlers]
    return "; ".join([
        "default-src 'self'",
        "script-src " + " ".join(["'self'", *hashes]),
        # Angular writes component styles inline.
        "style-src 'self' 'unsafe-inline'",
        "font-src 'self' data:",
        "img-src 'self' data: blob:",
        "media-src 'self' blob: https://storage.googleapis.com",
        "connect-src 'self' https://*.supabase.co wss://*.supabase.co https://eu.i.posthog.com",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
        "object-src 'none'",
    ])


def _built_index() -> str | None:
    path = Path(__file__).resolve().parents[2] / "frontend" / "dist" / "browser" / "index.html"
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def security_headers(on_cloud_run: bool, index_html: str | None = None) -> list[tuple[bytes, bytes]]:
    headers = [
        (b"content-security-policy-report-only", content_security_policy(index_html).encode()),
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
            running_on_cloud_run() if on_cloud_run is None else on_cloud_run,
            _built_index(),
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
