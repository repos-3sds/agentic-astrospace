"""scripts/asc.py: App Store Connect calls go through `_request`, which is
replaced here, so these run offline. Token signing uses the real openssl
against a throwaway P-256 key, the same kind Apple issues as a .p8."""
from __future__ import annotations

import base64
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("asc", ROOT / "scripts" / "asc.py")
asc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(asc)

needs_openssl = pytest.mark.skipif(shutil.which("openssl") is None, reason="openssl not installed")


def _b64url_decode(part: str) -> bytes:
    return base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))


def _raw_to_der(raw: bytes) -> bytes:
    def integer(value: bytes) -> bytes:
        value = value.lstrip(b"\x00") or b"\x00"
        if value[0] & 0x80:
            value = b"\x00" + value
        return bytes([0x02, len(value)]) + value
    body = integer(raw[:32]) + integer(raw[32:])
    return bytes([0x30, len(body)]) + body


@pytest.fixture
def p8(tmp_path):
    path = tmp_path / "AuthKey_TEST.p8"
    subprocess.run(["openssl", "genpkey", "-algorithm", "EC", "-pkeyopt", "ec_paramgen_curve:P-256",
                    "-out", str(path)], check=True, capture_output=True)
    return path


@needs_openssl
def test_token_is_a_valid_es256_jwt(p8, tmp_path):
    token = asc.build_token("KEY123", "issuer-uuid", p8.read_text(), now=1_700_000_000)
    header_b64, claims_b64, sig_b64 = token.split(".")
    assert json.loads(_b64url_decode(header_b64)) == {"alg": "ES256", "kid": "KEY123", "typ": "JWT"}
    claims = json.loads(_b64url_decode(claims_b64))
    assert claims["iss"] == "issuer-uuid" and claims["aud"] == "appstoreconnect-v1"
    assert claims["exp"] - claims["iat"] <= 1200  # Apple's 20-minute ceiling

    raw = _b64url_decode(sig_b64)
    assert len(raw) == 64
    pub = tmp_path / "pub.pem"
    subprocess.run(["openssl", "pkey", "-in", str(p8), "-pubout", "-out", str(pub)], check=True)
    sig = tmp_path / "sig.der"
    sig.write_bytes(_raw_to_der(raw))
    verify = subprocess.run(["openssl", "dgst", "-sha256", "-verify", str(pub), "-signature", str(sig)],
                            input=f"{header_b64}.{claims_b64}".encode(), capture_output=True)
    assert verify.returncode == 0, verify.stderr


def test_der_conversion_pads_short_integers():
    r, s = b"\x01" * 31, b"\x80" + b"\x02" * 31
    raw = asc.der_to_raw_signature(_raw_to_der(b"\x00" + r + s))
    assert raw == b"\x00" + r + s


def test_highest_build_ignores_non_numeric_versions():
    builds = [{"attributes": {"version": "587"}}, {"attributes": {"version": "1.0"}},
              {"attributes": {"version": "1203"}}, {"attributes": {}}]
    assert asc.highest_build(builds) == 1203
    assert asc.highest_build([]) == 0


def _profile(pid, state="ACTIVE", kind="IOS_APP_STORE", bundle="B1", certs=("C1",)):
    return {"id": pid, "attributes": {"profileType": kind, "profileState": state, "name": pid,
                                      "uuid": pid, "profileContent": ""},
            "relationships": {"bundleId": {"data": {"type": "bundleIds", "id": bundle}},
                              "certificates": {"data": [{"type": "certificates", "id": c} for c in certs]}}}


def test_pick_profile_needs_active_app_store_profile_with_our_cert():
    profiles = [
        _profile("invalid", state="INVALID"),
        _profile("dev", kind="IOS_APP_DEVELOPMENT"),
        _profile("other-app", bundle="B2"),
        _profile("other-cert", certs=("C9",)),
        _profile("good", certs=("C9", "C1")),
    ]
    assert asc.pick_profile(profiles, "B1", "C1")["id"] == "good"
    assert asc.pick_profile(profiles[:4], "B1", "C1") is None


def test_ensure_profile_creates_one_when_none_fits(monkeypatch):
    calls = []

    def fake(method, path, token, body=None):
        calls.append((method, path.split("?")[0], body))
        if path.startswith("/certificates"):
            return {"data": [{"id": "C1", "attributes": {"serialNumber": "0A1B2C"}}]}
        if path.startswith("/bundleIds"):
            return {"data": [{"id": "B0", "attributes": {"identifier": "app.asksiddha.mobile.widget"}},
                             {"id": "B1", "attributes": {"identifier": "app.asksiddha.mobile"}}]}
        if method == "GET" and path.startswith("/profiles"):
            return {"data": [_profile("stale", state="INVALID")]}
        if method == "POST" and path == "/profiles":
            return {"data": _profile("new")}
        raise AssertionError(path)

    monkeypatch.setattr(asc, "_request", fake)
    profile = asc.ensure_profile("t", "serial=A1B2C")  # openssl's spelling, leading zero dropped
    assert profile["id"] == "new"
    method, path, body = calls[-1]
    assert (method, path) == ("POST", "/profiles")
    rel = body["data"]["relationships"]
    assert rel["bundleId"]["data"]["id"] == "B1"
    assert rel["certificates"]["data"] == [{"type": "certificates", "id": "C1"}]
    assert body["data"]["attributes"]["profileType"] == "IOS_APP_STORE"


def test_widget_extension_gets_its_own_profile(monkeypatch):
    calls = []

    def fake(method, path, token, body=None):
        calls.append((method, path.split("?")[0], body))
        if path.startswith("/certificates"):
            return {"data": [{"id": "C1", "attributes": {"serialNumber": "0A1B2C"}}]}
        if path.startswith("/bundleIds"):
            return {"data": [{"id": "B1", "attributes": {"identifier": "app.asksiddha.mobile"}},
                             {"id": "B2", "attributes": {"identifier": "app.asksiddha.mobile.widgets"}}]}
        if method == "GET" and path.startswith("/profiles"):
            # The app's own profile carries the certificate but not this App ID.
            return {"data": [_profile("app", bundle="B1")]}
        if method == "POST" and path == "/profiles":
            return {"data": _profile("new")}
        raise AssertionError(path)

    monkeypatch.setattr(asc, "_request", fake)
    profile = asc.ensure_profile("t", "0A1B2C", asc.WIDGETS_BUNDLE_ID)
    assert profile["id"] == "new"
    body = calls[-1][2]["data"]
    assert body["relationships"]["bundleId"]["data"]["id"] == "B2"
    assert body["attributes"]["name"].startswith("Siddha CI App Store Widgets ")


def test_unknown_certificate_is_a_clear_error(monkeypatch):
    monkeypatch.setattr(asc, "_request", lambda *a, **k: {"data": []})
    with pytest.raises(asc.AscError, match="no distribution certificate"):
        asc.find_certificate("t", "DEADBEEF")


def test_no_command_can_submit_or_release():
    text = (ROOT / "scripts" / "asc.py").read_text()
    for forbidden in ("appStoreVersionSubmissions", "reviewSubmissions", "betaAppReviewSubmissions",
                      "appStoreVersionReleaseRequests", "betaGroups"):
        assert forbidden not in text
