"""Today's Subhashita: one verse a day from the Gita, Chanakya Niti and the Puranas.

The corpus (``subhashitas.json``) is curated, not generated. Every entry
carries its source and verse reference and its provenance: the pre-1931
print edition (``editions.json``) its Sanskrit was keyed from, with a link
to the scanned page; the English is a short plain rendering written for this app, and the
meaning is one plain line on what the verse asks of the reader. The
sources, method and what was left out (and why) are in
``docs/subhashita_corpus.md``; ``scripts/subhashita/build_corpus.py`` rebuilds it.

Each account sees its own verse on a date (Hawk, 2026-10-19: "each account
should get random daily quotes not same"). The verse is fixed by the day
count from ``EPOCH`` plus an offset drawn from the account id, so the
rotation needs no state, every surface (API, push, widget) agrees without
coordinating, and each reader still walks the whole corpus before a verse
repeats, never the same source two days running. Signed out, the offset is
0. A shared status card carries its own verse, so friends need not match.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from functools import lru_cache
from pathlib import Path

EPOCH = date(2026, 1, 1)
TITLE = "Today's Subhashita"

_CORPUS = Path(__file__).with_name("subhashitas.json")
_FIELDS = ("id", "source", "ref", "sanskrit", "english", "meaning")


@lru_cache(maxsize=1)
def corpus() -> tuple[dict, ...]:
    rows = json.loads(_CORPUS.read_text(encoding="utf-8"))
    return tuple({field: row[field] for field in _FIELDS} for row in rows)


def offset_for(reader: str | None) -> int:
    """Where this reader's rotation starts: stable per account, 0 signed out."""
    if not reader:
        return 0
    return int(hashlib.sha256(reader.encode("utf-8")).hexdigest(), 16) % len(corpus())


def for_day(day: date, reader: str | None = None) -> dict:
    """The verse for a calendar date and reader, with the date it is for."""
    rows = corpus()
    row = rows[((day - EPOCH).days + offset_for(reader)) % len(rows)]
    return {"date": day.isoformat(), **row}
