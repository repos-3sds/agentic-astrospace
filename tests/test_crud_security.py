from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from astrospace.db.database import Base
from astrospace.db import crud


def _session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_reading_helpers_filter_by_kundli_owner():
    db = _session()
    try:
        owner = crud.create_kundli(db, {
            "user_id": "user-a",
            "name": "Owner",
            "relation": "self",
            "birth_year": 1993,
            "birth_month": 7,
            "birth_day": 20,
            "birth_hour": 11,
            "birth_minute": 28,
            "birth_city": "Rajahmundry",
            "birth_nation": "IN",
        })
        other = crud.create_kundli(db, {
            "user_id": "user-b",
            "name": "Other",
            "relation": "friend",
            "birth_year": 1997,
            "birth_month": 2,
            "birth_day": 26,
            "birth_hour": 21,
            "birth_minute": 30,
            "birth_city": "Hyderabad",
            "birth_nation": "IN",
        })
        reading = crud.save_reading(
            db,
            owner.id,
            "daily",
            "A private reading",
            period_label="2026-07-14",
            generated_local_date="2026-07-14",
        )
        crud.save_reading(
            db,
            other.id,
            "daily",
            "Another user's reading",
            period_label="2026-07-14",
            generated_local_date="2026-07-14",
        )

        assert crud.get_reading(db, owner.id, reading.id, "user-a") is not None
        assert crud.get_reading(db, owner.id, reading.id, "user-b") is None
        assert crud.get_latest_reading(db, owner.id, "daily", "user-b") is None
        assert crud.get_readings(db, owner.id, "user-b") == []
        assert crud.get_readings_for_calendar(db, owner.id, "user-b", "2026-07-14", "2026-07-14") == []
    finally:
        db.close()


def test_user_settings_are_per_user():
    db = _session()
    try:
        first = crud.upsert_user_settings(db, "user-a", {
            "chart_style": "north",
            "ayanamsha": "raman",
            "node_type": "true",
            "timezone_mode": "panchanga_place",
            "panchanga_place": {
                "city": "Hyderabad",
                "nation": "IN",
                "timezone": "Asia/Kolkata",
                "label": "Hyderabad, IN · Asia/Kolkata",
            },
            "language": "en",
            "regional_format": "en-IN",
        })
        second = crud.upsert_user_settings(db, "user-b", {
            "chart_style": "south",
            "ayanamsha": "lahiri",
            "node_type": "mean",
            "timezone_mode": "browser",
            "panchanga_place": None,
            "language": "en",
            "regional_format": "en-US",
        })

        assert first.user_id == "user-a"
        assert second.user_id == "user-b"
        assert crud.get_user_settings(db, "user-a").chart_style == "north"
        assert crud.get_user_settings(db, "user-b").chart_style == "south"
    finally:
        db.close()
