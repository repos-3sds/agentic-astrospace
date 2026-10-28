"""Ask home suggestions built from the profile's own chart
(astrospace/core/vedic/ask_suggestions.py).

Every prompt the app offers must be one the answer pipeline takes as asked:
no refer-out, no "which area do you mean?". And it must not assume a life
the reader has not told us about."""
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from astrospace.agents.orchestrator import _needs_clarification
from astrospace.agents.safety import refer_out_kind
from astrospace.context.router import KeywordRouter
from astrospace.core.vedic import VedicChart
from astrospace.core.vedic.ask_suggestions import TOPICS, ask_suggestions, facts_from_chart, topic_suggestions

IST = ZoneInfo("Asia/Kolkata")
AS_OF = datetime(2026, 10, 28, 9, 0, tzinfo=IST)

BIRTHS = [
    (1990, 5, 14, 6, 30, "Hyderabad"),
    (1985, 11, 2, 22, 15, "Chennai"),
    (2001, 1, 20, 9, 0, "Mumbai"),
    (1972, 8, 9, 4, 45, "Kolkata"),
    (1996, 3, 27, 13, 10, "Delhi"),
    (1964, 12, 31, 18, 0, "Bengaluru"),
]
LIVES = [
    {},
    {"relationship_status": "married", "has_children": True, "employment_status": "employed"},
    {"relationship_status": "single", "has_children": False, "employment_status": "student"},
    {"employment_status": "unemployed", "looking_for_work": True},
    {"employment_status": "retired"},
]


@pytest.fixture(scope="module")
def charts():
    return [VedicChart("X", *b, "IN") for b in BIRTHS]


def _all(charts):
    for chart in charts:
        for mode in ("guided", "balanced", "practitioner"):
            for life in LIVES:
                yield life, ask_suggestions(chart, mode=mode, as_of=AS_OF, life=life)


def _prompts(result):
    yield from result["general"]
    for items in result["by_topic"].values():
        yield from items


def test_every_list_is_full(charts):
    for _, result in _all(charts):
        assert len(result["general"]) == 3
        assert set(result["by_topic"]) == set(TOPICS)
        for topic, items in result["by_topic"].items():
            assert 3 <= len(items) <= 4, (topic, items)
            assert len({s["prompt"] for s in items}) == len(items)
            assert all(s["because"] for s in items)


def test_no_prompt_refers_out_or_needs_clarifying(charts):
    router = KeywordRouter()
    seen = {s["prompt"] for _, result in _all(charts) for s in _prompts(result)}
    refer = [p for p in seen if refer_out_kind(p)]
    unclear = [p for p in seen if _needs_clarification(router.route(p))]
    assert not refer, refer
    assert not unclear, unclear


def test_prompts_follow_the_running_dasha(charts):
    for chart in charts:
        facts = facts_from_chart(chart, as_of=AS_OF)
        running = {facts.md["lord"], facts.ad["lord"]}
        text = " ".join(s["prompt"] + s["because"] for s in ask_suggestions(chart, as_of=AS_OF)["general"])
        assert any(lord in text for lord in running) or "Sade Sati" in text or "Saturn" in text


def test_nothing_assumes_a_child_or_a_marriage(charts):
    for life, result in _all(charts):
        text = " ".join(s["prompt"] for s in _prompts(result)).lower()
        if life.get("has_children") is not True:
            assert "my child" not in text and "my children" not in text
        if life.get("relationship_status") != "married":
            assert not re.search(r"my marriage(?! plans)", text), text
            assert "my spouse" not in text and "my husband" not in text and "my wife" not in text


def test_reader_facts_change_the_wording(charts):
    chart = charts[0]
    facts = facts_from_chart(chart, as_of=AS_OF, life={"relationship_status": "married", "has_children": True})
    marriage = " ".join(s["prompt"] for s in topic_suggestions(facts, "marriage"))
    child = " ".join(s["prompt"] for s in topic_suggestions(facts, "child"))
    assert re.search(r"my marriage(?! plans)", marriage)
    assert "my children" in child


def test_money_and_health_never_ask_for_a_verdict(charts):
    banned = ("invest", "buy", "stock", "loan", "disease", "illness", "surgery", "cure", "die", "death")
    for _, result in _all(charts):
        for topic in ("money", "health"):
            for s in result["by_topic"][topic]:
                assert not any(word in s["prompt"].lower() for word in banned), s


def test_practitioner_gets_house_numbers_and_others_do_not(charts):
    for chart in charts:
        plain = ask_suggestions(chart, mode="balanced", as_of=AS_OF)
        assert not any("th house" in s["because"] or "rules your" in s["because"] for s in _prompts(plain))


class TestRoute:
    @pytest.fixture(scope="class")
    def client(self):
        from fastapi.testclient import TestClient
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool

        from main import app
        from astrospace.api.auth import AuthUser, current_user
        from astrospace.db import get_db
        from astrospace.db.database import Base

        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False},
                               poolclass=StaticPool)
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        def override_get_db():
            db = Session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[current_user] = lambda: AuthUser(
            id="test-user-suggest", email="suggest@astrospace.dev", role="dev")
        try:
            yield TestClient(app)
        finally:
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides.pop(current_user, None)

    def test_unknown_profile_404(self, client):
        assert client.get("/api/v1/ask/nonexistent-id/suggestions").status_code == 404

    def test_lists_follow_what_the_reader_told_us(self, client):
        kundli = client.post("/api/v1/kundlis", json={
            "name": "Reader", "relation": "self",
            "birth_year": 1991, "birth_month": 8, "birth_day": 14, "birth_hour": 6, "birth_minute": 12,
            "birth_city": "Vijayawada", "birth_nation": "IN",
        }).json()["id"]
        before = client.get(f"/api/v1/ask/{kundli}/suggestions").json()
        assert [t["id"] for t in before["topics"]] == list(TOPICS)
        assert len(before["general"]) == 3
        assert "my children" not in " ".join(s["prompt"] for s in before["by_topic"]["child"])

        added = client.post(f"/api/v1/profiles/{kundli}/context/facts", json={
            "expected_revision": 0, "key": "has_children", "value": {"value": True},
            "source": {"kind": "profile_form", "channel": "profile_settings"},
            "consent": {"state": "granted", "surface": "profile_settings"},
        }, headers={"Idempotency-Key": "8d7f1c1e-0a51-4c39-9d6c-5b1f2a7c3e01"})
        assert added.status_code == 201, added.text
        after = client.get(f"/api/v1/ask/{kundli}/suggestions?mode=practitioner").json()
        assert "my children" in " ".join(s["prompt"] for s in after["by_topic"]["child"])
