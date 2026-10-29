"""Two or more charts for one purpose: muhurta for a group, months that suit
everyone, which saved profiles a question names, and Ask's `group_reading`."""
from datetime import date

import pytest

from astrospace.agents.orchestrator import AskOrchestrator
from astrospace.agents.verifier import valid_sources
from astrospace.context.group_reading import group_section, purpose_of
from astrospace.context.people import resolve_people
from astrospace.core.vedic import group_timing, muhurta
from astrospace.core.vedic.chart import VedicChart

PLACE = {"lat": 17.385, "lng": 78.4867, "tz_str": "Asia/Kolkata"}


@pytest.fixture(scope="module")
def family():
    return {
        "Ramesh": VedicChart("Ramesh", 1974, 8, 2, 6, 10, **PLACE),
        "Lakshmi": VedicChart("Lakshmi", 1978, 1, 20, 21, 45, lat=16.5, lng=80.6, tz_str="Asia/Kolkata"),
        "Arjun": VedicChart("Arjun", 2002, 3, 9, 4, 20, **PLACE),
    }


# ── muhurta for several people ───────────────────────────────────────────────

def _find(**kw):
    return muhurta.find("buy_vehicle", date(2026, 11, 2), date(2026, 11, 15),
                        janma_nakshatra_index=5, janma_rashi_index=2, limit=8, **PLACE, **kw)


def test_couple_slots_list_both_people():
    out = _find(partner={"nak": 11, "rashi": 4, "name": "Meera"})
    assert out["results"]
    for slot in out["results"]:
        assert [p["name"] for p in slot["people"]] == ["you", "Meera"]
        assert all(p["standing"] in ("strong", "fair", "weak") for p in slot["people"])


def test_one_person_slots_have_no_people_list():
    assert all("people" not in slot for slot in _find()["results"])


def test_family_of_three_is_scored_and_listed():
    others = [{"nak": 11, "rashi": 4, "name": "Lakshmi"}, {"nak": 20, "rashi": 8, "name": "Arjun"}]
    out = _find(others=others)
    assert out["results"]
    assert [p["name"] for p in out["results"][0]["people"]] == ["you", "Lakshmi", "Arjun"]


def test_a_members_hard_day_marks_a_date_but_a_leads_rules_it_out():
    # A major goal over a month, so each person's Chandrashtama days fall in it.
    def scan(person):
        return muhurta.find("bhoomi_puja", date(2027, 1, 4), date(2027, 2, 3),
                            janma_nakshatra_index=5, janma_rashi_index=2, limit=30,
                            observe_season=False, others=[person], **PLACE)
    member = {"nak": 0, "rashi": 4, "name": "Arjun"}
    hard_for_member = [s for s in scan(member)["results"]
                       if any(p["chandrashtama"] for p in s["people"] if p["name"] == "Arjun")]
    hard_for_lead = [s for s in scan({**member, "lead": True})["results"]
                     if any(p["chandrashtama"] for p in s["people"] if p["name"] == "Arjun")]
    assert hard_for_lead == []
    assert hard_for_member, "a member's hard day should stay, marked"


def test_more_than_five_people_is_refused():
    others = [{"nak": i, "rashi": i % 12, "name": f"P{i}"} for i in range(5)]
    with pytest.raises(ValueError):
        _find(others=others)


# ── months that suit everyone ────────────────────────────────────────────────

def test_good_months_shape(family):
    people = [{"name": n, "chart": c} for n, c in family.items()]
    out = group_timing.good_months(people, "vehicle", date(2026, 11, 1), 6)
    assert len(out["months"]) == 6
    assert out["months"][0]["label"] == "November 2026"
    for row in out["months"]:
        assert row["together"] in ("good", "fair", "mixed")
        assert {p["name"] for p in row["people"]} == set(family)
        assert all(p["standing"] in ("strong", "fair", "quiet", "slow") for p in row["people"])
        assert (row["together"] == "mixed") == bool(row["slow_for"])
    assert out["is_convention_dependent"] and "BPHS" in out["rules"]


def test_unknown_birth_time_reads_from_the_moon(family):
    people = [{"name": "Ramesh", "chart": family["Ramesh"]},
              {"name": "Lakshmi", "chart": family["Lakshmi"], "time_known": False}]
    out = group_timing.good_months(people, "home", date(2026, 11, 1), 3)
    assert out["time_unknown_for"] == ["Lakshmi"]


def test_unknown_purpose_is_refused(family):
    with pytest.raises(ValueError):
        group_timing.good_months([{"name": "R", "chart": family["Ramesh"]}], "lottery", date(2026, 11, 1))


# ── which saved profiles a question names ────────────────────────────────────

PROFILES = [
    {"id": "r", "name": "Ramesh K", "relation": "self"},
    {"id": "l", "name": "Lakshmi", "relation": "spouse"},
    {"id": "a", "name": "Arjun", "relation": "child"},
    {"id": "m", "name": "Meera", "relation": "child"},
    {"id": "k", "name": "Karthik", "relation": "prospect", "kind": "prospect"},
    {"id": "v", "name": "Vikram", "relation": "friend"},
]


@pytest.mark.parametrize("question,ids", [
    ("Lakshmi and I want to buy a flat next year", ["r", "l"]),
    ("My wife and I want to buy a car", ["r", "l"]),
    ("My friend Vikram and I want to start a catering business", ["r", "v"]),
    ("Which dates suit Arjun and Meera's weddings on the same day?", ["a", "m"]),
    ("Dates for my two kids' weddings", ["a", "m"]),
    ("Good griha pravesh date for the whole family", ["r", "l", "a", "m"]),
    ("When should I buy a car?", ["r"]),
])
def test_resolves_the_people_named(question, ids):
    assert resolve_people(question, PROFILES, "r")["ids"] == ids


def test_one_of_two_children_is_never_guessed():
    found = resolve_people("Will my son get a job abroad?", PROFILES, "r")
    assert found["ids"] == ["r"] and not found["group"]
    assert found["ambiguous"] == {"son": ["Arjun", "Meera"]}


def test_a_relative_not_saved_is_reported():
    found = resolve_people("How is this year for my father?", PROFILES, "r")
    assert found["not_saved"] == ["father"] and not found["group"]


def test_family_leaves_out_prospects_and_friends():
    ids = resolve_people("How does next year look for our family?", PROFILES, "r")["ids"]
    assert "k" not in ids and "v" not in ids


def test_picked_profiles_count_and_others_accounts_cannot_be_picked():
    found = resolve_people("When should we buy a car?", PROFILES, "r", picked_ids=["l", "someone-else"])
    assert found["ids"] == ["r", "l"]


def test_never_more_than_five():
    many = PROFILES + [{"id": f"x{i}", "name": f"Kid{i}", "relation": "child"} for i in range(4)]
    assert len(resolve_people("for our whole family", many, "r")["ids"]) == 5


# ── Ask's group_reading section ──────────────────────────────────────────────

@pytest.mark.parametrize("question,purpose", [
    ("buy a flat", "home"), ("new car", "vehicle"), ("start a business together", "venture"),
    ("both weddings", "marriage"), ("pilgrimage trip", "travel"), ("thread ceremony", "event"),
    ("what about us", "general"),
])
def test_purpose_of(question, purpose):
    assert purpose_of(question) == purpose


def test_group_section_reads_everyone(family):
    people = [{"name": n, "relation": r, "chart": family[n]}
              for n, r in (("Ramesh", "self"), ("Lakshmi", "spouse"))]
    section = group_section(people, "Lakshmi and I want to buy a car. Good date?", today=date(2026, 11, 2))
    assert [p["name"] for p in section["people"]] == ["Ramesh", "Lakshmi"]
    assert section["purpose"] == "buying a vehicle"
    assert len(section["months"]) == 12
    slots = section["muhurta"]["slots"]
    assert slots and [e["name"] for e in slots[0]["each"]] == ["Ramesh", "Lakshmi"]
    assert "lawyer or CA" in section["how_to_use"]


def test_one_person_gets_no_section_unless_someone_was_missing(family):
    me = [{"name": "Ramesh", "relation": "self", "chart": family["Ramesh"]}]
    assert group_section(me, "When should I buy a car?") is None
    note = group_section(me, "How is my father's year?", not_saved=["father"])
    assert note["not_saved"] == ["father"] and "not saved" in note["how_to_use"]


def test_group_reading_is_citable_only_when_present():
    assert "group_reading" in valid_sources({"group_reading": {"people": [1]}})
    assert "group_reading" not in valid_sources({})


def test_ask_bundle_carries_the_group(family):
    def loader(question):
        return {"people": [{"name": "Ramesh", "relation": "self", "chart": family["Ramesh"]},
                           {"name": "Lakshmi", "relation": "spouse", "chart": family["Lakshmi"]}]}
    orchestrator = AskOrchestrator(chart_loader=lambda: family["Ramesh"], group_loader=loader)
    outcome = orchestrator.prepare("Lakshmi and I want to buy a house next year. Which months suit us?")
    bundle = outcome.prepared.bundle
    assert [p["name"] for p in bundle["group_reading"]["people"]] == ["Ramesh", "Lakshmi"]
    assert "group_reading" in outcome.prepared.context_used


def test_a_failing_group_loader_falls_back_to_one_chart(family):
    def loader(question):
        raise RuntimeError("profile store down")
    orchestrator = AskOrchestrator(chart_loader=lambda: family["Ramesh"], group_loader=loader)
    outcome = orchestrator.prepare("Lakshmi and I want to buy a house next year. Which months suit us?")
    assert "group_reading" not in outcome.prepared.bundle


# ── the route's loader, against a real database ──────────────────────────────

def test_route_loader_reads_saved_profiles(tmp_path):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from astrospace.api.ask_routes import _group_loader
    from astrospace.db import crud
    from astrospace.db.database import Base

    engine = create_engine(f"sqlite:///{tmp_path / 'g.db'}")
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    base = {"user_id": "u", "birth_month": 3, "birth_day": 9, "birth_hour": 6,
            "birth_minute": 0, "birth_city": "Hyderabad", "birth_nation": "IN"}
    me = crud.create_kundli(db, {**base, "name": "Ramesh K", "relation": "self", "birth_year": 1974})
    crud.create_kundli(db, {**base, "name": "Lakshmi", "relation": "spouse", "birth_year": 1978,
                            "birth_time_accuracy": "unknown"})
    crud.create_kundli(db, {**base, "user_id": "someone-else", "name": "Lakshmi", "relation": "self",
                            "birth_year": 1980})

    load = _group_loader(db, "u", me, ("lahiri", "mean"), picked=None)
    found = load("Lakshmi and I want to buy a flat")
    assert [p["name"] for p in found["people"]] == ["Ramesh", "Lakshmi"]
    assert [p["time_known"] for p in found["people"]] == [True, False]
    assert load("When should I buy a car?") is None
    assert load("How is my father's year?")["not_saved"] == ["father"]
