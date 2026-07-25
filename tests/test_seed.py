"""Tests for the catalog seeder.

Idempotency is the point. `user_observances` and `user_remedies` reference
`festivals.id` and `remedies.id`, so a re-seed after an engine change has to
update rows in place — if it inserted duplicates or reassigned ids, it would
orphan whatever users had saved.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from astrospace.core.vedic import festivals as festival_engine
from astrospace.core.vedic import muhurta as muhurta_engine
from astrospace.core.vedic import remedies as remedy_engine
from astrospace.db import seed
from astrospace.db.database import Base
from astrospace.db.models import Festival, FestivalOccurrence, MuhurtaGoal, Remedy


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    try:
        yield session
    finally:
        session.close()


class TestCatalogs:
    def test_seeds_every_row_from_each_engine(self, db):
        report = seed.seed_all(db)
        assert report["remedies"]["inserted"] == len(remedy_engine.catalog())
        assert report["festivals"]["inserted"] == len(festival_engine.catalog())
        assert (report["muhurta_goals"]["inserted"]
                == len(muhurta_engine.goal_catalog()))

        assert db.query(Remedy).count() == len(remedy_engine.catalog())
        assert db.query(Festival).count() == len(festival_engine.catalog())
        assert db.query(MuhurtaGoal).count() == len(muhurta_engine.goal_catalog())

    def test_re_running_changes_nothing(self, db):
        seed.seed_all(db)
        before = db.query(Festival).count()
        report = seed.seed_all(db)
        assert report["festivals"]["inserted"] == 0
        assert report["festivals"]["updated"] == 0
        assert db.query(Festival).count() == before

    def test_re_seed_updates_in_place_and_keeps_ids(self, db):
        """A corrected rule must not orphan saved user_observances."""
        seed.seed_all(db)
        row = db.query(Festival).filter_by(slug="diwali").first()
        original_id = row.id
        row.description = "stale text"
        db.commit()

        report = seed.seed_festivals(db)
        assert report["updated"] == 1
        refreshed = db.query(Festival).filter_by(slug="diwali").first()
        assert refreshed.id == original_id
        assert refreshed.description != "stale text"

    def test_convention_flags_are_persisted(self, db):
        seed.seed_festivals(db)
        row = db.query(Festival).filter_by(slug="maha_shivaratri").first()
        assert row.panchanga_rule["at"] == "nishita"
        assert row.panchanga_rule["is_convention_dependent"] is True
        assert row.panchanga_rule["observance_note"]

    def test_remedies_carry_their_provenance(self, db):
        seed.seed_remedies(db)
        rows = db.query(Remedy).all()
        assert all(r.tradition_source for r in rows)
        assert all(r.is_convention_dependent for r in rows)


class TestOccurrences:
    def test_occurrences_need_festivals_first(self, db):
        with pytest.raises(RuntimeError, match="run seed_festivals"):
            seed.seed_festival_occurrences(db, "Chennai", "IN", [2026])

    def test_seeds_a_year_for_a_place(self, db):
        seed.seed_festivals(db)
        report = seed.seed_festival_occurrences(db, "Chennai", "IN", [2026])
        expected = len(festival_engine.occurrences(2026, city="Chennai",
                                                   nation="IN"))
        assert report["inserted"] == expected
        assert db.query(FestivalOccurrence).count() == expected

    def test_occurrences_are_idempotent(self, db):
        seed.seed_festivals(db)
        seed.seed_festival_occurrences(db, "Chennai", "IN", [2026])
        before = db.query(FestivalOccurrence).count()
        report = seed.seed_festival_occurrences(db, "Chennai", "IN", [2026])
        assert report["inserted"] == 0
        assert db.query(FestivalOccurrence).count() == before

    def test_places_are_stored_separately(self, db):
        """Two places can legitimately disagree by a day, so both are kept."""
        seed.seed_festivals(db)
        seed.seed_festival_occurrences(db, "Chennai", "IN", [2026])
        seed.seed_festival_occurrences(db, "New Delhi", "IN", [2026])
        keys = {row[0] for row in db.query(FestivalOccurrence.place_key).all()}
        assert keys == {"IN/Chennai", "IN/New Delhi"}

    def test_seeding_unblocks_the_practice_endpoint(self, db):
        """/practice/remedies takes a remedy_id that had nothing to point at.

        This is the reason the seeder exists, so it is asserted through the
        route rather than against the table.
        """
        from fastapi.testclient import TestClient

        from main import app
        from astrospace.api.auth import AuthUser, current_user
        from astrospace.db import crud, get_db

        seed.seed_remedies(db)
        remedy_id = db.query(Remedy).filter_by(remedy_type="mantra").first().id
        kundli_id = crud.create_kundli(db, {
            "user_id": "seed-test-user", "name": "Seeded", "relation": "self",
            "birth_year": 1991, "birth_month": 8, "birth_day": 14,
            "birth_hour": 6, "birth_minute": 12,
            "birth_city": "Vijayawada", "birth_nation": "IN",
        }).id

        def override_get_db():
            # Must be a generator function — FastAPI injects the return value
            # of a plain callable, so a bare iterator arrives as the session.
            yield db

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[current_user] = lambda: AuthUser(
            id="seed-test-user", email="seed@astrospace.dev", role="dev"
        )
        try:
            client = TestClient(app)
            started = client.post("/api/v1/practice/remedies", json={
                "kundli_id": kundli_id, "remedy_id": remedy_id,
                "cadence": "daily",
            })
            assert started.status_code == 200, started.text
            assert started.json()["remedy_id"] == remedy_id
        finally:
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides.pop(current_user, None)

    def test_caveats_survive_into_the_row(self, db):
        """A client reading the table gets the same caveat as one calling the
        engine — otherwise the honesty contract stops at the API boundary."""
        seed.seed_festivals(db)
        seed.seed_festival_occurrences(db, "Chennai", "IN", [2026])
        festival_id = db.query(Festival).filter_by(slug="diwali").first().id
        row = (db.query(FestivalOccurrence)
               .filter_by(festival_id=festival_id, place_key="IN/Chennai")
               .first())
        assert row.occurs_on.isoformat() == "2026-11-08"
        assert row.computed_meta["is_convention_dependent"] is True
        assert "pradosh" in row.computed_meta["observance_note"]
