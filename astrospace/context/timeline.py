"""One scannable, dated spine for a reading — the periods a reader is living
through, flattened and sorted.

Everything here already existed in the bundle before this module did; what did
not exist was a way to *scan* it. `dasha_relevance.chain` carries the current
nested chain, `retrospect` carries the current mahadasha's boundaries, and
`gochara.active_rules` carries transit windows — four overlapping dated ranges,
each in its own shape, in three different sections. A reader (and a model
narrating for one) cannot answer "where am I, and what turns next" from that
without re-deriving it in prose every single time, and prose is exactly where
dates get quietly rounded, merged, or invented.

So this is deterministic and server-computed, like every other bundle section:
one flat list, one date format, one age per boundary, one `status` per entry,
sorted. The agent narrates it; it never has to reconstruct it.

Scope is deliberately bounded to what a consultation actually references — the
previous, current and next mahadasha, the antardashas inside the current
mahadasha, and the currently-active transit windows for this domain's planets.
The full 120-year Vimshottari list is already available from `chart.dashas()`
for anything that genuinely needs it; putting it here would make the one thing
this module exists for (scannability) worse.
"""
from __future__ import annotations

from datetime import datetime, timezone

_TROPICAL_YEAR_DAYS = 365.2425


def as_dt(value) -> datetime | None:
    """Dasha boundaries arrive as datetimes or ISO strings depending on the
    caller; normalise so date/age arithmetic never depends on which."""
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def as_utc(value) -> datetime | None:
    moment = as_dt(value)
    if moment is None:
        return None
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def age_at(birth_utc: datetime, value) -> float | None:
    """Age in years at `value`, to one decimal.

    Ages travel with every boundary for the same reason `retrospect` carries
    them: people remember their lives by age, so "when you were 32" is
    checkable in a way "in late 2022" is not.
    """
    moment = as_utc(value)
    if moment is None:
        return None
    return round((moment - birth_utc).days / _TROPICAL_YEAR_DAYS, 1)


def _status(start, end, as_of_utc: datetime) -> str:
    start_utc, end_utc = as_utc(start), as_utc(end)
    if start_utc is not None and start_utc > as_of_utc:
        return "upcoming"
    if end_utc is not None and end_utc <= as_of_utc:
        return "past"
    return "current"


def _entry(kind: str, label: str, lord: str | None, start, end,
           birth_utc: datetime, as_of_utc: datetime, *,
           domain_relevant: bool = False, **extra) -> dict:
    return {
        "id": f"{kind}:{(lord or label)}:{str(start)[:10]}",
        "kind": kind,
        "label": label,
        "lord": lord,
        "start": str(start)[:10],
        "end": str(end)[:10],
        "age_at_start": age_at(birth_utc, start),
        "age_at_end": age_at(birth_utc, end),
        "status": _status(start, end, as_of_utc),
        "domain_relevant": domain_relevant,
        **extra,
    }


def build_timeline(chart, gochara: dict | None, as_of: datetime,
                   domain_lords: set[str] | None = None) -> dict:
    """The flat, sorted, dated spine. `domain_lords` is this domain's karakas
    plus its house lords — an entry ruled by one of them is flagged
    `domain_relevant`, so a wealth reading can tell at a glance which of the
    reader's periods actually speaks to money and which are simply the
    calendar they happen to be living in."""
    domain_lords = domain_lords or set()
    birth_utc = chart.moment.dt_utc
    as_of_utc = as_of.astimezone(timezone.utc)

    dashas = chart.dashas(as_of)
    mahadashas = dashas.get("mahadashas") or []
    current_index = next(
        (i for i, row in enumerate(mahadashas)
         if _status(row.get("start"), row.get("end"), as_of_utc) == "current"),
        None,
    )
    if current_index is None:
        return {
            "schema_version": "ce.timeline.v1",
            "available": False,
            "as_of": as_of_utc.isoformat(),
            "entries": [],
            "note": "No mahadasha covers this instant; timeline omitted.",
        }

    entries: list[dict] = []
    # Previous / current / next mahadasha. Slicing rather than indexing so the
    # first and last mahadasha in the list don't need their own special cases.
    for row in mahadashas[max(0, current_index - 1):current_index + 2]:
        lord = row.get("lord")
        entries.append(_entry(
            "mahadasha", f"{lord} mahadasha", lord,
            row.get("start"), row.get("end"), birth_utc, as_of_utc,
            domain_relevant=lord in domain_lords,
        ))

    current = mahadashas[current_index]
    current_lord = current.get("lord")
    for row in current.get("antardashas") or []:
        lord = row.get("lord")
        entries.append(_entry(
            "antardasha", f"{current_lord}–{lord} antardasha", lord,
            row.get("start"), row.get("end"), birth_utc, as_of_utc,
            domain_relevant=lord in domain_lords,
        ))

    # Transit windows are already scoped to this domain's `gochara_planets` by
    # the time they reach here (see assembler._gochara_for_domain), and every
    # rule in `active_rules` is by definition active right now — but their real
    # start/end dates are only present when the boundary walk found them, so
    # `_status` can legitimately have nothing to work with. Those keep the
    # "current" the active-rule list already asserts.
    for rule in (gochara or {}).get("active_rules") or []:
        entries.append(_entry(
            "gochara", rule.get("name") or "transit", rule.get("planet"),
            rule.get("start_date"), rule.get("end_date"), birth_utc, as_of_utc,
            domain_relevant=rule.get("planet") in domain_lords,
            rule_id=rule.get("rule_id"),
            severity=rule.get("severity"),
            source_status=rule.get("source_status"),
        ))

    entries.sort(key=lambda row: (row["start"], row["kind"], row["label"]))

    # "What turns next" is the other half of "where am I", and it is the part
    # a reader cannot get by scanning: it is the earliest END among the
    # periods currently running, not the earliest start in the list.
    ends = sorted(
        (row for row in entries if row["status"] == "current" and row["end"] != "None"),
        key=lambda row: row["end"],
    )
    return {
        "schema_version": "ce.timeline.v1",
        "available": True,
        "as_of": as_of_utc.isoformat(),
        "entries": entries,
        "current": [row["id"] for row in entries if row["status"] == "current"],
        "next_transition": (
            {"id": ends[0]["id"], "label": ends[0]["label"],
             "on": ends[0]["end"], "age": ends[0]["age_at_end"]}
            if ends else None
        ),
        "note": (
            "Dated period boundaries only, sorted. Like `retrospect`, this says "
            "WHEN the reader's periods turn and how old they are at each — never "
            "what happened to them in one."
        ),
    }
