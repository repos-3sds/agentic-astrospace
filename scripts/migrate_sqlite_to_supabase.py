#!/usr/bin/env python3
"""Copy local AstroSpace SQLite data into Supabase/Postgres.

Usage:
  python scripts/migrate_sqlite_to_supabase.py \
    --sqlite sqlite:////absolute/path/astrospace.db \
    --postgres postgresql+psycopg://...

The script is idempotent at the row level: existing primary keys are updated.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine


TABLES = {
    "kundlis": [
        "id", "user_id", "name", "relation", "birth_year", "birth_month", "birth_day",
        "birth_hour", "birth_minute", "birth_city", "birth_nation", "sun_sign",
        "moon_sign", "ascendant", "chart_data", "notes", "created_at", "updated_at",
    ],
    "readings": [
        "id", "kundli_id", "reading_type", "period_label", "generated_local_date",
        "version", "parent_reading_id", "deviation_score", "deviation_summary",
        "user_rating", "user_feedback", "reviewed_at", "content", "generated_at",
    ],
    "prediction_claims": [
        "id", "kundli_id", "reading_id", "user_id", "reading_type", "period_label",
        "generated_local_date", "target_start_date", "target_end_date", "category",
        "claim_text", "confidence", "source_excerpt", "status", "user_feedback",
        "reviewed_at", "created_at",
    ],
}

JSON_COLUMNS = {
    "kundlis": {"chart_data"},
    "readings": {"deviation_summary"},
}


def normalize_postgres_url(url: str) -> str:
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def execute_schema(engine: Engine, schema_path: Path) -> None:
    sql = schema_path.read_text()
    with engine.begin() as conn:
        conn.execute(text(sql))


def table_columns(engine: Engine, table: str) -> set[str]:
    inspector = inspect(engine)
    schema = "public" if engine.dialect.name == "postgresql" else None
    if table not in inspector.get_table_names(schema=schema):
        return set()
    return {col["name"] for col in inspector.get_columns(table, schema=schema)}


def fetch_rows(sqlite: Engine, table: str, columns: list[str]) -> list[dict[str, Any]]:
    existing = table_columns(sqlite, table)
    if not existing:
        return []
    selected = [column for column in columns if column in existing]
    if not selected:
        return []
    query = text(f"select {', '.join(selected)} from {table}")
    with sqlite.connect() as conn:
        rows = [dict(row._mapping) for row in conn.execute(query)]
    for row in rows:
        for column in JSON_COLUMNS.get(table, set()):
            value = row.get(column)
            if isinstance(value, str) and value:
                try:
                    row[column] = json.loads(value)
                except json.JSONDecodeError:
                    pass
    return rows


def upsert_rows(postgres: Engine, table: str, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    columns = list(rows[0])
    assignments = [column for column in columns if column != "id"]
    json_columns = JSON_COLUMNS.get(table, set())
    values = [
        f"cast(:{column} as jsonb)" if column in json_columns else f":{column}"
        for column in columns
    ]
    normalized_rows: list[dict[str, Any]] = []
    for row in rows:
        normalized = dict(row)
        for column in json_columns:
            value = normalized.get(column)
            if isinstance(value, (dict, list)):
                normalized[column] = json.dumps(value)
        normalized_rows.append(normalized)
    insert_sql = f"""
        insert into public.{table} ({', '.join(columns)})
        values ({', '.join(values)})
        on conflict (id) do update set
        {', '.join(f'{column} = excluded.{column}' for column in assignments)}
    """
    with postgres.begin() as conn:
        conn.execute(text(insert_sql), normalized_rows)
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sqlite", default="sqlite:///./astrospace.db")
    parser.add_argument("--postgres", required=True, help="Supabase Postgres SQLAlchemy URL")
    parser.add_argument("--schema", default="docs/supabase_schema.sql")
    parser.add_argument("--skip-schema", action="store_true")
    args = parser.parse_args()

    sqlite = create_engine(args.sqlite)
    postgres = create_engine(normalize_postgres_url(args.postgres))

    if not args.skip_schema:
        execute_schema(postgres, Path(args.schema))

    totals: dict[str, int] = {}
    for table, columns in TABLES.items():
        rows = fetch_rows(sqlite, table, columns)
        totals[table] = upsert_rows(postgres, table, rows)

    print("Migration complete")
    for table, count in totals.items():
        print(f"{table}: {count}")


if __name__ == "__main__":
    main()
