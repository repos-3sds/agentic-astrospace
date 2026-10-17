"""Today's Subhashita: one verse a day from the Gita, Chanakya Niti and the Puranas.

The corpus (``subhashitas.json``) is curated, not generated. Every entry
carries its source and verse reference and the URL its Sanskrit was checked
against; the English is a short plain rendering written for this app. The
sources, method and what was left out (and why) are in
``docs/subhashita_corpus.md``; ``scripts/subhashita/build_corpus.py`` rebuilds it.

Everyone sees the same verse on the same date, so a verse shared to a
WhatsApp status is the one a friend opening the app sees too. The verse for
a date is fixed by its day count from ``EPOCH``, so the rotation needs no
state and every surface (API, push, widget) agrees without coordinating.
"""
from __future__ import annotations

import json
from datetime import date
from functools import lru_cache
from pathlib import Path

EPOCH = date(2026, 1, 1)
TITLE = "Today's Subhashita"

_CORPUS = Path(__file__).with_name("subhashitas.json")
_FIELDS = ("id", "source", "ref", "sanskrit", "english")


@lru_cache(maxsize=1)
def corpus() -> tuple[dict, ...]:
    rows = json.loads(_CORPUS.read_text(encoding="utf-8"))
    return tuple({field: row[field] for field in _FIELDS} for row in rows)


def for_day(day: date) -> dict:
    """The verse for a calendar date, with the date it is for."""
    rows = corpus()
    row = rows[(day - EPOCH).days % len(rows)]
    return {"date": day.isoformat(), **row}
