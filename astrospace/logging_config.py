"""Structured logging for Cloud Run.

Nothing configured logging before this, so every INFO line — including the
`astrospace.ask.cost` line the launch plan reads cost per answer from — was
dropped by the root logger's WARNING default. Cloud Logging parses one JSON
object per stdout line: `severity` sets the level, `message` the summary, and
`logging.googleapis.com/trace` ties the line to the request that produced it,
so a provider failure can be read next to the request that hit it.

The trace id comes from the `X-Cloud-Trace-Context` header Cloud Run's front
end adds to every request (`TRACE_ID/SPAN_ID;o=1`). `TraceContextMiddleware`
stores it in a context variable; Starlette copies the context into the worker
threads sync routes and streams run on, so lines logged there carry it too.
"""
from __future__ import annotations

import contextvars
import json
import logging
import os
import sys
from datetime import datetime, timezone

_trace: contextvars.ContextVar[tuple[str, str | None] | None] = contextvars.ContextVar(
    "astrospace_trace", default=None,
)

_HANDLER_FLAG = "_astrospace_json_handler"


def parse_trace_header(value: str | None) -> tuple[str, str | None] | None:
    """`TRACE_ID/SPAN_ID;o=1` -> (trace_id, span_id). None when absent."""
    if not value:
        return None
    trace_id, _, rest = value.partition("/")
    trace_id = trace_id.strip()
    if not trace_id:
        return None
    span_id = rest.split(";", 1)[0].strip() or None
    return trace_id, span_id


def current_trace() -> tuple[str, str | None] | None:
    return _trace.get()


def _project_id() -> str | None:
    # Cloud Run does not set a project variable itself; set GOOGLE_CLOUD_PROJECT
    # on the service so Cloud Logging can link the line to its trace. Without
    # it the raw trace id is still logged.
    return os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "time": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        trace = current_trace()
        if trace:
            trace_id, span_id = trace
            project = _project_id()
            entry["logging.googleapis.com/trace"] = (
                f"projects/{project}/traces/{trace_id}" if project else trace_id
            )
            if span_id:
                entry["logging.googleapis.com/spanId"] = span_id
        return json.dumps(entry, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    """Install one JSON stdout handler on the root logger. Idempotent:
    `main` is imported more than once (uvicorn re-imports it; tests reload
    it), and a second handler would print every line twice."""
    root = logging.getLogger()
    if not any(getattr(handler, _HANDLER_FLAG, False) for handler in root.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        setattr(handler, _HANDLER_FLAG, True)
        root.addHandler(handler)
    if root.level == logging.NOTSET or root.level > level:
        root.setLevel(level)
    # Pinned explicitly so a later root reconfiguration (uvicorn's log config,
    # a test's caplog) cannot silently drop the cost lines again.
    logging.getLogger("astrospace").setLevel(level)


class TraceContextMiddleware:
    """Pure ASGI (not BaseHTTPMiddleware) so the context variable it sets is
    visible to the route, its threadpool workers and its streamed body."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        header = None
        for name, value in scope.get("headers") or ():
            if name == b"x-cloud-trace-context":
                header = value.decode("latin-1")
                break
        token = _trace.set(parse_trace_header(header))
        try:
            await self.app(scope, receive, send)
        finally:
            _trace.reset(token)
