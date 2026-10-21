"""Every table and column the server's models use exists after the migrations.

Run against a database built from scripts/ci/supabase_shim.sql,
docs/supabase_schema.sql and supabase/migrations/ in order (the CI
"Postgres migrations" job does this; audit I12). Production has failed twice
on a model column whose migration was never written or never applied (the
ask_messages token columns, the Subhashita table); the unit suite runs on
SQLite built from the models themselves, so it could not notice.

    DATABASE_URL=postgresql+psycopg://... python scripts/check_schema_drift.py

It also checks that every table in public has row-level security on: a
table without it is open to any signed-in client through PostgREST (the
2026-10-18 security audit, S2).

Exits 1 and lists the gaps. Extra columns in the database are fine: the
migrations may run ahead of the models.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, inspect, text  # noqa: E402

from astrospace.db import models  # noqa: E402,F401 (registers every table)
from astrospace.db.database import Base  # noqa: E402


def drift(url: str) -> list[str]:
    engine = create_engine(url)
    inspector = inspect(engine)
    gaps: list[str] = []
    for table in Base.metadata.sorted_tables:
        schema = table.schema or "public"
        if not inspector.has_table(table.name, schema=schema):
            gaps.append(f"table {schema}.{table.name} is missing")
            continue
        have = {column["name"] for column in inspector.get_columns(table.name, schema=schema)}
        gaps.extend(f"column {schema}.{table.name}.{column.name} is missing"
                    for column in table.columns if column.name not in have)
    with engine.connect() as conn:
        open_tables = conn.execute(text(
            "select c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace "
            "where n.nspname = 'public' and c.relkind = 'r' and not c.relrowsecurity order by 1"
        )).scalars().all()
    gaps.extend(f"table public.{name} has row-level security off" for name in open_tables)
    return gaps


def main() -> int:
    url = os.environ.get("DATABASE_URL", "")
    if not url.startswith("postgresql"):
        print("DATABASE_URL must point at the migrated Postgres database", file=sys.stderr)
        return 2
    gaps = drift(url)
    for gap in gaps:
        print(gap)
    print(f"{len(Base.metadata.tables)} model tables checked, {len(gaps)} gaps")
    return 1 if gaps else 0


if __name__ == "__main__":
    raise SystemExit(main())
