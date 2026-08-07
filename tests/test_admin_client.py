from unittest.mock import Mock

from psycopg.types.json import Json
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from astrospace.admin.audit_middleware import AppAuditMiddleware
from astrospace.admin.client import SupabaseAdminClient


def _db_fallback_client(monkeypatch):
    """A client with no Supabase secret, forcing the DATABASE_URL/psycopg fallback path."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/test")
    return SupabaseAdminClient("https://example.supabase.co", "")


def _raise_on_unadapted_dict(sql, values=()):
    """Mimics psycopg's real behavior: raw dict/list params can't be adapted to a placeholder."""
    for value in values:
        if isinstance(value, (dict, list)):
            raise TypeError(
                f"cannot adapt type '{type(value).__name__}' using placeholder '%s' (format)"
            )
    return [{"id": "row-1"}]


def test_db_insert_wraps_dict_and_list_values_as_json(monkeypatch):
    client = _db_fallback_client(monkeypatch)
    captured = {}

    def fake_write_returning(sql, values):
        captured["values"] = values
        return [{"id": "row-1"}]

    monkeypatch.setattr(client, "_db_write_returning", fake_write_returning)

    client.insert("knowledge_audit_log", {
        "action": "user.suspend",
        "before_state": {"banned_until": None},
        "after_state": {"banned_until": "876000h"},
        "reason": None,
    })

    values = captured["values"]
    assert values[0] == "user.suspend"
    assert isinstance(values[1], Json) and values[1].obj == {"banned_until": None}
    assert isinstance(values[2], Json) and values[2].obj == {"banned_until": "876000h"}


def test_db_patch_wraps_dict_values_as_json(monkeypatch):
    client = _db_fallback_client(monkeypatch)
    captured = {}

    def fake_write_returning(sql, values):
        captured["values"] = values
        return [{"id": "row-1"}]

    monkeypatch.setattr(client, "_db_write_returning", fake_write_returning)

    client.patch(
        "knowledge_sources",
        params={"id": "eq.row-1"},
        payload={"metadata": {"pages": 12}, "status": "ready"},
    )

    values = captured["values"]
    assert isinstance(values[0], Json) and values[0].obj == {"pages": 12}
    assert values[1] == "ready"


def test_insert_with_dict_valued_column_does_not_raise(monkeypatch):
    """Regression test: a dict-valued column (e.g. audit metadata) must not hit
    psycopg's 'cannot adapt type dict' error on the DATABASE_URL fallback path."""
    client = _db_fallback_client(monkeypatch)
    monkeypatch.setattr(client, "_db_write_returning", _raise_on_unadapted_dict)

    rows = client.insert("app_request_audit_log", {
        "actor_id": None,
        "method": "POST",
        "route": "/api/v1/kundlis",
        "status_code": 200,
        "metadata": {"query": ""},
    })

    assert rows == [{"id": "row-1"}]


def test_app_audit_middleware_never_500s_on_dict_valued_audit_payload(monkeypatch):
    """End-to-end: a mutating request must not fail because audit logging
    (which always sends a dict-valued 'metadata' field) can't reach the DB."""
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_SECRET_KEY", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/test")
    monkeypatch.setattr(SupabaseAdminClient, "_db_write_returning", staticmethod(_raise_on_unadapted_dict))

    async def mutate(request):
        return JSONResponse({"ok": True})

    app = Starlette(routes=[Route("/api/v1/kundlis/{kundli_id}", mutate, methods=["POST"])])
    app.add_middleware(AppAuditMiddleware)

    response = TestClient(app).post("/api/v1/kundlis/abcdef1234567890")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_rows_paginates_unbounded_queries(monkeypatch):
    client = SupabaseAdminClient("https://example.supabase.co", "secret")
    first = [{"id": value} for value in range(1000)]
    second = [{"id": value} for value in range(1000, 1438)]
    responses = [
        Mock(json=Mock(return_value=first)),
        Mock(json=Mock(return_value=second)),
    ]
    request = Mock(side_effect=responses)
    monkeypatch.setattr(client, "request", request)

    rows = client.rows("knowledge_chunks", params={"select": "id"})

    assert len(rows) == 1438
    assert request.call_args_list[0].kwargs["params"]["offset"] == 0
    assert request.call_args_list[1].kwargs["params"]["offset"] == 1000


def test_rows_respects_explicit_limit(monkeypatch):
    client = SupabaseAdminClient("https://example.supabase.co", "secret")
    request = Mock(return_value=Mock(json=Mock(return_value=[{"id": "one"}])))
    monkeypatch.setattr(client, "request", request)

    rows = client.rows("knowledge_chunks", params={"select": "id", "limit": 1})

    assert rows == [{"id": "one"}]
    request.assert_called_once()
