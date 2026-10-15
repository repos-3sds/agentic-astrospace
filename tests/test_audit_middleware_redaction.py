"""The request audit log must never persist auth codes or tokens from a query string."""
from __future__ import annotations

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from astrospace.admin import audit_middleware
from astrospace.admin.audit_middleware import AppAuditMiddleware, redact_query


def test_redact_query_masks_credential_values_but_keeps_keys():
    out = redact_query("code=abc123&next=%2Fm%2Ftoday&Token=xyz")
    assert "abc123" not in out
    assert "xyz" not in out
    assert "code=%5Bredacted%5D" in out
    assert "next=%2Fm%2Ftoday" in out


def test_redact_query_handles_empty_and_long_strings():
    assert redact_query("") == ""
    assert len(redact_query("q=" + "x" * 2000)) <= 500


def test_middleware_stores_redacted_query(monkeypatch):
    captured: list[dict] = []

    class FakeAdmin:
        def insert(self, table, payload, **kwargs):
            captured.append(payload)
            return [payload]

    monkeypatch.setattr(audit_middleware, "get_admin_client", lambda: FakeAdmin())

    async def mutate(request):
        return JSONResponse({"ok": True})

    app = Starlette(routes=[Route("/api/v1/ask/{thread_id}", mutate, methods=["POST"])])
    app.add_middleware(AppAuditMiddleware)

    response = TestClient(app).post(
        "/api/v1/ask/abcdef1234567890?code=pkce-secret&access_token=tok&page=2"
    )

    assert response.status_code == 200
    assert len(captured) == 1
    query = captured[0]["metadata"]["query"]
    assert "pkce-secret" not in query
    assert "access_token=tok" not in query
    assert "access_token=%5Bredacted%5D" in query
    assert "page=2" in query
