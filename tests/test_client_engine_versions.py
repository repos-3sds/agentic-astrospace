"""The native client's cache-compatibility constants must match the engines.

ui/src/app/core/vedic.service.ts refuses a cached Today or Calendar payload
whose engine/dataset version differs from the one it expects. When the server
constant moves and the client's does not, every cached read is treated as
incompatible and discarded, which silently turns the offline cache off. That
is what happened between #98 (daily-guidance-1.1) and 2026-10-15.
"""

import re
from pathlib import Path

from astrospace.context.daily import DAILY_GUIDANCE_ENGINE_VERSION
from astrospace.core.vedic.calendar import CALENDAR_DATASET_VERSION, CALENDAR_ENGINE_VERSION

CLIENT = Path(__file__).resolve().parent.parent / "ui" / "src" / "app" / "core" / "vedic.service.ts"


def _client_constant(name: str) -> str:
    match = re.search(rf"const {name} = '([^']+)';", CLIENT.read_text(encoding="utf-8"))
    assert match, f"{name} not found in {CLIENT}"
    return match.group(1)


def test_daily_guidance_engine_version_matches_client():
    assert _client_constant("DAILY_GUIDANCE_ENGINE_VERSION") == DAILY_GUIDANCE_ENGINE_VERSION


def test_calendar_versions_match_client():
    assert _client_constant("CALENDAR_ENGINE_VERSION") == CALENDAR_ENGINE_VERSION
    assert _client_constant("CALENDAR_DATASET_VERSION") == CALENDAR_DATASET_VERSION
