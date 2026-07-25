from unittest.mock import Mock

from astrospace.admin.client import SupabaseAdminClient


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
