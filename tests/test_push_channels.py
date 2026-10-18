"""Android notification channels per category (nativeness audit N12)."""

from astrospace.notifications.push import ANDROID_CHANNEL_ID, android_channel


def test_window_alerts_have_their_own_channel():
    assert android_channel("window_alert") == "siddha_windows"


def test_everything_else_keeps_the_bell_channel():
    # siddha_bell is the manifest default, so older builds still get the bell.
    for category in ("morning_brief", "daily_subhashita", None, "unknown"):
        assert android_channel(category) == ANDROID_CHANNEL_ID == "siddha_bell"


def test_channel_ids_match_the_app():
    from pathlib import Path

    java = Path("ui/android/app/src/main/java/app/asksiddha/mobile/MainActivity.java").read_text()
    assert '"siddha_windows"' in java and '"siddha_bell"' in java
