import os
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import inspect, text
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker, DeclarativeBase
from ..config import integer


def _database_url() -> str:
    """Return the SQLAlchemy database URL.

    DATABASE_URL remains the primary app setting. SUPABASE_DB_URL is accepted as
    a clearer alias for cloud deployments. Plain postgres:// and postgresql://
    URLs are normalized to the psycopg SQLAlchemy driver.
    """
    url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not url and (os.getenv("K_SERVICE") or os.getenv("CLOUD_RUN_JOB")):
        # Cloud Run's disk is wiped when an instance recycles. Booting on
        # SQLite there would take sign-ups and lose them, so refuse to start.
        raise RuntimeError("DATABASE_URL (or SUPABASE_DB_URL) must be set on Cloud Run")
    # Local-dev fallback only: SQLite in the working directory.
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
def engine_options(url: str) -> dict:
    """Pool settings per backend.

    SQLite keeps SQLAlchemy's defaults. Postgres sits behind Supabase's
    transaction pooler, which drops connections it considers idle, so every
    checkout is pinged (`pool_pre_ping`) and nothing older than five minutes
    is reused (`pool_recycle`). The pool is sized for one Cloud Run instance:
    routes release their connection before slow LLM/TTS calls (see
    `release_connection`), so 5 + 5 per instance serves a request concurrency
    of 20–40 without pinning a pooler slot per waiting reader. The two env
    vars exist so the size can follow `--concurrency`/`--max-instances`
    without a code change.
    """
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {
        "connect_args": {"prepare_threshold": None},
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": integer("DB_POOL_SIZE", 5),
        "max_overflow": integer("DB_MAX_OVERFLOW", 5),
        "pool_timeout": 30,
    }


engine = create_engine(DATABASE_URL, **engine_options(DATABASE_URL))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def release_connection(db: Session) -> None:
    """End the session's transaction and hand its connection back to the pool.

    Call this before any slow provider call (LLM, TTS). Under Supavisor's
    transaction mode an open transaction pins a server connection, so one held
    idle through a 10–90 s model call is a pooler slot nobody else can use.
    Anything pending is committed rather than discarded. Loaded objects are
    expired; re-reading an attribute starts a new short transaction, so read
    what you need (ids, plain values) before calling this.
    """
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


@contextmanager
def short_session(db: Session) -> Iterator[Session]:
    """A fresh session on the same engine as `db`, for a write that follows a
    long provider call. It commits or rolls back on exit and keeps loaded
    attributes readable after closing (`expire_on_commit=False`), so returned
    rows can be serialised without another round trip.

    Bound to `db`'s engine rather than to `SessionLocal` so it follows
    whatever database the request was given (tests override `get_db`).
    """
    session = Session(bind=db.get_bind(), autoflush=False, expire_on_commit=False)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class Base(DeclarativeBase):
    pass


def init_db():
    # Importing the module registers every model on Base.metadata; the explicit
    # names keep the original four discoverable at a glance.
    from . import models  # noqa: F401
    from .models import Kundli, PredictionClaim, Reading, UserSettings  # noqa: F401
    # Postgres schema comes only from supabase/migrations, which also turn on
    # RLS and revoke client grants. create_all used to run there too, so a
    # model merged before its migration shipped as a table with no RLS and
    # Supabase's default grants. Local SQLite (dev and tests) still builds
    # from the models; ASTROSPACE_CREATE_TABLES=1 forces it for a scratch
    # Postgres.
    if DATABASE_URL.startswith("sqlite") or os.getenv("ASTROSPACE_CREATE_TABLES") == "1":
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
