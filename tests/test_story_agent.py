"""Your Story (Guided mode): personality traits, life areas and the current
chapter, read from one chart through the classical rules it meets.

The model is stubbed: these tests pin what the reader is promised (each
section gets only the stored rules this chart meets, badges come from the
chart and not the model, nothing crosses a boundary, one story per profile
written once and kept, and the code backup whenever it cannot be written),
not what a model happens to write.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from astrospace.agents import story_agent as sa
from astrospace.agents import story_classics as sc
from astrospace.api.auth import AuthUser, current_user
from astrospace.context import life_story_store as store
from astrospace.core.vedic import VedicChart
from astrospace.db import crud, get_db
from astrospace.db.database import Base
from astrospace.db.models import LifeStory
from main import app

ME = "story-reader"
AS_OF = datetime(2026, 10, 28, tzinfo=timezone.utc)
PLACEMENTS = Path("astrospace/context/placement_references.json")


def _chart(which: str = "anika") -> VedicChart:
    return {
        "anika": VedicChart("Anika", 1990, 5, 15, 6, 30, "Hyderabad", "IN"),
        "ravi": VedicChart("Ravi", 1985, 11, 2, 22, 10, "Chennai", "IN"),
        "meera": VedicChart("Meera", 1995, 2, 20, 13, 45, "Mumbai", "IN"),
    }[which]


def _signals(which: str = "anika") -> dict:
    chart = _chart(which)
    facts = sc.chart_facts(chart, AS_OF)
    return {"rules": sc.section_rules(facts), "tones": sc.area_tones(facts), "yogas": facts["yogas"],
            "running": facts["running"], "_facts": facts}


def _ids(signals: dict, section: str) -> list[str]:
    return [rule["id"] for rule in signals["rules"][section]]


def _story(rules: list[str] | None = None, detail: str = "You stay calm when others rush.",
           chapter: str = "You are in a Rahu period until 2028. It puts faith and long journeys at the front.") -> sa.LifeStory:
    return sa.LifeStory(
        headline="Calm, warm and quietly determined",
        summary="You move at your own pace and keep your word. People trust you with things that matter.",
        traits=[sa.Trait(title="Steady under pressure", detail=detail),
                sa.Trait(title="A fine eye for beauty", detail="Food, music and a tidy home lift your mood."),
                sa.Trait(title="Generous with friends", detail="You give freely, and it tends to come back."),
                sa.Trait(title="Keeps promises", detail="People rely on your word.")],
        growth="Steady can turn stubborn. When a plan stops working, change course a little sooner.",
        areas=[sa.Area(key="work", text="Your work tends to be noticed.", tip="Take on one hard task this month."),
               sa.Area(key="relationships", text="People feel safe around you.", tip="Say thank you out loud."),
               sa.Area(key="money", text="Money grows the slow, sure way.", tip="Save first, spend after."),
               sa.Area(key="energy", text="Your energy is good with a rhythm.", tip="Sleep at the same time daily.")],
        chapter=chapter,
        rules_used=rules or ["bphs4_lagna_taurus", "bj17_9_moon_in_sagittarius", "uk4_tenth_bhava_scope"],
    )


class _Scripted(sa.LifeStoryAgent):
    def __init__(self, drafts):
        self.provider, self.model, self.usage_log = "gemini", "stub", []
        self.queue, self.prompts = list(drafts), []

    def run_structured(self, messages, schema, tool_name="deliver_result", input_schema=None):
        self.prompts.append(messages[0]["content"])
        return self.queue.pop(0)


# ── The placement rules ─────────────────────────────────────────────────────

def test_every_placement_has_its_rule_except_the_stars_the_ocr_lost():
    refs = {ref["ref_id"] for ref in json.loads(PLACEMENTS.read_text(encoding="utf-8"))["references"]}
    signs = [s.lower() for s in sc.SIGNS]
    assert {f"bphs4_lagna_{s}" for s in signs} <= refs
    assert {f"bphs26_{h}_lagna_lord_in_{h}" for h in range(1, 13)} <= refs
    assert len([r for r in refs if r.startswith("bj17_")]) == 12
    # Brihat Jataka ch.XVI st.1-4 (Ashwini to Punarvasu) is missing from our copy.
    assert len([r for r in refs if r.startswith("bj16_")]) == 20
    assert set(sc.STAR_PLAIN) == {r.split("_moon_star_")[1].replace("_", " ").title()
                                  for r in refs if r.startswith("bj16_")}


def test_placement_rules_pass_the_same_guards_as_the_main_store():
    from tests.test_kb_references_integrity import _MORTAL
    main = json.loads(Path("astrospace/context/references.json").read_text(encoding="utf-8"))["references"]
    placements = json.loads(PLACEMENTS.read_text(encoding="utf-8"))["references"]
    sources = json.loads(Path("astrospace/context/sources.json").read_text(encoding="utf-8"))["sources"]
    assert not {r["ref_id"] for r in main} & {r["ref_id"] for r in placements}
    for ref in placements:
        assert not _MORTAL.search(ref["statement"]), ref["ref_id"]
        assert sources[ref["source"]["text_key"]]["corpus_status"] == "readable"
        assert "trans." in ref["source"]["location"]
        assert ref["status"] == "convention_dependent" and ref["observance_note"]
        assert not re.search(r"\b(wives|wife will|thievish|gambler|sinful|cheat)\b", ref["statement"], re.I), ref["ref_id"]


def test_plain_backup_lines_carry_no_astrology_terms():
    lines = [*sc.LAGNA_PLAIN.values(), *sc.LAGNA_LORD_PLAIN.values(), *sc.MOON_PLAIN.values(),
             *sc.STAR_PLAIN.values(), *sc.GROWTH_PLAIN.values(), *sc.MAHAPURUSHA_PLAIN.values(),
             *(f"{text} {tip}" for text, tip in sc.AREA_PLAIN.values())]
    assert [line for line in lines if sa._jargon(line)] == []


# ── What each section is given ──────────────────────────────────────────────

def test_personality_reads_this_charts_own_placements():
    ids = _ids(_signals("anika"), "personality")
    # Taurus rising, its lord Venus in the 11th, Moon in Sagittarius in Uttara Ashadha.
    assert {"bphs4_lagna_taurus", "bphs26_11_lagna_lord_in_11", "bj17_9_moon_in_sagittarius",
            "bj16_11_moon_star_uttara_ashadha"} <= set(ids)
    assert not [i for i in ids if i.startswith("bphs4_lagna_") and i != "bphs4_lagna_taurus"]


def test_two_people_with_the_same_rising_sign_get_different_rules():
    ravi, meera = (set(_ids(_signals(w), "personality")) for w in ("ravi", "meera"))
    assert "bphs4_lagna_gemini" in ravi & meera
    assert ravi ^ meera >= {"bphs26_6_lagna_lord_in_6", "bphs26_8_lagna_lord_in_8",
                            "bj17_3_moon_in_gemini", "bj17_7_moon_in_libra"}


def test_a_star_the_ocr_lost_simply_has_no_rule():
    # Ravi's Moon is in Ardra, one of the seven stars our Brihat Jataka copy is missing.
    assert not [i for i in _ids(_signals("ravi"), "personality") if i.startswith("bj16_")]


def test_moon_strength_sets_how_fully_the_moon_rules_show():
    rule = next(r for r in _signals("anika")["rules"]["personality"] if r["id"] == "bj17_9_moon_in_sagittarius")
    assert "show only in part" in rule["applies_because"]


def test_work_follows_the_tenth_lords_real_strength():
    anika, ravi = _signals("anika"), _signals("ravi")
    # Anika's 10th lord Saturn is in its own sign; Ravi's Jupiter is debilitated in the 8th.
    assert "bphs21_2_tenth_lord_strong" in _ids(anika, "work")
    assert "bphs21_3_tenth_lord_weak" in _ids(ravi, "work")
    weak = next(r for r in ravi["rules"]["work"] if r["id"] == "bphs21_3_tenth_lord_weak")
    assert "Never as failure" in weak["read_as"]


def test_badges_come_from_the_chart_not_a_fixed_list():
    assert _signals("anika")["tones"]["work"] == "strong"
    assert _signals("ravi")["tones"]["work"] == "gentle"
    tones = {w: _signals(w)["tones"] for w in ("anika", "ravi", "meera")}
    assert len({t["work"] for t in tones.values()}) > 1


def test_money_reads_the_second_and_eleventh_lords():
    ids = _ids(_signals("ravi"), "money")
    assert {"uk_wealth_2nd_11th", "bphs24_124_eleventh_lord_in_fourth", "bphs_dhana_yoga_wealth"} <= set(ids)


def test_relationships_reuse_the_marriage_picker():
    assert "bphs_seventh_kalatra" in _ids(_signals("anika"), "relationships")


def test_energy_never_carries_a_disease_rule():
    for which in ("anika", "ravi", "meera"):
        assert _ids(_signals(which), "energy") == ["uk_1st_lagna_vitality"]


def test_every_picked_rule_is_a_stored_statement():
    stored = sc._stored()
    for section, rules in _signals("meera")["rules"].items():
        for rule in rules:
            assert stored[rule["id"]] == rule["rule"], (section, rule["id"])


def test_the_model_never_sees_the_raw_facts():
    signals = _signals()
    assert "_facts" not in sa.model_input(signals) and "rules" in sa.model_input(signals)


# ── The code backup ─────────────────────────────────────────────────────────

def test_the_backup_is_built_from_this_charts_placements():
    anika = sc.fallback_story(_signals("anika")["_facts"])
    meera = sc.fallback_story(_signals("meera")["_facts"])
    assert anika["traits"][0]["detail"] == sc.LAGNA_PLAIN["Taurus"]
    assert anika["headline"] != meera["headline"]
    assert [a["tone"] for a in anika["areas"]] == [_signals("anika")["tones"][k] for k in
                                                    ("work", "relationships", "money", "energy")]
    assert "Rahu period until" in anika["chapter"]


# ── The agent ───────────────────────────────────────────────────────────────

def test_a_clean_story_is_returned_first_time():
    agent = _Scripted([_story()])
    assert agent.write(_signals()) is not None and len(agent.prompts) == 1


def test_the_prompt_carries_the_shared_simple_english_rule():
    from astrospace.agents.style import PLAIN_INDIAN_ENGLISH
    assert sa.SYSTEM.endswith(PLAIN_INDIAN_ENGLISH)


@pytest.mark.parametrize("line", [
    "You will die young.",
    "You will get diabetes.",
])
def test_a_boundary_is_retried_then_dropped(line):
    agent = _Scripted([_story(detail=line), _story(detail=line)])
    assert agent.write(_signals()) is None
    assert "boundary" in agent.prompts[1]


def test_a_rule_id_that_was_not_given_is_sent_back():
    agent = _Scripted([_story(rules=["bphs4_lagna_taurus", "bphs_made_up_rule", "uk4_tenth_bhava_scope"]), _story()])
    assert "bphs_made_up_rule" not in agent.write(_signals()).rules_used
    assert "bphs_made_up_rule" in agent.prompts[1]


def test_astrology_words_in_a_trait_ask_for_plain_words():
    jargon = _story(detail="Your Moon in Sagittarius and your lagna lord make you calm.")
    agent = _Scripted([jargon, _story()])
    agent.write(_signals())
    assert "plain words in the trait" in agent.prompts[1]


def test_the_chapter_must_name_the_running_period():
    vague = _story(chapter="This is a time for faith and travel.")
    agent = _Scripted([vague, vague])
    assert agent.write(_signals()) is vague
    assert "Rahu period" in agent.prompts[1]


def test_the_model_cannot_set_a_badge():
    payload = sa.to_payload(_story(), _signals("ravi"))
    assert [a["tone"] for a in payload["areas"]] == ["gentle", "gentle", "steady", "gentle"]
    assert payload["areas"][0]["title"] == "Work & purpose"


# ── Store and endpoint ──────────────────────────────────────────────────────

@pytest.fixture()
def env(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine)

    def override_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    with factory() as db:
        kundli_id = crud.create_kundli(db, {
            "user_id": ME, "name": "Anika", "relation": "self", "birth_year": 1990, "birth_month": 5,
            "birth_day": 15, "birth_hour": 6, "birth_minute": 30, "birth_city": "Hyderabad", "birth_nation": "IN",
        }).id
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[current_user] = lambda: AuthUser(id=ME, role="dev")
    try:
        yield TestClient(app), kundli_id, factory
    finally:
        app.dependency_overrides.clear()


class _Counting:
    def __init__(self, story=None, fail=False):
        self.calls, self.story, self.fail = 0, story, fail

    def __call__(self):
        outer = self

        class Agent:
            def write(self, signals):
                outer.calls += 1
                if outer.fail:
                    raise RuntimeError("API key not valid")
                return outer.story

            def usage_totals(self):
                return {"provider": "gemini", "model": "stub", "calls": 1,
                        "input_tokens": 3000, "output_tokens": 900}

        return Agent()


@pytest.fixture()
def agent(monkeypatch):
    counting = _Counting(_story())
    original = store.ensure_story

    def ensure(*args, **kw):
        kw.setdefault("agent_factory", counting)
        return original(*args, **kw)

    monkeypatch.setattr(store, "ensure_story", ensure)
    return counting


def test_written_once_then_served_from_the_store(env, agent):
    http, kundli_id, factory = env
    first = http.get(f"/api/v1/vedic/{kundli_id}/story").json()
    again = http.get(f"/api/v1/vedic/{kundli_id}/story").json()
    assert first["source"] == "agent" and first["cached"] is False
    assert first["story"]["headline"].startswith("Calm, warm")
    assert again["cached"] is True and again["story"] == first["story"]
    assert agent.calls == 1
    with factory() as db:
        assert db.query(LifeStory).one().user_id == ME


def test_editing_a_birth_time_is_a_new_story(env, agent):
    http, kundli_id, factory = env
    http.get(f"/api/v1/vedic/{kundli_id}/story")
    with factory() as db:
        crud.update_kundli(db, kundli_id, {"birth_minute": 35}, ME)
    http.get(f"/api/v1/vedic/{kundli_id}/story")
    assert agent.calls == 2


def test_a_failure_serves_the_code_backup_and_stores_nothing(env, agent):
    http, kundli_id, factory = env
    agent.fail = True
    body = http.get(f"/api/v1/vedic/{kundli_id}/story").json()
    assert body["source"] == "template"
    assert body["story"]["traits"][0]["detail"] == sc.LAGNA_PLAIN["Taurus"]
    with factory() as db:
        assert db.query(LifeStory).count() == 0


def test_the_daily_ceiling_falls_back_to_the_backup(env, agent, monkeypatch):
    http, kundli_id, _factory = env
    monkeypatch.setattr(store, "DAILY_WRITE_CEILING", 0)
    assert http.get(f"/api/v1/vedic/{kundli_id}/story").json()["source"] == "template"
    assert agent.calls == 0


def test_switched_off(env, agent, monkeypatch):
    http, kundli_id, _factory = env
    monkeypatch.setenv("LIFE_STORY_AGENT", "off")
    assert http.get(f"/api/v1/vedic/{kundli_id}/story").json()["source"] == "template"
    assert agent.calls == 0


def test_another_readers_profile_is_not_found(env, agent):
    http, kundli_id, _factory = env
    app.dependency_overrides[current_user] = lambda: AuthUser(id="someone-else", role="dev")
    assert http.get(f"/api/v1/vedic/{kundli_id}/story").status_code == 404
    assert agent.calls == 0
