"""Agent-written daily brief: coverage, spoken length, boundaries, the store
and the schedule.

The model is stubbed: these tests pin what the app is promised (every area
the templated brief covered, a script that plays in under 90 s at 0.9x,
nothing that crosses a boundary, one brief per profile per day written on a
schedule and kept), not what a model happens to write.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from astrospace.agents import daily_brief_agent as dba
from astrospace.context import daily_brief_store as store
from astrospace.api.auth import AuthUser, current_user
from astrospace.db import crud, get_db
from astrospace.db.database import Base
from astrospace.db.models import DailyGuidanceCache, PushToken
from astrospace.notifications import daily_briefs
from main import app

ME = "brief-reader"
AS_OF = "2026-10-16T08:00:00+05:30"
# Rahu Kalam and Abhijit for the test day and place, from the engine.
RAHU, ABHIJIT = "10:24", "11:29"


def _brief(spoken_words_each: int = 30, avoid_detail: str = "Ketu from the Moon asks for rest.",
           timing: str = "Keep 10:24–11:52 for routine work; start fresh things in 11:29–12:16.") -> dba.DailyBrief:
    words = " ".join(["word"] * (spoken_words_each - 1)) + "."
    return dba.DailyBrief(
        headline="A day for finishing things",
        summary="Steady ground for closing open loops.",
        narrative="Your tara favours finishing. The Moon is settled. Jupiter supports you.",
        practical_close="Finish one real task before noon.",
        focus="Finish the task you have been circling.",
        energy="vibrant",
        areas=dba.LifeAreas(love="Say the kind thing.", money="Plan, don't spend.",
                            work="Take the initiative.", health="Rest well tonight.",
                            growth="Read something that stretches you."),
        do=[dba.BriefItem(headline="Close an open task", detail="Sadhaka tara favours completion."),
            dba.BriefItem(headline="Plan your money", detail="Guru Bala from the Moon is active."),
            dba.BriefItem(headline="Take initiative at work", detail="Your Ketu period favours it.")],
        avoid=[dba.BriefItem(headline="Overextending yourself", detail=avoid_detail)],
        timing_note=timing,
        why=["Your tara today is an accomplishment star.", "The Moon is in a good house for you."],
        spoken=[dba.SpokenSection(label=label, text=f"{label}: {words}")
                for label in ("Opening", "Overview", "Today", "Why", "Close")],
    )


def _payload() -> dict:
    from astrospace.context import daily_guidance
    from astrospace.core.vedic import VedicChart

    chart = VedicChart("Reader", 1991, 8, 14, 6, 12, "Vijayawada", "IN")
    return daily_guidance(chart, relation="self",
                          as_of=datetime(2026, 10, 16, 8, 0, tzinfo=ZoneInfo("Asia/Kolkata")))


class _Scripted(dba.DailyBriefAgent):
    """Returns the queued briefs in order and records the prompts."""

    def __init__(self, briefs):
        self.provider, self.model, self.usage_log = "gemini", "stub", []
        self.queue, self.prompts = list(briefs), []

    def run_structured(self, messages, schema, tool_name="deliver_result", input_schema=None):
        self.prompts.append(messages[0]["content"])
        self.usage_log.append({"purpose": tool_name, "input_tokens": 3000, "output_tokens": 600})
        return self.queue.pop(0)


def _write(agent, **kw):
    return agent.write(_payload(), first_name="Reader", date_label="Friday, 16 October", **kw)


# ── The agent ──────────────────────────────────────────────────────────────

def test_word_limit_plays_under_ninety_seconds_at_the_sheets_default_speed():
    assert dba.listen_seconds(dba.SPOKEN_WORD_LIMIT) < 90
    assert dba.listen_seconds(dba.SPOKEN_WORD_TARGET[1]) < 90


def test_the_brief_has_every_area_the_template_had():
    fields = set(dba.DailyBrief.model_fields)
    # verdict + narrative, summary, focus, energy, do/avoid, timing, reasons
    assert {"headline", "narrative", "practical_close", "summary", "focus", "energy",
            "do", "avoid", "timing_note", "why", "areas", "spoken"} <= fields
    # the template's relationship/money/work tones and its five life domains
    assert set(dba.LifeAreas.model_fields) == {"love", "money", "work", "health", "growth"}


def test_a_complete_brief_within_the_limit_is_returned_first_time():
    agent = _Scripted([_brief(30)])
    brief = _write(agent)
    assert brief is not None and dba.spoken_words(brief) == 150
    assert len(agent.prompts) == 1


def test_a_missing_window_time_is_sent_back_once():
    agent = _Scripted([_brief(30, timing="Go gently around midday."), _brief(30)])
    brief = _write(agent)
    assert RAHU in brief.timing_note
    assert "Rahu Kalam time" in agent.prompts[1] and "Abhijit" in agent.prompts[1]


def test_coverage_gaps_names_what_is_missing():
    payload = _payload()
    assert dba.coverage_gaps(_brief(30), payload) == []
    thin = _brief(30, timing="Midday is fine.").model_copy(update={"do": _brief(30).do[:1]})
    gaps = dba.coverage_gaps(thin, payload)
    assert any("Rahu Kalam" in gap for gap in gaps)
    assert any("do item per do candidate" in gap for gap in gaps)


def test_chandrashtama_must_be_named(monkeypatch):
    payload = _payload()
    payload = {**payload, "chandrabala": {**payload["chandrabala"], "chandrashtama": True}}
    no_moon = _brief(30, avoid_detail="Go easy.").model_copy(update={"why": ["Your tara is good.", "Transits help."]})
    assert any("chandrashtama" in gap for gap in dba.coverage_gaps(no_moon, payload))


def test_a_long_script_is_rewritten_with_its_word_count():
    agent = _Scripted([_brief(50), _brief(30)])
    brief = _write(agent)
    assert dba.spoken_words(brief) == 150
    assert "was 250 words" in agent.prompts[1]


def test_a_script_still_long_after_the_rewrite_is_trimmed_not_shipped_long():
    agent = _Scripted([_brief(50), _brief(48)])
    brief = _write(agent)
    assert brief is not None
    assert dba.spoken_words(brief) <= dba.SPOKEN_WORD_LIMIT
    labels = [section.label for section in brief.spoken]
    assert labels[0] == "Opening" and labels[-1] == "Close"


def test_a_boundary_crossing_brief_is_retried_then_dropped():
    bad = "This dosha will destroy your marriage."
    agent = _Scripted([_brief(30, avoid_detail=bad), _brief(30, avoid_detail=bad)])
    assert _write(agent) is None
    assert "crossed a boundary" in agent.prompts[1]


def test_the_model_sees_the_signals_and_the_place_not_kb_references_or_colours():
    agent = _Scripted([_brief(30)])
    _write(agent, mode="guided", tone="gentle", place="Vijayawada")
    prompt = agent.prompts[0]
    assert "Sadhaka" in prompt and "Rahu Kalam" in prompt and "Vijayawada" in prompt
    assert "narrative" in prompt and "do_candidates" in prompt
    assert "references" not in prompt and "lucky" not in prompt
    assert "new to astrology" in prompt and "gentle" in prompt


def test_audio_chunks_match_the_apps_split():
    short = "Namaste, Reader.  Here   is your day."
    assert daily_briefs.natural_chunks(short) == ["Namaste, Reader. Here is your day."]
    long = " ".join(f"Sentence number {i} is here." for i in range(80))
    chunks = daily_briefs.natural_chunks(long, max_chars=200)
    assert all(len(c) <= 200 for c in chunks) and " ".join(chunks) == " ".join(long.split())


# ── Store, endpoint and schedule ─────────────────────────────────────────────

@pytest.fixture()
def env():
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
        kundli = crud.create_kundli(db, {
            "user_id": ME, "name": "Reader Name", "relation": "self",
            "birth_year": 1991, "birth_month": 8, "birth_day": 14,
            "birth_hour": 6, "birth_minute": 12,
            "birth_city": "Vijayawada", "birth_nation": "IN",
        }).id
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[current_user] = lambda: AuthUser(id=ME, role="dev")
    try:
        yield TestClient(app), kundli, factory
    finally:
        app.dependency_overrides.clear()


class _Counting:
    """An agent factory whose agents return one fixed brief and count calls."""

    def __init__(self, brief=None, fail=False):
        self.calls, self.brief, self.fail = 0, brief, fail

    def __call__(self):
        outer = self

        class Agent:
            def write(self, payload, **kw):
                outer.calls += 1
                outer.last_kw = kw
                if outer.fail:
                    raise RuntimeError("API key not valid")
                return outer.brief

            def usage_totals(self):
                return {"provider": "gemini", "model": "stub", "calls": 1,
                        "input_tokens": 3000, "output_tokens": 600}

        return Agent()


@pytest.fixture()
def agent(monkeypatch):
    factory = _Counting(_brief(30))
    original = store.ensure_brief

    def ensure(*args, **kw):
        kw.setdefault("agent_factory", factory)
        return original(*args, **kw)

    monkeypatch.setattr(store, "ensure_brief", ensure)
    monkeypatch.setattr("astrospace.api.context_routes.ensure_brief", ensure)
    monkeypatch.setattr(daily_briefs, "ensure_brief", ensure)
    return factory


def test_on_open_writes_once_then_serves_the_stored_brief(env, agent):
    http, kundli, factory = env
    first = http.get(f"/api/v1/context/{kundli}/daily/brief", params={"as_of": AS_OF}).json()
    again = http.get(f"/api/v1/context/{kundli}/daily/brief", params={"as_of": AS_OF}).json()
    assert first["source"] == "agent" and first["cached"] is False
    assert first["trigger"] == "on_open" and first["listen_seconds"] < 90
    assert again["cached"] is True and again["brief"] == first["brief"]
    assert agent.calls == 1
    with factory() as db:
        assert db.query(DailyGuidanceCache).count() == 1
    # A different reading style is a different brief, written once too.
    http.get(f"/api/v1/context/{kundli}/daily/brief", params={"as_of": AS_OF, "tone": "direct"})
    http.get(f"/api/v1/context/{kundli}/daily/brief", params={"as_of": AS_OF, "tone": "direct"})
    assert agent.calls == 2


def test_a_failure_is_not_stored_and_the_template_stays(env, agent):
    http, kundli, factory = env
    agent.fail = True
    for _ in range(2):
        body = http.get(f"/api/v1/context/{kundli}/daily/brief", params={"as_of": AS_OF}).json()
        assert body["source"] == "template" and body["brief"] is None
    assert agent.calls == 2
    with factory() as db:
        assert db.query(DailyGuidanceCache).count() == 0


def test_editing_the_birth_details_is_a_new_brief(env, agent):
    http, kundli, factory = env
    http.get(f"/api/v1/context/{kundli}/daily/brief", params={"as_of": AS_OF})
    with factory() as db:
        crud.update_kundli(db, kundli, {"birth_minute": 13}, ME)
    http.get(f"/api/v1/context/{kundli}/daily/brief", params={"as_of": AS_OF})
    assert agent.calls == 2


def test_endpoint_can_be_switched_off(env, agent, monkeypatch):
    http, kundli, _factory = env
    monkeypatch.setenv("DAILY_BRIEF_AGENT", "off")
    body = http.get(f"/api/v1/context/{kundli}/daily/brief", params={"as_of": AS_OF}).json()
    assert body["source"] == "template" and body["brief"] is None and agent.calls == 0


def test_other_users_profiles_are_not_found(env):
    http, _kundli, _factory = env
    assert http.get("/api/v1/context/someone-else/daily/brief").status_code == 404


def _install_app(db, timezone_name="Asia/Kolkata"):
    db.add(PushToken(user_id=ME, provider="fcm", token="t-1", timezone=timezone_name))
    db.commit()


def test_the_schedule_writes_each_profile_once_in_the_readers_style(env, agent):
    http, kundli, factory = env
    now = datetime(2026, 10, 16, 0, 30, tzinfo=timezone.utc)  # 06:00 in Kolkata
    with factory() as db:
        _install_app(db)
        crud.upsert_user_settings(db, ME, {"tone": "direct", "experience_mode": "practitioner"})
        crud.create_kundli(db, {
            "user_id": ME, "name": "Asha", "relation": "mother",
            "birth_year": 1965, "birth_month": 2, "birth_day": 3, "birth_hour": 9, "birth_minute": 0,
            "birth_city": "Hyderabad", "birth_nation": "IN",
        })
        first = daily_briefs.schedule_daily_briefs(db, now=now, prerender=lambda spoken: 0)
        second = daily_briefs.schedule_daily_briefs(db, now=now, prerender=lambda spoken: 0)
    assert first["written"] == 2 and second == {**second, "written": 0, "already": 2}
    assert agent.calls == 2
    assert agent.last_kw["tone"] == "direct" and agent.last_kw["mode"] == "practitioner"

    # Today then reads the scheduled brief instead of writing one.
    body = http.get(f"/api/v1/context/{kundli}/daily/brief",
                    params={"timezone": "Asia/Kolkata", "tone": "direct", "mode": "practitioner"}).json()
    assert body["trigger"] == "scheduled" and body["cached"] is True
    assert agent.calls == 2


def test_the_schedule_prerenders_audio_only_for_natural_voice_readers(env, agent, monkeypatch):
    _http, _kundli, factory = env
    now = datetime(2026, 10, 16, 0, 30, tzinfo=timezone.utc)
    rendered = []
    monkeypatch.setenv("ASTROSPACE_TTS_BUCKET", "tts-bucket")
    with factory() as db:
        _install_app(db)
        monkeypatch.setattr(daily_briefs, "_natural_voice_allowed", lambda db, user_id: False)
        free = daily_briefs.schedule_daily_briefs(db, now=now, prerender=rendered.append)
        monkeypatch.setattr(daily_briefs, "_natural_voice_allowed", lambda db, user_id: True)
        plus = daily_briefs.schedule_daily_briefs(db, now=now, prerender=rendered.append)
        again = daily_briefs.schedule_daily_briefs(db, now=now, prerender=rendered.append)
    assert free["audio"] == 0 and plus["audio"] == 1 and again["audio"] == 0
    assert len(rendered) == 1 and rendered[0][0]["label"] == "Opening"


def test_the_schedule_stops_at_its_budget(env, agent):
    _http, _kundli, factory = env
    now = datetime(2026, 10, 16, 0, 30, tzinfo=timezone.utc)
    with factory() as db:
        _install_app(db)
        crud.create_kundli(db, {
            "user_id": ME, "name": "Asha", "relation": "mother",
            "birth_year": 1965, "birth_month": 2, "birth_day": 3, "birth_hour": 9, "birth_minute": 0,
            "birth_city": "Hyderabad", "birth_nation": "IN",
        })
        result = daily_briefs.schedule_daily_briefs(db, now=now, prerender=lambda s: 0, max_briefs=1)
    assert result["written"] == 1 and result["deferred"] == 1


def test_the_schedule_does_nothing_when_switched_off(env, agent, monkeypatch):
    _http, _kundli, factory = env
    monkeypatch.setenv("DAILY_BRIEF_AGENT", "off")
    with factory() as db:
        _install_app(db)
        result = daily_briefs.schedule_daily_briefs(db, prerender=lambda s: 0)
    assert result["written"] == 0 and agent.calls == 0
