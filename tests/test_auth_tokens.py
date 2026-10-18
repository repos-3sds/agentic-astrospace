"""Local verification of Supabase access tokens (security audit S9)."""
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException

from astrospace.api import auth

URL = "https://example.supabase.co"


@pytest.fixture()
def keys(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", URL)
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon")
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
    private = ec.generate_private_key(ec.SECP256R1())

    class Key:
        key = private.public_key()

    class Client:
        def get_signing_key_from_jwt(self, token):
            return Key()

    monkeypatch.setattr(auth, "_jwks_client", lambda: Client())
    calls = []
    monkeypatch.setattr(auth._http, "get", lambda *a, **k: calls.append(a) or (_ for _ in ()).throw(AssertionError("no remote call expected")))
    auth._remote_cache.clear()
    return private, calls


def _token(private, **overrides):
    claims = {
        "sub": "user-1", "email": "a@example.test", "role": "authenticated",
        "aud": "authenticated", "iss": f"{URL}/auth/v1", "exp": int(time.time()) + 600,
    }
    claims.update(overrides)
    return jwt.encode(claims, private, algorithm="ES256", headers={"kid": "k1"})


def test_a_signed_token_is_accepted_without_calling_supabase(keys):
    private, calls = keys
    user = auth.verify_access_token(_token(private))
    assert (user.id, user.email, user.role, user.auth_enabled) == ("user-1", "a@example.test", "authenticated", True)
    assert calls == []


@pytest.mark.parametrize("token", ["junk", "a.b.c", ""])
def test_junk_is_refused_without_a_network_call(keys, token):
    with pytest.raises(HTTPException) as err:
        auth.verify_access_token(token)
    assert err.value.status_code == 401
    assert keys[1] == []


@pytest.mark.parametrize("overrides", [
    {"exp": int(time.time()) - 3600},
    {"aud": "anon"},
    {"iss": "https://evil.example/auth/v1"},
])
def test_expired_or_foreign_tokens_are_refused(keys, overrides):
    with pytest.raises(HTTPException) as err:
        auth.verify_access_token(_token(keys[0], **overrides))
    assert err.value.status_code == 401


def test_a_token_signed_by_another_key_is_refused(keys):
    other = ec.generate_private_key(ec.SECP256R1())
    with pytest.raises(HTTPException):
        auth.verify_access_token(_token(other))


def test_hs256_uses_the_secret_when_set(monkeypatch, keys):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "s" * 40)
    token = jwt.encode({
        "sub": "user-2", "aud": "authenticated", "iss": f"{URL}/auth/v1", "exp": int(time.time()) + 600,
    }, "s" * 40, algorithm="HS256")
    assert auth.verify_access_token(token).id == "user-2"


def test_hs256_without_a_secret_asks_supabase_once_then_caches(monkeypatch, keys):
    calls = []

    class Response:
        status_code = 200

        def json(self):
            return {"id": "user-3", "email": "c@example.test", "role": "authenticated"}

    monkeypatch.setattr(auth._http, "get", lambda *a, **k: calls.append(a) or Response())
    token = jwt.encode({"sub": "user-3", "exp": int(time.time()) + 600}, "x" * 40, algorithm="HS256")
    assert auth.verify_access_token(token).id == "user-3"
    assert auth.verify_access_token(token).id == "user-3"
    assert len(calls) == 1
