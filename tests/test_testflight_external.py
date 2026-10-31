"""scripts/testflight_external.py: offline, with `_request` replaced."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("tfx", ROOT / "scripts" / "testflight_external.py")
tfx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tfx)


def _build(state, version="645"):
    return {"id": "B1", "attributes": {"version": version, "processingState": state, "expired": False}}


def test_waits_for_processing_then_returns(monkeypatch):
    states = iter([{"data": []}, {"data": [_build("PROCESSING")]}, {"data": [_build("VALID")]}])
    monkeypatch.setattr(tfx.asc, "_request", lambda *a, **k: next(states))
    assert tfx.wait_until_valid("t", 645, 600, sleep=lambda s: None)["id"] == "B1"


def test_failed_build_stops(monkeypatch):
    monkeypatch.setattr(tfx.asc, "_request", lambda *a, **k: {"data": [_build("INVALID")]})
    with pytest.raises(tfx.asc.AscError, match="INVALID"):
        tfx.wait_until_valid("t", 645, 600, sleep=lambda s: None)


def test_existing_review_submission_is_not_resubmitted(monkeypatch):
    calls = []

    def fake(method, path, token, body=None):
        calls.append(method)
        return {"data": {"attributes": {"betaReviewState": "WAITING_FOR_REVIEW"}}}

    monkeypatch.setattr(tfx.asc, "_request", fake)
    assert tfx.submit_for_beta_review("t", "B1") == "WAITING_FOR_REVIEW"
    assert calls == ["GET"]


def test_new_submission_posts_the_build(monkeypatch):
    calls = []

    def fake(method, path, token, body=None):
        calls.append((method, path, body))
        if method == "GET":
            return {"data": None}
        return {"data": {"attributes": {"betaReviewState": "WAITING_FOR_REVIEW"}}}

    monkeypatch.setattr(tfx.asc, "_request", fake)
    tfx.submit_for_beta_review("t", "B1")
    method, path, body = calls[-1]
    assert (method, path) == ("POST", "/betaAppReviewSubmissions")
    assert body["data"]["relationships"]["build"]["data"]["id"] == "B1"


def test_what_to_test_kept_when_present(monkeypatch):
    calls = []

    def fake(method, path, token, body=None):
        calls.append(method)
        return {"data": [{"id": "L1", "attributes": {"whatsNew": "already"}}]}

    monkeypatch.setattr(tfx.asc, "_request", fake)
    assert tfx.ensure_what_to_test("t", "B1", "new") == "kept"
    assert calls == ["GET"]


def test_never_touches_app_store_release():
    text = (ROOT / "scripts" / "testflight_external.py").read_text()
    for forbidden in ("appStoreVersionSubmissions", "reviewSubmissions\"", "appStoreVersionReleaseRequests"):
        assert forbidden not in text
