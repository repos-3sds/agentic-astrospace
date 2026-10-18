"""Android App Links for asksiddha.app (nativeness audit N17)."""

import json
import re
from pathlib import Path

ASSETLINKS = Path("firebase-public/.well-known/assetlinks.json")
FINGERPRINT = re.compile(r"^([0-9A-F]{2}:){31}[0-9A-F]{2}$")


def test_manifest_claims_the_m_paths_with_verification():
    manifest = Path("ui/android/app/src/main/AndroidManifest.xml").read_text()
    assert 'android:autoVerify="true"' in manifest
    assert 'android:host="asksiddha.app" android:pathPrefix="/m/"' in manifest


def test_hosting_does_not_drop_the_well_known_folder():
    hosting = json.loads(Path("firebase.json").read_text())["hosting"]
    assert "**/.*" not in hosting["ignore"]


def test_assetlinks_names_the_app_and_real_fingerprints():
    if not ASSETLINKS.exists():
        return  # added once the Play signing fingerprints are known
    statements = json.loads(ASSETLINKS.read_text())
    assert statements, "assetlinks.json is empty"
    for statement in statements:
        assert statement["relation"] == ["delegate_permission/common.handle_all_urls"]
        target = statement["target"]
        assert target["namespace"] == "android_app"
        assert target["package_name"] == "app.asksiddha.mobile"
        assert target["sha256_cert_fingerprints"]
        for fp in target["sha256_cert_fingerprints"]:
            assert FINGERPRINT.match(fp), fp
