"""scripts/play_upload.py: the Play upload talks to Google only through
`_request`, which is replaced here, so these run offline. Signing uses the real
openssl against a throwaway key."""
from __future__ import annotations

import base64
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("play_upload", ROOT / "scripts" / "play_upload.py")
play_upload = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(play_upload)

needs_openssl = pytest.mark.skipif(shutil.which("openssl") is None, reason="openssl not installed")


def _b64url_decode(part: str) -> bytes:
    return base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))


@pytest.fixture
def key_file(tmp_path):
    pem = tmp_path / "test.pem"
    subprocess.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048",
                    "-out", str(pem)], check=True, capture_output=True)
    path = tmp_path / "play-publisher.json"
    path.write_text(json.dumps({
        "type": "service_account",
        "client_email": "play-publisher@example.iam.gserviceaccount.com",
        "private_key_id": "abc123",
        "private_key": pem.read_text(),
        "token_uri": "https://oauth2.googleapis.com/token",
    }))
    return path


@pytest.fixture
def aab(tmp_path):
    path = tmp_path / "app-release.aab"
    path.write_bytes(b"PK\x03\x04 fake bundle")
    return path


class FakePlay:
    """Records every call and answers like the Android Publisher API."""

    def __init__(self, version_code=560, track_codes=("547",), fail_on=None):
        self.calls = []
        self.version_code = version_code
        self.track_codes = list(track_codes)
        self.fail_on = fail_on

    def __call__(self, method, url, *, token=None, body=None, content_type=None, timeout=60):
        self.calls.append((method, url, body))
        if self.fail_on and self.fail_on(method, url):
            raise play_upload.PlayError(f"{method} failed (400): boom")
        if url.endswith("/token"):
            return {"access_token": "tok"}
        if method == "POST" and url.endswith("/edits"):
            return {"id": "e1"}
        if method == "GET" and "/tracks/" in url:
            return {"track": url.rsplit("/", 1)[1],
                    "releases": [{"status": "completed", "versionCodes": self.track_codes}]}
        if "/bundles" in url:
            return {"versionCode": self.version_code, "sha256": "x"}
        if method == "PUT":
            return json.loads(body)
        return {}

    def methods(self):
        return [(m, u.split("/edits")[-1].split("?")[0]) for m, u, _ in self.calls if not u.endswith("/token")]


@needs_openssl
def test_assertion_is_a_valid_rs256_jwt(key_file, tmp_path):
    key = play_upload.load_key(str(key_file))
    jwt = play_upload.build_assertion(key, now=1_000_000)
    header_b64, claims_b64, sig_b64 = jwt.split(".")
    assert json.loads(_b64url_decode(header_b64)) == {"alg": "RS256", "typ": "JWT", "kid": "abc123"}
    claims = json.loads(_b64url_decode(claims_b64))
    assert claims["iss"] == "play-publisher@example.iam.gserviceaccount.com"
    assert claims["scope"] == "https://www.googleapis.com/auth/androidpublisher"
    assert claims["exp"] - claims["iat"] == 3600

    pub = tmp_path / "pub.pem"
    subprocess.run(["openssl", "pkey", "-pubout", "-out", str(pub)], input=key["private_key"].encode(),
                   check=True, capture_output=True)
    sig = tmp_path / "sig.bin"
    sig.write_bytes(_b64url_decode(sig_b64))
    verify = subprocess.run(["openssl", "dgst", "-sha256", "-verify", str(pub), "-signature", str(sig)],
                            input=f"{header_b64}.{claims_b64}".encode(), capture_output=True)
    assert verify.returncode == 0, verify.stdout + verify.stderr


@needs_openssl
def test_upload_happy_path_commits_a_completed_internal_release(key_file, aab, monkeypatch, capsys):
    fake = FakePlay()
    monkeypatch.setattr(play_upload, "_request", fake)
    assert play_upload.main([str(aab), "--key", str(key_file), "--notes", "Festival guidance."]) == 0

    assert fake.methods() == [
        ("POST", ""), ("GET", "/e1/tracks/internal"), ("POST", "/e1/bundles"),
        ("PUT", "/e1/tracks/internal"), ("POST", "/e1:commit"),
    ]
    put_body = json.loads(next(b for m, _, b in fake.calls if m == "PUT"))
    assert put_body == {"track": "internal", "releases": [{
        "versionCodes": ["560"], "status": "completed",
        "releaseNotes": [{"language": "en-IN", "text": "Festival guidance."}],
    }]}
    bundle_call = next(c for c in fake.calls if "/bundles" in c[1])
    assert "/upload/androidpublisher/" in bundle_call[1] and "uploadType=media" in bundle_call[1]
    assert bundle_call[2] == aab.read_bytes()
    out = capsys.readouterr()
    assert "versionCode 560" in out.out
    assert "PRIVATE KEY" not in out.out + out.err


@pytest.mark.parametrize("track", ["production", "beta", "Internal"])
def test_tracks_other_than_internal_and_alpha_are_refused_before_any_request(track, aab, monkeypatch, capsys):
    fake = FakePlay()
    monkeypatch.setattr(play_upload, "_request", fake)
    assert play_upload.main([str(aab), "--track", track]) == 1
    assert fake.calls == []
    assert "not allowed" in capsys.readouterr().err


@needs_openssl
def test_alpha_track_is_accepted(key_file, aab, monkeypatch):
    fake = FakePlay()
    monkeypatch.setattr(play_upload, "_request", fake)
    assert play_upload.main([str(aab), "--track", "alpha", "--key", str(key_file)]) == 0
    assert ("PUT", "/e1/tracks/alpha") in fake.methods()


@needs_openssl
def test_stale_version_code_discards_the_edit(key_file, aab, monkeypatch, capsys):
    fake = FakePlay(version_code=547, track_codes=("547",))
    monkeypatch.setattr(play_upload, "_request", fake)
    assert play_upload.main([str(aab), "--key", str(key_file)]) == 1
    methods = fake.methods()
    assert ("DELETE", "/e1") in methods
    assert not any(u.endswith(":commit") for _, u in methods)
    assert "not above 547" in capsys.readouterr().err


@needs_openssl
def test_failed_commit_discards_the_edit(key_file, aab, monkeypatch):
    fake = FakePlay(fail_on=lambda m, u: u.endswith(":commit"))
    monkeypatch.setattr(play_upload, "_request", fake)
    assert play_upload.main([str(aab), "--key", str(key_file)]) == 1
    assert fake.methods()[-1] == ("DELETE", "/e1")


@needs_openssl
def test_changes_not_sent_for_review_flag(key_file, aab, monkeypatch):
    fake = FakePlay()
    monkeypatch.setattr(play_upload, "_request", fake)
    assert play_upload.main([str(aab), "--key", str(key_file), "--changes-not-sent-for-review"]) == 0
    assert fake.calls[-1][1].endswith(":commit?changesNotSentForReview=true")


@needs_openssl
def test_check_mode_reads_the_track_and_changes_nothing(key_file, monkeypatch, capsys):
    fake = FakePlay()
    monkeypatch.setattr(play_upload, "_request", fake)
    assert play_upload.main(["--check", "--key", str(key_file)]) == 0
    assert fake.methods() == [("POST", ""), ("GET", "/e1/tracks/internal"), ("DELETE", "/e1")]
    assert "completed 547" in capsys.readouterr().out


def test_missing_key_and_bad_file_fail_plainly(tmp_path, aab, monkeypatch, capsys):
    monkeypatch.setattr(play_upload, "_request", FakePlay())
    monkeypatch.setenv("PLAY_SERVICE_ACCOUNT_JSON", str(tmp_path / "nope.json"))
    assert play_upload.main([str(aab)]) == 1
    assert "key not found" in capsys.readouterr().err
    not_aab = tmp_path / "app.apk"
    not_aab.write_bytes(b"x")
    assert play_upload.main([str(not_aab)]) == 1
    assert "not an .aab" in capsys.readouterr().err


def test_key_path_defaults_to_the_mac_location(tmp_path, monkeypatch):
    monkeypatch.delenv("PLAY_SERVICE_ACCOUNT_JSON", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    with pytest.raises(play_upload.PlayError) as exc:
        play_upload.load_key()
    assert ".config/astrospace/play-publisher.json" in str(exc.value)
