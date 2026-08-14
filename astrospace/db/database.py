import os
from sqlalchemy import inspect, text
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

def _database_url() -> str:
    """Return the SQLAlchemy database URL.

    DATABASE_URL remains the primary app setting. SUPABASE_DB_URL is accepted as
    a clearer alias for cloud deployments. Plain postgres:// and postgresql://
    URLs are normalized to the psycopg SQLAlchemy driver.
    """
    url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    # Local-dev fallback only: SQLite in the working directory. Cloud Run's
    # filesystem is ephemeral — production must set DATABASE_URL to Postgres.
    url = url or "sqlite:///./astrospace.db"
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


DATABASE_URL = _database_url()

# SQLite needs check_same_thread=False. Supabase's transaction pooler is not
# compatible with psycopg's server-side prepared statements across pooled
# connections, so disable them for deployed Postgres connections.
connect_args = (
    {"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {"prepare_threshold": None}
)

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def init_db():
    # Importing the module registers every model on Base.metadata; the explicit
    # names keep the original four discoverable at a glance.
    from . import models  # noqa: F401
    from .models import Kundli, PredictionClaim, Reading, UserSettings  # noqa: F401
    # create_all uses checkfirst=True, so tables already created by the Supabase
    # migrations are left untouched — this only fills gaps (e.g. local SQLite).
    Base.metadata.create_all(bind=engine)
    _migrate_sqlite_kundlis()
    _migrate_sqlite_readings()
    _migrate_sqlite_prediction_claims()
    _migrate_sqlite_user_settings()


def _migrate_sqlite_kundlis():
    if not DATABASE_URL.startswith("sqlite"):
        return
    inspector = inspect(engine)
    if "kundlis" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("kundlis")}
    # Mirrors the ALTERs in 20260725120000_create_mobile_app_schema.sql, so a
    # local SQLite database created before that migration keeps working.
    additions = {
        "birth_latitude": "FLOAT",
        "birth_longitude": "FLOAT",
        "birth_timezone": "VARCHAR",
        "birth_state": "VARCHAR",
        "birth_time_accuracy": "VARCHAR DEFAULT 'exact'",
        "kind": "VARCHAR DEFAULT 'profile'",
        "archived_at": "DATETIME",
    }
    with engine.begin() as conn:
        if "user_id" not in existing:
            conn.execute(text("ALTER TABLE kundlis ADD COLUMN user_id VARCHAR DEFAULT 'local-dev-user'"))
        for column, ddl in additions.items():
            if column not in existing:
                conn.execute(text(f"ALTER TABLE kundlis ADD COLUMN {column} {ddl}"))
        conn.execute(text("""
            UPDATE kundlis
            SET user_id = 'local-dev-user'
            WHERE user_id IS NULL OR user_id = ''
        """))
        conn.execute(text("UPDATE kundlis SET kind = 'profile' WHERE kind IS NULL"))
        conn.execute(text(
            "UPDATE kundlis SET birth_time_accuracy = 'exact' WHERE birth_time_accuracy IS NULL"
        ))


def _migrate_sqlite_user_settings():
    """Additive columns for experience mode / tone on local SQLite."""
    if not DATABASE_URL.startswith("sqlite"):
        return
    inspector = inspect(engine)
    if "user_settings" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("user_settings")}
    additions = {
        "experience_mode": "VARCHAR DEFAULT 'balanced'",
        "tone": "VARCHAR DEFAULT 'gentle'",
        "memory_enabled": "BOOLEAN DEFAULT 1",
        "memory_mode": "VARCHAR DEFAULT 'ask'",
        "large_tap_mode": "BOOLEAN DEFAULT 0",
        "audio_enabled": "BOOLEAN DEFAULT 1",
        "reduce_motion": "BOOLEAN DEFAULT 0",
        "onboarding_completed_at": "DATETIME",
    }
    with engine.begin() as conn:
        for column, ddl in additions.items():
            if column not in existing:
                conn.execute(text(f"ALTER TABLE user_settings ADD COLUMN {column} {ddl}"))
        conn.execute(text(
            "UPDATE user_settings SET experience_mode = 'balanced' WHERE experience_mode IS NULL"
        ))
        conn.execute(text("UPDATE user_settings SET tone = 'gentle' WHERE tone IS NULL"))
        conn.execute(text("UPDATE user_settings SET memory_enabled = 1 WHERE memory_enabled IS NULL"))
        conn.execute(text("UPDATE user_settings SET memory_mode = 'ask' WHERE memory_mode IS NULL"))


def _migrate_sqlite_readings():
    """Small additive migration path for local SQLite during active development."""
    if not DATABASE_URL.startswith("sqlite"):
        return
    inspector = inspect(engine)
    if "readings" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("readings")}
    additions = {
        "language": "VARCHAR DEFAULT 'en'",
        "generated_local_date": "VARCHAR",
        "version": "INTEGER DEFAULT 1",
        "parent_reading_id": "VARCHAR",
        "deviation_score": "FLOAT",
        "deviation_summary": "JSON",
        "user_rating": "INTEGER",
        "user_feedback": "TEXT",
        "reviewed_at": "DATETIME",
    }
    with engine.begin() as conn:
        for column, ddl in additions.items():
            if column not in existing:
                conn.execute(text(f"ALTER TABLE readings ADD COLUMN {column} {ddl}"))
        conn.execute(text("UPDATE readings SET version = 1 WHERE version IS NULL"))
        conn.execute(text("""
            UPDATE readings
            SET generated_local_date = CASE
                WHEN reading_type = 'daily'
                     AND period_label GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
                THEN period_label
                ELSE substr(generated_at, 1, 10)
            END
            WHERE generated_local_date IS NULL
        """))


def _migrate_sqlite_prediction_claims():
    """Backfill additive indexes/columns for local SQLite prediction storage."""
    if not DATABASE_URL.startswith("sqlite"):
        return
    inspector = inspect(engine)
    if "prediction_claims" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("prediction_claims")}
    additions = {
        "user_id": "VARCHAR DEFAULT 'local-dev-user'",
        "reading_type": "VARCHAR DEFAULT 'daily'",
        "period_label": "VARCHAR",
        "generated_local_date": "VARCHAR",
        "target_start_date": "VARCHAR",
        "target_end_date": "VARCHAR",
        "category": "VARCHAR DEFAULT 'general'",
        "confidence": "FLOAT",
        "source_excerpt": "TEXT",
        "status": "VARCHAR DEFAULT 'pending'",
        "user_feedback": "TEXT",
        "reviewed_at": "DATETIME",
        "created_at": "DATETIME",
    }
    with engine.begin() as conn:
        for column, ddl in additions.items():
            if column not in existing:
                conn.execute(text(f"ALTER TABLE prediction_claims ADD COLUMN {column} {ddl}"))
        conn.execute(text("""
            UPDATE prediction_claims
            SET status = 'pending'
            WHERE status IS NULL OR status = ''
        """))
        conn.execute(text("""
            UPDATE prediction_claims
            SET user_id = 'local-dev-user'
            WHERE user_id IS NULL OR user_id = ''
        """))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
