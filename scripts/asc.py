"""App Store Connect API calls for the iOS half of the Ship workflow.

GitHub Actions builds the iOS app on every green merge to main and uploads it
to TestFlight (.github/workflows/ship.yml, docs/ship_ios_testflight.md). This
script does the parts that need Apple's API, with the standard library and the
`openssl` binary only, so it runs on a fresh macOS runner or the Mac with
nothing to install:

    python3 scripts/asc.py check                       # key works, app is visible
    python3 scripts/asc.py latest-build                # highest build number Apple holds
    python3 scripts/asc.py profile --serial 1A2B... --out ci.mobileprovision
    python3 scripts/asc.py create-cert --out-dir DIR   # one-time setup, Mac only

The API key comes from $ASC_KEY_ID, $ASC_ISSUER_ID and either $ASC_KEY_FILE
(path to the AuthKey_XXXX.p8) or $ASC_KEY_P8 (its contents). None of it is
ever printed.

What it deliberately cannot do: submit for review, release to the App Store,
add testers, or touch the external TestFlight group. Uploading a build makes it
appear in TestFlight; the internal group gets it automatically, and anything
past that stays a person's decision in App Store Connect.
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

APP_ID = "6827191709"            # "Siddha: Astrology | Life Guide"
BUNDLE_ID = "app.asksiddha.mobile"
API = "https://api.appstoreconnect.apple.com/v1"
PROFILE_PREFIX = "Siddha CI App Store"


class AscError(RuntimeError):
    pass


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def der_to_raw_signature(der: bytes, size: int = 32) -> bytes:
    """openssl writes ECDSA signatures as DER (SEQUENCE of two INTEGERs); a JWT
    wants the two numbers back to back, each padded to the curve size."""
    def read_len(buf: bytes, i: int) -> tuple[int, int]:
        n = buf[i]
        if n < 0x80:
            return n, i + 1
        count = n & 0x7F
        return int.from_bytes(buf[i + 1:i + 1 + count], "big"), i + 1 + count

    if not der or der[0] != 0x30:
        raise AscError("unexpected signature format from openssl")
    _, i = read_len(der, 1)
    parts = []
    for _ in range(2):
        if der[i] != 0x02:
            raise AscError("unexpected signature format from openssl")
        length, i = read_len(der, i + 1)
        value = der[i:i + length].lstrip(b"\x00")
        if len(value) > size:
            raise AscError("signature integer longer than the curve")
        parts.append(value.rjust(size, b"\x00"))
        i += length
    return parts[0] + parts[1]


def _key_pem() -> str:
    path = os.environ.get("ASC_KEY_FILE", "").strip()
    if path:
        key_path = Path(os.path.expanduser(path))
        if not key_path.is_file():
            raise AscError(f"ASC_KEY_FILE points at {key_path}, which does not exist")
        return key_path.read_text(encoding="utf-8")
    pem = os.environ.get("ASC_KEY_P8", "").strip()
    if not pem:
        raise AscError("set ASC_KEY_FILE (path to AuthKey_XXXX.p8) or ASC_KEY_P8")
    return pem + "\n"


def sign_es256(message: bytes, pem: str) -> bytes:
    fd, pem_path = tempfile.mkstemp(prefix="asc-key-", suffix=".p8")
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(pem)
        proc = subprocess.run(["openssl", "dgst", "-sha256", "-sign", pem_path],
                              input=message, capture_output=True, check=False)
    finally:
        os.unlink(pem_path)
    if proc.returncode != 0 or not proc.stdout:
        raise AscError("openssl could not sign the App Store Connect token (is the .p8 intact?)")
    return der_to_raw_signature(proc.stdout)


def build_token(key_id: str, issuer_id: str, pem: str, now: int | None = None) -> str:
    now = int(time.time()) if now is None else now
    header = {"alg": "ES256", "kid": key_id, "typ": "JWT"}
    # Apple refuses tokens that live longer than 20 minutes.
    claims = {"iss": issuer_id, "iat": now, "exp": now + 1140, "aud": "appstoreconnect-v1"}
    signing_input = f"{_b64url(json.dumps(header).encode())}.{_b64url(json.dumps(claims).encode())}"
    return f"{signing_input}.{_b64url(sign_es256(signing_input.encode('ascii'), pem))}"


def token_from_env() -> str:
    key_id = os.environ.get("ASC_KEY_ID", "").strip()
    issuer = os.environ.get("ASC_ISSUER_ID", "").strip()
    if not key_id or not issuer:
        raise AscError("set ASC_KEY_ID and ASC_ISSUER_ID")
    return build_token(key_id, issuer, _key_pem())


def _request(method: str, path: str, token: str, body: dict | None = None) -> dict:
    url = path if path.startswith("https://") else f"{API}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        try:
            errors = json.loads(detail)["errors"]
            detail = "; ".join(f"{e.get('title', '')}: {e.get('detail', '')}" for e in errors)
        except (ValueError, KeyError, TypeError):
            detail = detail[:500]
        raise AscError(f"{method} {url.split('?')[0]} failed ({exc.code}): {detail}") from None
    except urllib.error.URLError as exc:
        raise AscError(f"{method} {url.split('?')[0]} failed: {exc.reason}") from None
    return json.loads(raw) if raw else {}


def _get(path: str, token: str, **query: str) -> dict:
    return _request("GET", f"{path}?{urllib.parse.urlencode(query)}" if query else path, token)


# --- builds -----------------------------------------------------------------

def highest_build(builds: list[dict]) -> int:
    best = 0
    for build in builds:
        try:
            best = max(best, int(str(build["attributes"]["version"]).strip()))
        except (KeyError, TypeError, ValueError):
            continue  # a non-numeric build number was never ours
    return best


def latest_build(token: str, app_id: str = APP_ID) -> int:
    data = _get("/builds", token, **{"filter[app]": app_id, "sort": "-uploadedDate",
                                     "limit": "100", "fields[builds]": "version"})
    return highest_build(data.get("data", []))


# --- signing ----------------------------------------------------------------

def _norm_serial(serial: str) -> str:
    return serial.strip().upper().removeprefix("SERIAL=").lstrip("0")


def find_certificate(token: str, serial: str) -> dict:
    want = _norm_serial(serial)
    data = _get("/certificates", token, **{"filter[certificateType]": "DISTRIBUTION,IOS_DISTRIBUTION",
                                           "limit": "200"})
    for cert in data.get("data", []):
        if _norm_serial(cert["attributes"].get("serialNumber", "")) == want:
            return cert
    raise AscError(f"no distribution certificate with serial {serial} on the team "
                   "(revoked? re-run scripts/ci/setup_ios_ship.sh)")


def find_bundle_id(token: str, identifier: str = BUNDLE_ID) -> dict:
    data = _get("/bundleIds", token, **{"filter[identifier]": identifier, "limit": "50"})
    for bundle in data.get("data", []):
        if bundle["attributes"].get("identifier") == identifier:
            return bundle
    raise AscError(f"App ID {identifier} not found on the team")


def pick_profile(profiles: list[dict], bundle_pk: str, cert_pk: str) -> dict | None:
    """An active App Store profile for this App ID that carries this
    certificate. A profile goes INVALID when the App ID's capabilities change,
    which is why one is looked up (or made) on every run, not stored."""
    for profile in profiles:
        attrs = profile.get("attributes", {})
        rel = profile.get("relationships", {})
        if attrs.get("profileType") != "IOS_APP_STORE" or attrs.get("profileState") != "ACTIVE":
            continue
        if (rel.get("bundleId", {}).get("data") or {}).get("id") != bundle_pk:
            continue
        if any(c.get("id") == cert_pk for c in rel.get("certificates", {}).get("data") or []):
            return profile
    return None


def ensure_profile(token: str, serial: str) -> dict:
    cert = find_certificate(token, serial)
    bundle = find_bundle_id(token)
    data = _get("/profiles", token, **{"filter[profileType]": "IOS_APP_STORE",
                                       "filter[profileState]": "ACTIVE",
                                       "include": "bundleId,certificates",
                                       "limit[certificates]": "50", "limit": "200"})
    profile = pick_profile(data.get("data", []), bundle["id"], cert["id"])
    if profile:
        return profile
    body = {"data": {
        "type": "profiles",
        "attributes": {"name": f"{PROFILE_PREFIX} {time.strftime('%Y-%m-%d %H%M', time.gmtime())}",
                       "profileType": "IOS_APP_STORE"},
        "relationships": {
            "bundleId": {"data": {"type": "bundleIds", "id": bundle["id"]}},
            "certificates": {"data": [{"type": "certificates", "id": cert["id"]}]},
        },
    }}
    return _request("POST", "/profiles", token, body)["data"]


def create_certificate(token: str, out_dir: Path, p12_password: str) -> str:
    """Make a new Apple Distribution certificate whose private key exists only
    in out_dir, and bundle both as distribution.p12. Returns the serial."""
    out_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(out_dir, 0o700)
    key, csr = out_dir / "distribution.key", out_dir / "distribution.csr"
    cer, pem, p12 = out_dir / "distribution.cer", out_dir / "distribution.pem", out_dir / "distribution.p12"
    run = lambda *args: subprocess.run(args, check=True, capture_output=True)  # noqa: E731
    run("openssl", "genrsa", "-out", str(key), "2048")
    os.chmod(key, 0o600)
    run("openssl", "req", "-new", "-key", str(key), "-out", str(csr),
        "-subj", "/CN=Siddha CI/O=Siddha/C=IN")
    body = {"data": {"type": "certificates", "attributes": {
        "certificateType": "DISTRIBUTION", "csrContent": csr.read_text()}}}
    data = _request("POST", "/certificates", token, body)["data"]
    cer.write_bytes(base64.b64decode(data["attributes"]["certificateContent"]))
    run("openssl", "x509", "-inform", "DER", "-in", str(cer), "-out", str(pem))
    # macOS Keychain cannot read OpenSSL 3's default p12 ciphers; -legacy keeps
    # it importable. LibreSSL (/usr/bin/openssl on a Mac) has no such flag and
    # already writes the old format.
    base = ["openssl", "pkcs12", "-export", "-inkey", str(key), "-in", str(pem),
            "-out", str(p12), "-name", "Siddha CI distribution", "-passout", "env:ASC_P12_PASSWORD"]
    env = {**os.environ, "ASC_P12_PASSWORD": p12_password}
    proc = subprocess.run([*base, "-legacy"], capture_output=True, env=env, check=False)
    if proc.returncode != 0:
        subprocess.run(base, capture_output=True, env=env, check=True)
    os.chmod(p12, 0o600)
    return data["attributes"]["serialNumber"]


# --- cli --------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check", help="the key works and the app is visible")
    sub.add_parser("latest-build", help="highest build number App Store Connect holds")
    prof = sub.add_parser("profile", help="find or create the App Store profile for the CI certificate")
    prof.add_argument("--serial", required=True, help="serial number of the distribution certificate")
    prof.add_argument("--out", required=True, type=Path, help="where to write the .mobileprovision")
    cert = sub.add_parser("create-cert", help="one-time: new distribution certificate + p12")
    cert.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        token = token_from_env()
        if args.cmd == "check":
            app = _get(f"/apps/{APP_ID}", token)["data"]["attributes"]
            print(f"OK: {app.get('name')} ({app.get('bundleId')}), latest build {latest_build(token)}")
        elif args.cmd == "latest-build":
            print(latest_build(token))
        elif args.cmd == "profile":
            profile = ensure_profile(token, args.serial)
            attrs = profile["attributes"]
            args.out.write_bytes(base64.b64decode(attrs["profileContent"]))
            print(f"name={attrs['name']}")
            print(f"uuid={attrs['uuid']}")
        elif args.cmd == "create-cert":
            password = os.environ.get("ASC_P12_PASSWORD", "")
            if not password:
                raise AscError("set ASC_P12_PASSWORD for the new p12")
            print(f"serial={create_certificate(token, args.out_dir, password)}")
    except AscError as exc:
        print(f"asc: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
