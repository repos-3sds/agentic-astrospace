import os
from sqlalchemy import inspect, text
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# SQLite by default; swap to Supabase with DATABASE_URL=postgresql://...
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:////home/user/agentic-astrospace/astrospace.db"
)

# SQLite needs check_same_thread=False
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def init_db():
    from .models import Kundli, PredictionClaim, Reading  # noqa: F401
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
