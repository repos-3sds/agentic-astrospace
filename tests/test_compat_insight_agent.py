"""Agent-written "About you two" section of the full compatibility report.

The model is stubbed: these tests pin what the reader is promised (facts the
kootas never use reach the model, nothing crosses a boundary, one section per
pair written once and kept, the fixed guidance whenever it cannot be written),
not what a model happens to write.
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from astrospace.agents import compat_insight_agent as cia
from astrospace.api.auth import AuthUser, current_user
from astrospace.context import compat_insight_store as store
from astrospace.core.vedic import VedicChart
from astrospace.core.vedic.compatibility import gun_milan
from astrospace.db import crud, get_db
from astrospace.db.database import Base
from astrospace.db.models import CompatibilityInsight
from main import app

ME = "compat-reader"
AS_OF = datetime(2026, 10, 20, tzinfo=timezone.utc)


def _charts():
    return (VedicChart("Ravi Kumar", 1991, 3, 14, 6, 40, "Hyderabad", "IN"),
            VedicChart("Meera", 1993, 8, 22, 21, 15, "Chennai", "IN"))


def _insight(rules: list[str] | None = None, detail: str = "You both meet new people in a soft, caring way.") -> cia.CoupleInsight:
    return cia.CoupleInsight(
        headline="Same way of seeing life, different speed",
        summary="Ravi and Meera, you start from the same place. Ravi speaks fast and Meera keeps things inside.",
        bond=[cia.InsightItem(title="You face life the same way", detail=detail),
              cia.InsightItem(title="Home plans line up", detail="You usually want the same things for the house.")],
        care=[cia.CareItem(title="How you each react", detail="Ravi is quick; Meera goes quiet when hurt.",
                           step="When a talk gets heated, Ravi stops first.")],
        each=[cia.PersonNote(name="Ravi", how_they_care="Ravi shows care by doing.", what_helps="Ask him one direct question."),
              cia.PersonNote(name="Meera", how_they_care="Meera shows care through warmth.", what_helps="Thank her out loud.")],
        this_period="Ravi is in a Jupiter period until 2027 and Meera in a steady Saturn period.",
        rules_used=rules or ["bphs_seventh_kalatra", "bphs_venus_karaka_seventh"],
    )


class _Scripted(cia.CompatInsightAgent):
    def __init__(self, drafts):
        self.provider, self.model, self.usage_log = "gemini", "stub", []
        self.queue, self.prompts = list(drafts), []

    def run_structured(self, messages, schema, tool_name="deliver_result", input_schema=None):
        self.prompts.append(messages[0]["content"])
        return self.queue.pop(0)


# ── What the model is given ─────────────────────────────────────────────────

def test_the_input_carries_what_the_kootas_never_use():
    a, b = _charts()
    signals = cia.insight_input(a, b, gun_milan(a, b), "married", AS_OF)
    ravi, meera = signals["people"]
    assert ravi["name"] == "Ravi" and meera["name"] == "Meera"
    assert ravi["rising_sign"] == "Pisces"
    assert ravi["seventh_house"] == {"sign": "Virgo", "lord": "Mercury",
                                     "lord_sits": {"sign": "Pisces", "house": 1, "dignity": "Debilitated"},
                                     "planets_in_it": []}
    assert set(meera["seventh_house"]["planets_in_it"]) == {"Mars", "Jupiter"}
    assert ravi["venus"]["house"] == 2 and meera["venus"]["sign"] == "Cancer"
    assert ravi["running_period"]["mahadasha"] == {"lord": "Jupiter", "ends": "2027-12-07"}
    assert meera["running_period"]["antardasha"]["lord"] == "Venus"
    assert len(signals["kootas"]) == 8 and signals["stage"] == "married"


def test_each_person_gets_only_the_classical_rules_their_chart_meets():
    ravi, meera = _signals()["people"]
    ravi_ids = [rule["id"] for rule in ravi["classical_rules"]]
    meera_ids = [rule["id"] for rule in meera["classical_rules"]]
    # Ravi's 7th lord Mercury is debilitated in his 1st; nothing sits in his 7th.
    assert "bphs18_4_seventh_lord_strength" in ravi_ids
    assert "bphs18_16_malefic_on_seventh" not in ravi_ids
    # Meera has Mars in her 7th and is running a Venus sub-period.
    assert {"bphs18_16_malefic_on_seventh", "phal10_malefic_seventh_harm"} <= set(meera_ids)
    assert "phal10_marriage_dasha_timing" in meera_ids
    # Neither 7th lord sits in a dusthana, the 7th or the 8th.
    for ids in (ravi_ids, meera_ids):
        assert not {"bphs18_2_seventh_lord_dusthana", "bphs24_79_seventh_lord_in_seventh",
                    "bphs24_80_seventh_lord_in_eighth"} & set(ids)
    malefic = next(r for r in meera["classical_rules"] if r["id"] == "bphs18_16_malefic_on_seventh")
    assert malefic["applies_because"] == "Mars in the 7th house" and "Never as harm" in malefic["read_as"]


def test_every_picked_rule_is_a_stored_marriage_reference():
    from astrospace.context.kb import get_knowledge_base
    stored = {ref.ref_id: ref.statement for ref in get_knowledge_base().retrieve(["marriage"], limit=100)}
    for person in _signals()["people"]:
        for rule in person["classical_rules"]:
            assert stored[rule["id"]] == rule["rule"]


@pytest.mark.parametrize("house,dignity,expected", [
    (8, "Neutral", {"bphs18_2_seventh_lord_dusthana", "bphs24_80_seventh_lord_in_eighth", "bphs18_4_seventh_lord_strength"}),
    (7, "Own", {"bphs24_79_seventh_lord_in_seventh", "bphs18_4_seventh_lord_strength"}),
    (12, "Exalted", {"bphs18_2_seventh_lord_dusthana", "bphs18_4_seventh_lord_strength"}),
])
def test_the_seventh_lord_placement_picks_its_rule(house, dignity, expected):
    from astrospace.agents.compat_classics import classical_rules
    planets = {"Venus": {"sign": "Taurus", "house": 3}, "Jupiter": {"sign": "Leo", "house": 6},
               "Saturn": {"sign": "Aries", "house": house}}
    rules = classical_rules(planets, {"Saturn": {"dignity": dignity}}, "Saturn", {}, {})
    ids = {rule["id"] for rule in rules}
    assert expected <= ids
    # A 7th lord in the 12th is weak whatever its sign dignity.
    if house == 12:
        assert "weak" in next(r for r in rules if r["id"] == "bphs18_4_seventh_lord_strength")["applies_because"]


def test_strong_seventh_lord_in_jupiters_aspect_adds_phaladeepika():
    from astrospace.agents.compat_classics import classical_rules
    planets = {"Venus": {"sign": "Taurus", "house": 2}, "Jupiter": {"sign": "Aries", "house": 1},
               "Mars": {"sign": "Libra", "house": 7}}
    ids = {r["id"] for r in classical_rules(planets, {"Mars": {"dignity": "Own"}}, "Mars", {}, {})}
    assert "phal10_strong_seventh_lord_marriage" in ids and "bphs24_79_seventh_lord_in_seventh" in ids
    # Mars is the 7th lord in its own house, not a malefic sitting on the 7th.
    assert "bphs18_16_malefic_on_seventh" not in ids


def _upapada_case(**signs):
    """Aries rising, Jupiter in Taurus: the Upapada falls in Cancer. Everything
    else sits in Gemini or Sagittarius, from where nothing aspects Cancer."""
    from astrospace.agents.compat_classics import upapada_facts
    at = {"Sun": 2, "Moon": 2, "Mars": 2, "Mercury": 2, "Jupiter": 1, "Venus": 2,
          "Saturn": 2, "Rahu": 2, "Ketu": 8, **signs}
    positions = {name: {"lon": sign * 30 + 10.0} for name, sign in at.items()}
    return upapada_facts(0, positions, {})


def _ids(rules):
    return {rule["id"] for rule in rules}


def test_a_benefic_in_the_upapada_picks_bphs_and_uttara_kalamritam():
    from astrospace.agents.compat_classics import classical_rules
    facts = _upapada_case(Venus=3)
    assert facts["upapada"]["sign"] == "Cancer" and facts["upapada"]["benefic_in"] == ["Venus"]
    ids = _ids(classical_rules({}, {}, "Venus", {}, {}, upapada=facts))
    assert {"bphs30_1_upapada_benefic", "uk4_39_upapada_benefic_character"} <= ids
    assert "bphs30_4_upapada_malefic" not in ids


def test_a_malefic_on_the_upapada_goes_out_softened_and_a_benefic_eases_it():
    from astrospace.agents.compat_classics import classical_rules
    strained = classical_rules({}, {}, "Venus", {}, {}, upapada=_upapada_case(Saturn=3))
    rule = next(r for r in strained if r["id"] == "bphs30_4_upapada_malefic")
    assert rule["applies_because"] == "Upapada in Cancer with Saturn"
    assert "Never as being without a partner" in rule["read_as"]
    eased = _ids(classical_rules({}, {}, "Venus", {}, {}, upapada=_upapada_case(Saturn=3, Venus=3)))
    assert "bphs30_5_upapada_benefic_relief" in eased and "bphs30_4_upapada_malefic" not in eased


def test_an_exalted_or_friendly_sun_is_no_malefic_on_the_upapada():
    from astrospace.agents.compat_classics import upapada_facts
    positions = {name: {"lon": sign * 30 + 10.0} for name, sign in
                 {"Sun": 3, "Moon": 2, "Mars": 2, "Mercury": 2, "Jupiter": 1, "Venus": 2,
                  "Saturn": 2, "Rahu": 2, "Ketu": 8}.items()}
    assert upapada_facts(0, positions, {"Sun": {"dignity": "Neutral"}})["upapada"]["malefic_on"] == ["Sun"]
    assert upapada_facts(0, positions, {"Sun": {"dignity": "Friend"}})["upapada"]["malefic_on"] == []


def test_the_real_pair_meets_its_upapada_and_navamsa_rules():
    ravi, meera = _signals()["people"]
    ravi_ids, meera_ids = _ids(ravi["classical_rules"]), _ids(meera["classical_rules"])
    # Ravi: Upapada Sagittarius in Mars's aspect; its lord Jupiter exalted in Cancer.
    assert ravi["upapada"]["sign"] == "Sagittarius" and ravi["upapada"]["lord"]["dignity"] == "Exalted"
    assert {"bphs30_4_upapada_malefic", "bphs30_14_upapada_lord_exalted"} <= ravi_ids
    # Both have Venus vargottama; Meera runs a Venus sub-period on it.
    for person, ids in ((ravi, ravi_ids), (meera, meera_ids)):
        assert person["navamsa"]["venus"]["vargottama"]
        assert {"bphs7_navamsa_for_spouse", "phal9_vargottama_own_house"} <= ids
    assert "phal20_vargottama_dasha_favourable" in meera_ids
    assert "phal20_vargottama_dasha_favourable" not in ravi_ids


def test_upapada_rules_state_their_convention():
    import json
    from pathlib import Path
    refs = json.loads(Path("astrospace/context/references.json").read_text(encoding="utf-8"))["references"]
    upapada = [ref for ref in refs if "upapada" in ref["ref_id"]]
    assert len(upapada) == 7
    assert all(ref["status"] == "convention_dependent" and "12th house" in ref["observance_note"]
               for ref in upapada)


def test_upapada_and_navamsa_words_never_reach_the_reader():
    assert set(cia.plain_words_jargon("Your Upapada and Navamsha are vargottama")) >= {"upapada", "navamsha", "vargottama"}


def test_kootas_carry_their_standard_meaning():
    kootas = _signals()["kootas"]
    assert all(row.get("meaning") for row in kootas)


def test_a_rule_id_that_was_not_given_is_sent_back():
    agent = _Scripted([_insight(rules=["bphs_seventh_kalatra", "bphs_made_up_rule"]), _insight()])
    assert agent.write(_signals()).rules_used == ["bphs_seventh_kalatra", "bphs_venus_karaka_seventh"]
    assert "bphs_made_up_rule" in agent.prompts[1]


def test_the_prompt_carries_the_shared_simple_english_rule():
    from astrospace.agents.style import PLAIN_INDIAN_ENGLISH
    assert cia.SYSTEM.endswith(PLAIN_INDIAN_ENGLISH)


# ── The agent ───────────────────────────────────────────────────────────────

def _signals():
    a, b = _charts()
    return cia.insight_input(a, b, gun_milan(a, b), "married", AS_OF)


def test_a_clean_section_is_returned_first_time():
    agent = _Scripted([_insight()])
    assert agent.write(_signals()) is not None and len(agent.prompts) == 1


@pytest.mark.parametrize("line", [
    "You two are not compatible.",
    "This match may end in divorce.",
    "You should not marry.",
])
def test_a_relationship_verdict_is_retried_then_dropped(line):
    agent = _Scripted([_insight(detail=line), _insight(detail=line)])
    assert agent.write(_signals()) is None
    assert "boundary" in agent.prompts[1]


def test_a_verdict_is_rewritten_when_the_retry_is_clean():
    agent = _Scripted([_insight(detail="You will divorce."), _insight()])
    assert agent.write(_signals()) is not None


def test_matching_terms_count_as_jargon_but_everyday_words_do_not():
    assert cia.plain_words_jargon("Strong Bhakoot, weak Gana") == ["bhakoot", "gana"]
    assert cia.plain_words_jargon("A garden of manners and balance") == []


def test_jargon_in_the_headline_asks_for_plain_words():
    jargon = _insight().model_copy(update={"headline": "Strong Bhakoot, weak Gana"})
    agent = _Scripted([jargon, _insight()])
    assert agent.write(_signals()).headline.startswith("Same way")
    assert "headline in plain words" in agent.prompts[1]


def test_a_missing_name_is_sent_back_once_then_kept_as_the_safe_draft():
    nameless = _insight().model_copy(update={
        "summary": "You start from the same place.", "headline": "Same outlook",
        "each": [cia.PersonNote(name="Ravi", how_they_care="Shows care by doing.", what_helps="Ask directly."),
                 cia.PersonNote(name="Partner", how_they_care="Shows care with warmth.", what_helps="Say thanks.")],
        "care": [cia.CareItem(title="How you react", detail="One is quick, one goes quiet.", step="Pause first.")],
        "this_period": "One of you is busy until 2027; the other is steady.",
    })
    agent = _Scripted([nameless, nameless])
    assert agent.write(_signals()) is nameless
    assert "Meera by name" in agent.prompts[1]


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
        ids = [crud.create_kundli(db, {
            "user_id": ME, "name": name, "relation": relation,
            "birth_year": y, "birth_month": m, "birth_day": d, "birth_hour": h, "birth_minute": mi,
            "birth_city": city, "birth_nation": "IN",
        }).id for name, relation, y, m, d, h, mi, city in (
            ("Ravi Kumar", "self", 1991, 3, 14, 6, 40, "Hyderabad"),
            ("Meera", "spouse", 1993, 8, 22, 21, 15, "Chennai"),
        )]
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[current_user] = lambda: AuthUser(id=ME, role="dev")
    try:
        yield TestClient(app), ids, factory
    finally:
        app.dependency_overrides.clear()


class _Counting:
    def __init__(self, insight=None, fail=False):
        self.calls, self.insight, self.fail, self.signals = 0, insight, fail, []

    def __call__(self):
        outer = self

        class Agent:
            def write(self, signals):
                outer.calls += 1
                outer.signals.append(signals)
                if outer.fail:
                    raise RuntimeError("API key not valid")
                return outer.insight

            def usage_totals(self):
                return {"provider": "gemini", "model": "stub", "calls": 1,
                        "input_tokens": 2500, "output_tokens": 900}

        return Agent()


@pytest.fixture()
def agent(monkeypatch):
    counting = _Counting(_insight())
    original = store.ensure_insight

    def ensure(*args, **kw):
        kw.setdefault("agent_factory", counting)
        return original(*args, **kw)

    monkeypatch.setattr(store, "ensure_insight", ensure)
    return counting


def _url(ids, **params):
    return f"/api/v1/vedic/{ids[0]}/compatibility/{ids[1]}/insight", params


def test_written_once_then_served_from_the_store(env, agent):
    http, ids, factory = env
    url, params = _url(ids)
    first = http.get(url, params=params).json()
    again = http.get(url, params=params).json()
    assert first["source"] == "agent" and first["cached"] is False
    assert first["insight"]["headline"].startswith("Same way")
    assert again["cached"] is True and again["insight"] == first["insight"]
    assert agent.calls == 1
    with factory() as db:
        row = db.query(CompatibilityInsight).one()
        assert row.user_id == ME and row.stage == "married"


def test_planning_is_its_own_section(env, agent):
    http, ids, _factory = env
    url, _ = _url(ids)
    http.get(url, params={"stage": "married"})
    planning = http.get(url, params={"stage": "planning"}).json()
    assert planning["stage"] == "planning" and agent.calls == 2
    assert agent.signals[1]["stage"] == "planning"


def test_editing_a_birth_time_is_a_new_section(env, agent):
    http, ids, factory = env
    url, params = _url(ids)
    http.get(url, params=params)
    with factory() as db:
        crud.update_kundli(db, ids[1], {"birth_minute": 20}, ME)
    http.get(url, params=params)
    assert agent.calls == 2


def test_a_failure_is_not_stored_and_the_fixed_guidance_stays(env, agent):
    http, ids, factory = env
    agent.fail = True
    url, params = _url(ids)
    for _ in range(2):
        body = http.get(url, params=params).json()
        assert body == {"source": "template", "insight": None}
    assert agent.calls == 2
    with factory() as db:
        assert db.query(CompatibilityInsight).count() == 0


def test_the_daily_ceiling_stops_new_writes(env, agent, monkeypatch):
    http, ids, _factory = env
    monkeypatch.setattr(store, "DAILY_WRITE_CEILING", 1)
    url, _ = _url(ids)
    assert http.get(url, params={"stage": "married"}).json()["source"] == "agent"
    assert http.get(url, params={"stage": "planning"}).json()["source"] == "template"
    # A stored section is still served past the ceiling.
    assert http.get(url, params={"stage": "married"}).json()["cached"] is True
    assert agent.calls == 1


def test_switched_off(env, agent, monkeypatch):
    http, ids, _factory = env
    monkeypatch.setenv("COMPAT_INSIGHT_AGENT", "off")
    url, params = _url(ids)
    assert http.get(url, params=params).json() == {"source": "template", "insight": None}
    assert agent.calls == 0


def test_another_readers_profiles_are_not_found(env, agent):
    http, ids, _factory = env
    app.dependency_overrides[current_user] = lambda: AuthUser(id="someone-else", role="dev")
    url, params = _url(ids)
    assert http.get(url, params=params).status_code == 404
    assert agent.calls == 0


def test_free_plan_gets_no_section_when_locks_are_on(env, agent, monkeypatch):
    http, ids, _factory = env
    monkeypatch.setenv("ASTROSPACE_QUOTAS_ENFORCED", "1")
    monkeypatch.delenv("ASTROSPACE_TESTERS_GET_PLUS", raising=False)
    url, params = _url(ids)
    assert http.get(url, params=params).json() == {"source": "locked", "insight": None}
    assert agent.calls == 0
