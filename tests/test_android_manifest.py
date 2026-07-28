"""Android backup must stay disabled.

Supabase's session — including the refresh token — lives in the WebView's
localStorage with no override to Keystore-backed storage (see
ui/src/app/core/auth.service.ts, which passes no `storage` option to
createClient). Android Auto Backup copies that directory to the user's
Google account, unencrypted, by default whenever `android:allowBackup` is
true — turning a lost or shared Google account into a stolen session with no
password or MFA challenge. There is no dataExtractionRules/fullBackupContent
carve-out for the WebView storage, so `allowBackup="false"` is the whole
mitigation; anyone who re-enables it needs to replace it with an equivalent
exclusion, not just delete the check below.
"""
import xml.etree.ElementTree as ET
from pathlib import Path

ANDROID_NS = "{http://schemas.android.com/apk/res/android}"
MANIFEST = (
    Path(__file__).resolve().parent.parent
    / "ui" / "android" / "app" / "src" / "main" / "AndroidManifest.xml"
)


def test_allow_backup_is_disabled():
    tree = ET.parse(MANIFEST)
    application = tree.getroot().find("application")
    assert application is not None, "no <application> element in AndroidManifest.xml"

    allow_backup = application.get(f"{ANDROID_NS}allowBackup")

    assert allow_backup == "false", (
        "android:allowBackup must stay \"false\" until the Supabase session "
        "is moved off WebView localStorage onto Keystore-backed storage — "
        "see the module docstring."
    )
