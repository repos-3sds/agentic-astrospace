"""Executable form of docs/mobile_data_contract.md's field budgets.

A type says `string`. It does not say *110 characters or the card breaks*.
Three defects shipped past a green build and a type checker on 2026-07-27,
all the same shape — engine output the layout was never sized for (see the
doc's "Why this exists"). Those budgets lived only as a markdown table;
nothing ran them.

Breakage travels engine -> UI, so these run here rather than in the frontend
suite, against the same routes the mobile app calls. Auth/DB pattern follows
test_mobile_routes.py: `get_db` and `current_user` are overridden with an
in-memory sqlite session and a fixed dev user.

Adding a budget for a new endpoint/field is one row in BUDGETS below, not a
new test function — `payloads()` fetches each endpoint at most once per run
regardless of how many budgets reference it.
"""
from dataclasses import dataclass
from typing import Any, Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from astrospace.api.auth import AuthUser, current_user
from astrospace.db import crud, get_db
from astrospace.db.database import Base

TEST_USER_ID = "test-user-mobile-data-contract"


@dataclass(frozen=True)
class FieldBudget:
    endpoint: str  # "{id}" is substituted with the test kundli's id
    field: str  # dotted path, for reporting only — the getter does the real work
    get: Callable[[dict], Any]
    holds: Callable[[Any], bool]
    why: str  # what breaks on the mobile screen if this budget is violated


BUDGETS: list[FieldBudget] = [
    FieldBudget(
        "/context/{id}/daily", "reading.summary",
        get=lambda daily: daily["reading"]["summary"],
        holds=lambda v: isinstance(v, str) and len(v) <= 110,
        why="Today's advice card is drawn for one line at this length; a "
            "longer summary pushed Do/Avoid off-screen (2026-07-27).",
    ),
    FieldBudget(
        "/context/{id}/daily", "verdict.tone",
        get=lambda daily: daily["verdict"]["tone"],
        holds=lambda v: v in {"supportive", "positive", "mixed", "caution"},
        why="Today's tone label and gaugePositionFromScore's bands "
            "(today.component.ts) both switch on exactly these four values "
            "— a fifth has no rendering.",
    ),
    FieldBudget(
        "/context/{id}/daily", "verdict.score",
        get=lambda daily: daily["verdict"]["score"],
        holds=lambda v: isinstance(v, int) and not isinstance(v, bool),
        why="gaugePositionFromScore maps this through a signed-tally band, "
            "never a 0-100 percentage. Today clamped it to that range once "
            "and every real reading rendered as an empty ring (2026-07-27).",
    ),
    FieldBudget(
        "/vedic/{id}/ashtakavarga", "sav",
        get=lambda av: av["sav"],
        holds=lambda v: len(v) == 12 and sum(v) == 337,
        why="Sarvashtakavarga is classical: twelve houses summing to "
            "exactly 337. A header stating any other total contradicts its "
            "own grid (2026-07-27).",
    ),
]


@pytest.fixture(scope="module")
def contract_client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    def override_current_user():
        return AuthUser(id=TEST_USER_ID, email="test@astrospace.dev", role="dev")

    db = session_factory()
    kundli = crud.create_kundli(db, {
        "user_id": TEST_USER_ID,
        "name": "Data Contract Test",
        "relation": "self",
        "birth_year": 1990, "birth_month": 5, "birth_day": 17,
        "birth_hour": 14, "birth_minute": 30,
        "birth_city": "Chennai", "birth_nation": "IN",
    })
    kundli_id = kundli.id
    db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[current_user] = override_current_user
    try:
        yield TestClient(app), kundli_id
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(current_user, None)


@pytest.fixture(scope="module")
def payloads(contract_client):
    """Fetches each distinct endpoint template at most once, regardless of
    how many budgets in the table reference it."""
    client, kundli_id = contract_client
    cache: dict[str, dict] = {}

    def get(endpoint_template: str) -> dict:
        if endpoint_template not in cache:
            path = "/api/v1" + endpoint_template.format(id=kundli_id)
            response = client.get(path)
            assert response.status_code == 200, (
                f"{path} -> {response.status_code}: {response.text}"
            )
            cache[endpoint_template] = response.json()
        return cache[endpoint_template]

    return get


@pytest.mark.parametrize(
    "budget", BUDGETS, ids=[f"{b.endpoint}::{b.field}" for b in BUDGETS]
)
def test_field_budget(payloads, budget: FieldBudget):
    payload = payloads(budget.endpoint)
    value = budget.get(payload)

    assert budget.holds(value), (
        f"{budget.endpoint} field `{budget.field}` violated its budget "
        f"(value={value!r}). {budget.why}"
    )


def test_calendar_selected_day_starts_at_requested_local_date(contract_client):
    client, kundli_id = contract_client
    response = client.get(
        f"/api/v1/vedic/{kundli_id}/calendar-intelligence",
        params={
            "days": 1,
            "as_of": "2026-09-03",
            "timezone": "Asia/Singapore",
            "city": "Singapore",
            "nation": "SG",
            "include_practitioner_detail": "true",
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["start_date"] == "2026-09-03"
    assert payload["timezone"] == "Asia/Singapore"
    assert payload["place"]["city"] == "Singapore"
    assert payload["panchanga_days"][0]["date"] == "2026-09-03"
    assert payload["panchanga_days"][0]["practitioner_detail"]["windows"]
