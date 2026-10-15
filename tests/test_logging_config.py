"""Structured logging (production audit 2026-10-15, P1 "Observability").

No logging was configured, so the INFO-level `astrospace.ask.cost` lines were
dropped in production and provider errors left no trace at all.
"""
import json
import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from astrospace.logging_config import (
    JsonFormatter, TraceContextMiddleware, configure_logging, current_trace,
    parse_trace_header,
)


def test_parse_trace_header():
    assert parse_trace_header("105445aa7843bc8bf206b120001000/1;o=1") == (
        "105445aa7843bc8bf206b120001000", "1",
    )
    assert parse_trace_header("abc") == ("abc", None)
    assert parse_trace_header("") is None
    assert parse_trace_header(None) is None


def test_configure_logging_is_idempotent_and_keeps_cost_lines():
    import main  # noqa: F401 — importing the app configures logging

    configure_logging()
    configure_logging()
    root = logging.getLogger()
    ours = [h for h in root.handlers if isinstance(h.formatter, JsonFormatter)]
    assert len(ours) == 1
    assert logging.getLogger("astrospace.ask.cost").isEnabledFor(logging.INFO)


def test_json_line_carries_the_cloud_trace(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "astro-proj")
    seen = {}

    app = FastAPI()
    app.add_middleware(TraceContextMiddleware)

    @app.get("/t")
    def t():  # sync: runs in the threadpool, like most routes here
        record = logging.LogRecord("astrospace.ask.cost", logging.INFO, __file__, 1,
                                   '{"event": "ask.cost"}', None, None)
        seen["line"] = JsonFormatter().format(record)
        seen["trace"] = current_trace()
        return {}

    TestClient(app).get("/t", headers={"X-Cloud-Trace-Context": "abc123/77;o=1"})
    entry = json.loads(seen["line"])
    assert entry["severity"] == "INFO"
    assert entry["logger"] == "astrospace.ask.cost"
    assert entry["logging.googleapis.com/trace"] == "projects/astro-proj/traces/abc123"
    assert entry["logging.googleapis.com/spanId"] == "77"
    assert seen["trace"] == ("abc123", "77")
    assert current_trace() is None  # reset after the request
