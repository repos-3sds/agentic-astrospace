"""Every Ask suggestion chip must route to a domain without a clarifying
question. A chip the app offers that answers "which area do you mean?" reads
as broken (regression finding H3, 2026-10-17)."""
import re
from pathlib import Path

from astrospace.agents.orchestrator import _needs_clarification
from astrospace.context.router import KeywordRouter

SUGGESTIONS = Path("ui/src/app/features/mobile/ask/ask-suggestions.ts")


def _prompts() -> list[str]:
    out = []
    for line in SUGGESTIONS.read_text().splitlines():
        if "prompt:" not in line:
            continue
        expr = line.split("prompt:", 1)[1].split(", because:")[0]
        for literal in re.findall(r"'([^']*)'|`([^`]*)`", expr):
            text = literal[0] or literal[1]
            out.append(re.sub(r"\$\{[^}]*\}", "Saturn", text))
    return out


def test_suggestions_are_found():
    assert len(_prompts()) >= 15


def test_every_suggestion_routes_without_clarification():
    router = KeywordRouter()
    unclear = [p for p in _prompts() if _needs_clarification(router.route(p))]
    assert not unclear, unclear
