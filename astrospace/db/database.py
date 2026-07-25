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

# SQLite needs check_same_thread=False
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

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


def _migrate_sqlite_kundlis():
    if not DATABASE_URL.startswith("sqlite"):
        return
    inspector = inspect(engine)
    if "kundlis" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("kundlis")}
    with engine.begin() as conn:
        if "user_id" not in existing:
            conn.execute(text("ALTER TABLE kundlis ADD COLUMN user_id VARCHAR DEFAULT 'local-dev-user'"))
        conn.execute(text("""
            UPDATE kundlis
            SET user_id = 'local-dev-user'
            WHERE user_id IS NULL OR user_id = ''
        """))


def _migrate_sqlite_readings():
    """Small additive migration path for local SQLite during active development."""
    if not DATABASE_URL.startswith("sqlite"):
        return
    inspector = inspect(engine)
    if "readings" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("readings")}
    additions = {
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
