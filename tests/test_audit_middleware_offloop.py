"""The request audit write runs off the event loop, bounded, and never breaks
a request (production audit 2026-10-15, P1 "Event loop").

It used to be a synchronous Supabase insert with a 45 s timeout inside an
async middleware, which froze the whole instance — SSE streams included —
whenever Supabase was slow.
"""
import threading
import time

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from astrospace.admin import audit_middleware
from astrospace.admin.audit_middleware import AppAuditMiddleware


def _app():
    async def mutate(request):
        return JSONResponse({"ok": True})

    app = Starlette(routes=[
        Route("/api/v1/kundlis", mutate, methods=["POST"]),
        Route("/api/v1/me", mutate, methods=["DELETE"]),
    ])
    app.add_middleware(AppAuditMiddleware)
    return app


def test_insert_runs_off_the_event_loop(monkeypatch):
    threads = []

    class FakeAdmin:
        def insert(self, table, payload, **kwargs):
            threads.append(threading.current_thread().name)
            assert kwargs["timeout"] <= 5
            return [payload]

    monkeypatch.setattr(audit_middleware, "get_admin_client", lambda: FakeAdmin())
    loop_thread = []

    async def mark(request):
        loop_thread.append(threading.current_thread().name)
        return JSONResponse({})

    app = Starlette(routes=[Route("/api/v1/kundlis", mark, methods=["POST"])])
    app.add_middleware(AppAuditMiddleware)
    assert TestClient(app).post("/api/v1/kundlis").status_code == 200
    assert threads and threads[0] != loop_thread[0]


def test_a_slow_audit_store_is_cut_off(monkeypatch):
    monkeypatch.setattr(audit_middleware, "AUDIT_WRITE_TIMEOUT_SECONDS", 0.1)

    class SlowAdmin:
        def insert(self, table, payload, **kwargs):
            time.sleep(1.0)

    monkeypatch.setattr(audit_middleware, "get_admin_client", lambda: SlowAdmin())
    started = time.monotonic()
    response = TestClient(_app()).post("/api/v1/kundlis")
    assert response.status_code == 200
    assert time.monotonic() - started < 0.9


def test_any_audit_failure_is_logged_not_raised(monkeypatch, caplog):
    class BrokenAdmin:
        def insert(self, table, payload, **kwargs):
            raise ValueError("unexpected shape")

    monkeypatch.setattr(audit_middleware, "get_admin_client", lambda: BrokenAdmin())
    response = TestClient(_app()).post("/api/v1/kundlis")
    assert response.status_code == 200
    assert "request audit write failed" in caplog.text


def test_account_deletion_row_carries_no_email(monkeypatch):
    captured = []

    class FakeAdmin:
        def insert(self, table, payload, **kwargs):
            captured.append(payload)

    monkeypatch.setattr(audit_middleware, "get_admin_client", lambda: FakeAdmin())

    async def delete_me(request):
        from astrospace.api.auth import AuthUser
        request.state.auth_user = AuthUser(id="u1", email="gone@example.com")
        return JSONResponse({"deleted": True})

    app = Starlette(routes=[Route("/api/v1/me", delete_me, methods=["DELETE"])])
    app.add_middleware(AppAuditMiddleware)
    TestClient(app).delete("/api/v1/me")
    assert captured and captured[0]["actor_email"] is None
    assert captured[0]["actor_id"] == audit_middleware.pseudonymous_actor_id("u1")
    assert "u1" not in captured[0]["actor_id"]
