"""Every email button opens a screen the phone app will route to.

The app claims all of asksiddha.app/m/ (AndroidManifest.xml), but only
navigates to paths in APP_LINK_ROUTES (ui/src/app/core/app-links.service.ts).
A button to any other path opened Siddha and went nowhere (sweep 2026-10-29
F-4). This reads both sides, so a new email path fails here first.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_LINKS = ROOT / "ui/src/app/core/app-links.service.ts"
EMAIL_SOURCES = [
    ROOT / "astrospace/notifications/email.py",
    ROOT / "astrospace/notifications/email_jobs.py",
    ROOT / "astrospace/notifications/email_series.py",
    ROOT / "astrospace/notifications/clock_change.py",
    ROOT / "astrospace/notifications/release_announcements.py",
]


def _allowed() -> set[str]:
    block = re.search(r"APP_LINK_ROUTES = new Set\(\[(.*?)\]\)", APP_LINKS.read_text(), re.S)
    assert block, "APP_LINK_ROUTES not found"
    return set(re.findall(r"'(/m/[^']*)'", block.group(1)))


def _email_paths() -> set[str]:
    found: set[str] = set()
    for source in EMAIL_SOURCES:
        text = source.read_text()
        for match in re.finditer(r"""(?:button_path\s*=|"path"\s*:|path\s*=|path, button\s*=)\s*f?["'](/m/[^"'?{]*)""", text):
            found.add(match.group(1).rstrip("/"))
    return found


def test_every_email_button_path_is_an_app_link():
    paths = _email_paths()
    assert {"/m/today", "/m/calendar", "/m/chart/periods"} <= paths, paths
    missing = sorted(paths - _allowed())
    assert not missing, f"add these to APP_LINK_ROUTES or change the email: {missing}"


def test_festival_email_opens_the_festival_day():
    from datetime import date
    from astrospace.notifications.email_jobs import festival_content

    content = festival_content(date(2026, 11, 8),
                               {"moon": None, "festivals": [{"name": "Diwali", "slug": "diwali"}]},
                               "Vijayawada")
    assert content.button_path == "/m/calendar/day?date=2026-11-08"
