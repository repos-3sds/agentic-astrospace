from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from astrospace.api import voice_routes
from astrospace.api.auth import AuthUser, current_user
from astrospace.db import get_db
from astrospace.db.database import Base
from astrospace.db.models import EntitlementOverride
from astrospace.entitlements.resolver import resolve_entitlements
from astrospace.voice import SpeechUnavailable, detect_language, set_synthesizer_for_tests, set_translator_for_tests
from astrospace.voice.tts import MAX_TEXT_BYTES, SPEAKING_RATE

USER = "voice-test-user"


class FakeSynthesizer:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def synthesize(self, text, language_code, voice_name, rate):
        self.calls.append((text, language_code, voice_name, rate))
        if self.fail:
            raise SpeechUnavailable("down")
        return b"ID3-fake-" + language_code.encode()


@pytest.fixture()
def env():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[current_user] = lambda: AuthUser(id=USER, email="v@example.test", role="authenticated")
    fake = FakeSynthesizer()
    set_synthesizer_for_tests(fake)
    voice_routes._usage.clear()
    try:
        yield TestClient(app), Session, fake
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(current_user, None)
        set_synthesizer_for_tests(None)


def _grant_natural_voice(Session):
    db = Session()
    snapshot = resolve_entitlements(db, USER)
    db.add(EntitlementOverride(
        billing_account_id=snapshot.account_id,
        entitlement_key="audio.natural_voice",
        value={"value": True}, reason="test", actor_user_id="test", revision=1,
        effective_at=datetime.utcnow() - timedelta(minutes=1),
    ))
    db.commit()
    db.close()


def test_free_reader_is_refused_with_upgrade_denial(env):
    client, _, fake = env
    response = client.post("/api/v1/voice/speech", json={"text": "Namaste."})
    assert response.status_code == 402
    assert response.json()["entitlement"] == "audio.natural_voice"
    assert fake.calls == []


def test_plus_reader_gets_mp3_in_detected_language_and_replays_hit_cache(env):
    client, Session, fake = env
    _grant_natural_voice(Session)

    english = client.post("/api/v1/voice/speech", json={"text": "Namaste, Hawk.  Here is your reading."})
    assert english.status_code == 200
    assert english.headers["content-type"] == "audio/mpeg"
    assert english.headers["x-speech-language"] == "en"
    assert english.headers["x-speech-cached"] == "0"
    assert "private" in english.headers["cache-control"]

    again = client.post("/api/v1/voice/speech", json={"text": "Namaste, Hawk. Here is your reading."})
    assert again.headers["x-speech-cached"] == "1"
    assert len(fake.calls) == 1, "whitespace-only differences must reuse the cached audio"

    telugu = client.post("/api/v1/voice/speech", json={"text": "నమస్తే హాక్. Tarabala అనుకూలంగా ఉంది."})
    assert telugu.headers["x-speech-language"] == "te"
    assert fake.calls[-1][1] == "te-IN"
    # Speed is applied on the device, so every request uses one fixed rate.
    assert {call[3] for call in fake.calls} == {SPEAKING_RATE}


def test_provider_outage_is_503_so_the_app_falls_back(env):
    client, Session, _ = env
    _grant_natural_voice(Session)
    set_synthesizer_for_tests(FakeSynthesizer(fail=True))
    assert client.post("/api/v1/voice/speech", json={"text": "Hello."}).status_code == 503


def test_overlong_text_and_daily_budget(env, monkeypatch):
    client, Session, _ = env
    _grant_natural_voice(Session)
    too_long = "తె" * (MAX_TEXT_BYTES // 6 + 10)  # under 4,500 chars, over the byte cap
    assert client.post("/api/v1/voice/speech", json={"text": too_long}).status_code == 413

    monkeypatch.setattr(voice_routes, "DAILY_CHAR_BUDGET", 12)
    assert client.post("/api/v1/voice/speech", json={"text": "Short one."}).status_code == 200
    assert client.post("/api/v1/voice/speech", json={"text": "Over budget."}).status_code == 429


def test_detect_language_uses_script_share():
    assert detect_language("Moon in Kanya; Tarabala is supportive.") == "en"
    assert detect_language("చంద్రుడు కన్యా రాశిలో ఉన్నాడు.") == "te"
    assert detect_language("") == "en"


BRIEF = [
    {"label": "Opening", "text": "Namaste, Hawk. Here is your reading for today."},
    {"label": "Close", "text": "Move with attention, and let the day stay simple."},
]


def test_telugu_brief_needs_natural_voice_and_is_cached(env):
    client, Session, _ = env
    calls = []

    def translator(system, prompt):
        calls.append(prompt)
        return '["నమస్తే Hawk. ఈ రోజు మీ reading ఇది.", "శ్రద్ధగా ముందుకు వెళ్ళండి, రోజును సరళంగా ఉంచండి."]'

    set_translator_for_tests(translator)
    try:
        assert client.post("/api/v1/voice/translate", json={"sections": BRIEF}).status_code == 402
        _grant_natural_voice(Session)

        response = client.post("/api/v1/voice/translate", json={"sections": BRIEF})
        assert response.status_code == 200
        body = response.json()
        assert body["language"] == "te"
        assert [s["label"] for s in body["sections"]] == ["Opening", "Close"]
        assert detect_language(body["sections"][0]["text"]) == "te"

        assert client.post("/api/v1/voice/translate", json={"sections": BRIEF}).status_code == 200
        assert len(calls) == 1, "the same brief must not be translated twice"
    finally:
        set_translator_for_tests(None)


@pytest.mark.parametrize("reply", [
    "Sorry, I can't.",                                  # no JSON
    '["only one section"]',                             # wrong count
    '["మీరు ఈ సంవత్సరం చనిపోతారు.", "సరే."]',          # fails the output checks
])
def test_bad_or_unsafe_translation_falls_back_to_english(env, reply):
    client, Session, _ = env
    _grant_natural_voice(Session)

    def boom(system, prompt):
        raise RuntimeError("quota")

    for translator in (lambda system, prompt: reply, boom):
        set_translator_for_tests(translator)
        try:
            assert client.post("/api/v1/voice/translate", json={"sections": BRIEF}).status_code == 503
        finally:
            set_translator_for_tests(None)
