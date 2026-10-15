"""The legacy /api/v1 LLM routes (reading, horoscope, compatibility, transits)
must not be callable without a signed-in user.

They call a language model on every request, so leaving them open let anyone
spend the provider budget, and their output skips the Ask safety gate. These
tests pin the boundary without making a provider call: auth runs first.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from astrospace.api.routes import router

PERSON = {
    "name": "A", "year": 1990, "month": 3, "day": 15, "hour": 8, "minute": 30,
    "city": "Hyderabad", "nation": "IN",
}
LLM_ROUTES = [
    ("/api/v1/reading", PERSON),
    ("/api/v1/transits", PERSON),
    ("/api/v1/horoscope", {"sun_sign": "Aries"}),
    ("/api/v1/compatibility", {"person1": PERSON, "person2": PERSON}),
]


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _clear(monkeypatch):
    for key in ("SUPABASE_URL", "SUPABASE_ANON_KEY", "ASTROSPACE_DEV_AUTH_BYPASS", "K_SERVICE"):
        monkeypatch.delenv(key, raising=False)


@pytest.mark.parametrize("path,body", LLM_ROUTES)
def test_llm_routes_need_a_bearer_token(client, monkeypatch, path, body):
    _clear(monkeypatch)
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key-value")

    response = client.post(path, json=body)

    assert response.status_code == 401


@pytest.mark.parametrize("path,body", LLM_ROUTES)
def test_llm_routes_refuse_when_cloud_run_has_no_auth_config(client, monkeypatch, path, body):
    _clear(monkeypatch)
    monkeypatch.setenv("K_SERVICE", "agentic-astrospace")

    response = client.post(path, json=body)

    assert response.status_code == 503
