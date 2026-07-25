"""Seed the catalog tables from the engines.

The engines are the source of truth. `remedies.catalog()`, `festivals.catalog()`
and `muhurta.goal_catalog()` already emit rows shaped for their tables, so this
module only has to persist them — nothing is authored here, which is what keeps
the database and the engines from drifting apart.

Everything is an upsert keyed on the table's unique constraint, so re-running
after an engine change updates rows in place rather than duplicating them. That
matters: festival rules get corrected, and `user_observances` points at
`festivals.id`, so those ids have to survive a re-seed.

Usage::

    python -m astrospace.db.seed                       # catalogs only
    python -m astrospace.db.seed --city Chennai --years 2026 2027

Occurrences are not seeded by default because computing a year walks ~400 days
of panchanga per place; ask for them explicitly.
"""
from __future__ import annotations

import argparse
from typing import Iterable

from sqlalchemy.orm import Session

from ..core.vedic import festivals as festival_engine
from ..core.vedic import muhurta as muhurta_engine
from ..core.vedic import remedies as remedy_engine
from .models import Festival, FestivalOccurrence, MuhurtaGoal, Remedy

DEFAULT_PLACES = [("Chennai", "IN"), ("New Delhi", "IN")]


def place_key(city: str, nation: str) -> str:
    """Stable key for a place. Festival dates depend on it, so it is part of
    the occurrence's identity rather than an afterthought."""
    return f"{nation}/{city}"


def _upsert(db: Session, model, key: dict, values: dict) -> str:
    """Insert or update by unique key. Returns "inserted" or "updated"."""
    row = db.query(model).filter_by(**key).first()
    if row is None:
        db.add(model(**key, **values))
        return "inserted"
    changed = False
    for field, value in values.items():
        if getattr(row, field) != value:
            setattr(row, field, value)
            changed = True
    return "updated" if changed else "unchanged"


def _tally(results: Iterable[str]) -> dict[str, int]:
    counts = {"inserted": 0, "updated": 0, "unchanged": 0}
    for result in results:
        counts[result] += 1
    return counts


# ── Catalogs ─────────────────────────────────────────────────────────────────

def seed_remedies(db: Session) -> dict[str, int]:
    results = [
        _upsert(db, Remedy, {"slug": row["slug"]},
                {k: v for k, v in row.items() if k != "slug"})
        for row in remedy_engine.catalog()
    ]
    db.commit()
    return _tally(results)


def seed_festivals(db: Session) -> dict[str, int]:
    results = [
        _upsert(db, Festival, {"slug": row["slug"]},
                {k: v for k, v in row.items() if k != "slug"})
        for row in festival_engine.catalog()
    ]
    db.commit()
    return _tally(results)


def seed_muhurta_goals(db: Session) -> dict[str, int]:
    results = [
        _upsert(db, MuhurtaGoal, {"slug": row["slug"]},
                {k: v for k, v in row.items() if k != "slug"})
        for row in muhurta_engine.goal_catalog()
    ]
    db.commit()
    return _tally(results)


# ── Occurrences ──────────────────────────────────────────────────────────────

def seed_festival_occurrences(db: Session, city: str, nation: str,
                              years: Iterable[int]) -> dict[str, int]:
    """Resolve and store festival dates for a place.

    Requires `seed_festivals` to have run — occurrences reference `festivals.id`,
    and a slug with no row is skipped rather than silently inventing a festival.
    """
    key = place_key(city, nation)
    ids = {row.slug: row.id for row in db.query(Festival.slug, Festival.id).all()}
    if not ids:
        raise RuntimeError(
            "No festivals in the database — run seed_festivals() first."
        )

    results: list[str] = []
    for year in years:
        for row in festival_engine.occurrences(year, city=city, nation=nation):
            festival_id = ids.get(row["slug"])
            if festival_id is None:
                continue
            results.append(_upsert(
                db, FestivalOccurrence,
                {"festival_id": festival_id, "occurs_on": row["occurs_on"],
                 "place_key": key},
                {"computed_meta": {
                    "rule": row["rule"],
                    # Carried into the row so a client reading from the table
                    # gets the same caveat as one calling the engine directly.
                    "observance_note": row["observance_note"],
                    "is_convention_dependent": row["is_convention_dependent"],
                    "place": row["place"],
                }},
            ))
        db.commit()
    return _tally(results)


# ── Entry point ──────────────────────────────────────────────────────────────

def seed_all(db: Session, *, places: list[tuple[str, str]] | None = None,
             years: Iterable[int] | None = None) -> dict[str, dict]:
    report = {
        "remedies": seed_remedies(db),
        "festivals": seed_festivals(db),
        "muhurta_goals": seed_muhurta_goals(db),
    }
    if years:
        for city, nation in (places or DEFAULT_PLACES):
            report[f"occurrences[{place_key(city, nation)}]"] = (
                seed_festival_occurrences(db, city, nation, years)
            )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--city", action="append", default=None,
                        help="City for festival occurrences; repeatable.")
    parser.add_argument("--nation", default="IN")
    parser.add_argument("--years", type=int, nargs="*", default=None,
                        help="Years to resolve occurrences for.")
    args = parser.parse_args()

    from .database import SessionLocal, init_db

    init_db()
    places = [(city, args.nation) for city in args.city] if args.city else None
    db = SessionLocal()
    try:
        report = seed_all(db, places=places, years=args.years)
    finally:
        db.close()

    for table, counts in report.items():
        print(f"{table:<32} " + "  ".join(f"{k}={v}" for k, v in counts.items()))


if __name__ == "__main__":
    main()
