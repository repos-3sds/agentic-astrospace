"""Upload a signed AAB to a Google Play testing track and roll it out.

The Mac builds the AAB; this sends it to Play so a build reaches testers
without dragging the file into Play Console (docs/native_builds.md, "Uploading
to Play"). Standard library plus the `openssl` binary only, so it runs from the
repo's .venv or the system python3 with nothing to install.

    python3 scripts/play_upload.py ui/android/app/build/outputs/bundle/release/app-release.aab
    python3 scripts/play_upload.py app-release.aab --notes "Festival guidance on Calendar."
    python3 scripts/play_upload.py --check          # credentials and track only, changes nothing

The service-account key is read from $PLAY_SERVICE_ACCOUNT_JSON, defaulting to
~/.config/astrospace/play-publisher.json. Its contents are never printed.

Only the internal and alpha (closed testing) tracks are accepted. Production is
refused here on purpose, and the service account has no production access
either, so a slip cannot reach the public listing.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PACKAGE = "app.asksiddha.mobile"
DEFAULT_KEY = "~/.config/astrospace/play-publisher.json"
KEY_ENV = "PLAY_SERVICE_ACCOUNT_JSON"
ALLOWED_TRACKS = ("internal", "alpha")
# The listing's default language (store/play/play_console_setup.md).
NOTES_LANGUAGE = "en-IN"

TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPE = "https://www.googleapis.com/auth/androidpublisher"
API = "https://androidpublisher.googleapis.com/androidpublisher/v3/applications"
UPLOAD_API = "https://androidpublisher.googleapis.com/upload/androidpublisher/v3/applications"


class PlayError(RuntimeError):
    pass


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def load_key(path: str | None = None) -> dict:
    key_path = Path(os.path.expanduser(path or os.environ.get(KEY_ENV) or DEFAULT_KEY))
    if not key_path.is_file():
        raise PlayError(f"service-account key not found at {key_path} (set {KEY_ENV} to override)")
    try:
        key = json.loads(key_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PlayError(f"could not read the key at {key_path}: {exc.__class__.__name__}") from None
    if key.get("type") != "service_account" or not key.get("private_key") or not key.get("client_email"):
        raise PlayError(f"{key_path} is not a service-account key")
    return key


def sign_rs256(message: bytes, private_key_pem: str) -> bytes:
    """RS256 with the system openssl. The PEM sits in a private temp file only
    for the length of the call."""
    fd, pem_path = tempfile.mkstemp(prefix="play-key-", suffix=".pem")
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(private_key_pem)
        proc = subprocess.run(
            ["openssl", "dgst", "-sha256", "-sign", pem_path],
            input=message,
            capture_output=True,
            check=False,
        )
    finally:
        os.unlink(pem_path)
    if proc.returncode != 0 or not proc.stdout:
        raise PlayError("openssl could not sign the token request")
    return proc.stdout


def build_assertion(key: dict, now: int | None = None) -> str:
    now = int(time.time()) if now is None else now
    header = {"alg": "RS256", "typ": "JWT"}
    if key.get("private_key_id"):
        header["kid"] = key["private_key_id"]
    claims = {
        "iss": key["client_email"],
        "scope": SCOPE,
        "aud": key.get("token_uri") or TOKEN_URL,
        "iat": now,
        "exp": now + 3600,
    }
    signing_input = f"{_b64url(json.dumps(header).encode())}.{_b64url(json.dumps(claims).encode())}"
    return f"{signing_input}.{_b64url(sign_rs256(signing_input.encode('ascii'), key['private_key']))}"


def _request(method: str, url: str, *, token: str | None = None, body: bytes | None = None,
             content_type: str | None = None, timeout: float = 60) -> dict:
    req = urllib.request.Request(url, data=body, method=method)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    if content_type:
        req.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(detail)["error"]["message"]
        except (ValueError, KeyError, TypeError):
            detail = detail[:500]
        raise PlayError(f"{method} {url.split('?')[0]} failed ({exc.code}): {detail}") from None
    except urllib.error.URLError as exc:
        raise PlayError(f"{method} {url.split('?')[0]} failed: {exc.reason}") from None
    return json.loads(raw) if raw else {}


def access_token(key: dict) -> str:
    form = urllib.parse.urlencode({
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": build_assertion(key),
    }).encode()
    data = _request("POST", key.get("token_uri") or TOKEN_URL, body=form,
                    content_type="application/x-www-form-urlencoded")
    if not data.get("access_token"):
        raise PlayError("Google returned no access token")
    return data["access_token"]


class Edit:
    """One Play edit: everything inside it is invisible until commit, and a
    failed run deletes it so nothing half-done is left behind."""

    def __init__(self, token: str, package: str = PACKAGE):
        self.token = token
        self.package = package
        self.id: str | None = None

    @property
    def base(self) -> str:
        return f"{API}/{self.package}/edits/{self.id}"

    def open(self) -> None:
        self.id = _request("POST", f"{API}/{self.package}/edits", token=self.token,
                           body=b"{}", content_type="application/json")["id"]

    def track(self, track: str) -> dict:
        return _request("GET", f"{self.base}/tracks/{track}", token=self.token)

    def upload_bundle(self, aab: Path) -> int:
        url = f"{UPLOAD_API}/{self.package}/edits/{self.id}/bundles?uploadType=media"
        data = _request("POST", url, token=self.token, body=aab.read_bytes(),
                        content_type="application/octet-stream", timeout=900)
        return int(data["versionCode"])

    def set_release(self, track: str, version_code: int, notes: str | None, status: str = "completed") -> dict:
        release: dict = {"versionCodes": [str(version_code)], "status": status}
        if notes:
            release["releaseNotes"] = [{"language": NOTES_LANGUAGE, "text": notes}]
        body = json.dumps({"track": track, "releases": [release]}).encode()
        return _request("PUT", f"{self.base}/tracks/{track}", token=self.token,
                        body=body, content_type="application/json")

    def commit(self, changes_not_sent_for_review: bool = False) -> dict:
        query = "?changesNotSentForReview=true" if changes_not_sent_for_review else ""
        return _request("POST", f"{self.base}:commit{query}", token=self.token)

    def discard(self) -> None:
        if self.id:
            try:
                _request("DELETE", self.base, token=self.token)
            except PlayError:
                pass  # Play expires abandoned edits on its own.
            self.id = None


def highest_version(track: dict) -> int:
    codes = [int(c) for r in track.get("releases", []) for c in r.get("versionCodes", [])]
    return max(codes, default=0)


def describe(track: dict) -> str:
    parts = [f"{r.get('status')} {','.join(r.get('versionCodes', []))}" for r in track.get("releases", [])]
    return "; ".join(parts) or "no releases"


def check_track(track: str) -> None:
    if track not in ALLOWED_TRACKS:
        raise PlayError(f"track {track!r} is not allowed; use one of {', '.join(ALLOWED_TRACKS)} "
                        "(production releases are made by hand in Play Console)")


def run_check(track: str, key_path: str | None = None) -> int:
    check_track(track)
    edit = Edit(access_token(load_key(key_path)))
    edit.open()
    try:
        print(f"Access OK for {PACKAGE}. {track} track: {describe(edit.track(track))}.")
    finally:
        edit.discard()
    return 0


def run_upload(aab: Path, track: str, notes: str | None, key_path: str | None = None,
               changes_not_sent_for_review: bool = False) -> int:
    check_track(track)
    if aab.suffix != ".aab" or not aab.is_file():
        raise PlayError(f"{aab} is not an .aab file")
    edit = Edit(access_token(load_key(key_path)))
    edit.open()
    try:
        before = highest_version(edit.track(track))
        print(f"Uploading {aab.name} ({aab.stat().st_size / 1_048_576:.1f} MB) to {track}…", flush=True)
        version_code = edit.upload_bundle(aab)
        if version_code <= before:
            raise PlayError(f"versionCode {version_code} is not above {before}, already on {track}; "
                            "build from a newer commit")
        edit.set_release(track, version_code, notes)
        edit.commit(changes_not_sent_for_review)
        edit.id = None
    except BaseException:
        edit.discard()
        raise
    print(f"Done: versionCode {version_code} is live on the {track} track (status completed).")
    return 0


def run_assign(version_code: int, track: str, notes: str | None, key_path: str | None = None,
               changes_not_sent_for_review: bool = False) -> int:
    """Put a bundle Play already holds on a track, without uploading it again.

    Play keeps every uploaded bundle and refuses a second upload of the same
    versionCode, so moving a build from internal to closed testing is this,
    not a re-upload.
    """
    check_track(track)
    edit = Edit(access_token(load_key(key_path)))
    edit.open()
    try:
        before = highest_version(edit.track(track))
        if version_code <= before:
            raise PlayError(f"versionCode {version_code} is not above {before}, already on {track}")
        print(f"Releasing versionCode {version_code} to {track}…", flush=True)
        edit.set_release(track, version_code, notes)
        edit.commit(changes_not_sent_for_review)
        edit.id = None
    except BaseException:
        edit.discard()
        raise
    print(f"Done: versionCode {version_code} is live on the {track} track (status completed).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Upload an AAB to a Play testing track.")
    parser.add_argument("aab", nargs="?", type=Path, help="path to the signed .aab")
    parser.add_argument("--track", default="internal", help="internal (default) or alpha")
    parser.add_argument("--notes", help=f"release notes ({NOTES_LANGUAGE}), up to 500 characters")
    parser.add_argument("--key", help=f"service-account JSON (default ${KEY_ENV} or {DEFAULT_KEY})")
    parser.add_argument("--version-code", type=int,
                        help="release a bundle Play already holds (e.g. promote internal to alpha); no upload")
    parser.add_argument("--check", action="store_true", help="verify access and show the track; change nothing")
    parser.add_argument("--changes-not-sent-for-review", action="store_true",
                        help="commit without sending for review (only if Play asks for it)")
    args = parser.parse_args(argv)
    if args.notes and len(args.notes) > 500:
        parser.error("release notes are limited to 500 characters")
    try:
        if args.check:
            return run_check(args.track, args.key)
        if args.version_code is not None:
            if args.aab:
                parser.error("give either the .aab path or --version-code, not both")
            return run_assign(args.version_code, args.track, args.notes, args.key,
                              args.changes_not_sent_for_review)
        if not args.aab:
            parser.error("give the .aab path, --version-code, or --check")
        return run_upload(args.aab, args.track, args.notes, args.key, args.changes_not_sent_for_review)
    except PlayError as exc:
        print(f"play_upload: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
