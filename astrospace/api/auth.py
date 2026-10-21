import hashlib
import logging
import os
import threading
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated

import jwt
import requests
from fastapi import Depends, Header, HTTPException, Request

DEV_USER_ID = "local-dev-user"
log = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuthUser:
    id: str
    email: str | None = None
    role: str | None = None
    auth_enabled: bool = False


def running_on_cloud_run() -> bool:
    """True when this process is a deployed Cloud Run service.

    Cloud Run injects K_SERVICE automatically; nothing in this codebase or its
    deploy docs sets it locally, so it reliably distinguishes production from
    a developer's machine without a manual "prod" flag anyone could forget to
    set. Used to refuse dev-only auth shortcuts outside local development,
    regardless of how they were triggered — an explicit flag or a missing key.
    """
    return bool(os.getenv("K_SERVICE"))


def supabase_configured() -> bool:
    bypass = os.getenv("ASTROSPACE_DEV_AUTH_BYPASS", "").lower() in {"1", "true", "yes"}
    if bypass and not running_on_cloud_run():
        return False
    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_ANON_KEY"))


# Every authenticated request used to make a fresh call to Supabase Auth
# (security audit S9): slow, and a free amplifier for anyone sending
# "Bearer junk". Tokens are now checked here first:
#   - anything that is not a well-formed, unexpired JWT is refused without a
#     network call;
#   - tokens signed with the project's asymmetric keys are verified locally
#     against its JWKS (cached), checking signature, audience, issuer, expiry;
#   - HS256 tokens are verified with SUPABASE_JWT_SECRET when that is set;
#   - otherwise Supabase Auth is asked once, through a pooled session, and the
#     answer is cached until the token expires or for five minutes at most.
_REMOTE_CACHE_SECONDS = 300
_REMOTE_CACHE_MAX = 4096
_remote_cache: dict[str, tuple[float, "AuthUser"]] = {}
_remote_lock = threading.Lock()
_http = requests.Session()


def _supabase_url() -> str:
    return os.environ["SUPABASE_URL"].rstrip("/")


@lru_cache(maxsize=1)
def _jwks_client() -> jwt.PyJWKClient:
    return jwt.PyJWKClient(
        f"{_supabase_url()}/auth/v1/.well-known/jwks.json",
        cache_keys=True,
        lifespan=600,
        timeout=5,
    )


def _user_from_claims(claims: dict) -> "AuthUser":
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return AuthUser(id=user_id, email=claims.get("email"), role=claims.get("role"), auth_enabled=True)


def _decode(token: str, key, algorithm: str) -> dict:
    return jwt.decode(
        token,
        key,
        algorithms=[algorithm],
        audience="authenticated",
        issuer=f"{_supabase_url()}/auth/v1",
        options={"require": ["exp", "sub"]},
        leeway=30,
    )


def _remote_user(token: str, expires_at: float) -> "AuthUser":
    digest = hashlib.sha256(token.encode()).hexdigest()
    now = time.time()
    with _remote_lock:
        cached = _remote_cache.get(digest)
    if cached and cached[0] > now:
        return cached[1]
    try:
        response = _http.get(
            f"{_supabase_url()}/auth/v1/user",
            headers={"apikey": os.environ["SUPABASE_ANON_KEY"], "Authorization": f"Bearer {token}"},
            timeout=8,
        )
    except requests.RequestException:
        # The exception text carries the Supabase URL and connection details;
        # log it, don't hand it to the caller.
        log.exception("Supabase auth lookup failed")
        raise HTTPException(status_code=503, detail="Sign-in service unavailable")
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    payload = response.json()
    if not payload.get("id"):
        raise HTTPException(status_code=401, detail="Invalid Supabase user payload")
    user = AuthUser(id=payload["id"], email=payload.get("email"), role=payload.get("role"), auth_enabled=True)
    with _remote_lock:
        if len(_remote_cache) >= _REMOTE_CACHE_MAX:
            for key in [k for k, (until, _) in _remote_cache.items() if until <= now] or list(_remote_cache)[:256]:
                _remote_cache.pop(key, None)
        _remote_cache[digest] = (min(expires_at, now + _REMOTE_CACHE_SECONDS), user)
    return user


def verify_access_token(token: str) -> "AuthUser":
    try:
        header = jwt.get_unverified_header(token)
        unverified = jwt.decode(token, options={"verify_signature": False})
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    expires_at = unverified.get("exp")
    if not isinstance(expires_at, (int, float)) or expires_at < time.time() - 30:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    algorithm = header.get("alg")
    try:
        if algorithm in {"ES256", "RS256"} and header.get("kid"):
            try:
                key = _jwks_client().get_signing_key_from_jwt(token).key
            except jwt.PyJWKClientError:
                # JWKS unreachable or key not published yet: ask Supabase.
                log.warning("JWKS lookup failed; falling back to Supabase Auth")
                return _remote_user(token, expires_at)
            return _user_from_claims(_decode(token, key, algorithm))
        secret = os.getenv("SUPABASE_JWT_SECRET")
        if algorithm == "HS256" and secret:
            return _user_from_claims(_decode(token, secret, "HS256"))
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return _remote_user(token, expires_at)


@lru_cache(maxsize=1)
def auth_config() -> dict:
    return {
        "enabled": supabase_configured(),
        "url": os.getenv("SUPABASE_URL"),
        "anon_key": os.getenv("SUPABASE_ANON_KEY"),
        # Public OAuth client IDs for native Google sign-in on the phone apps.
        # Unset, the apps keep using Supabase's browser flow.
        "google_web_client_id": os.getenv("GOOGLE_OAUTH_WEB_CLIENT_ID") or None,
        "google_ios_client_id": os.getenv("GOOGLE_OAUTH_IOS_CLIENT_ID") or None,
    }


def current_user(
    request: Request,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> AuthUser:
    if not supabase_configured():
        if running_on_cloud_run():
            # A deploy missing SUPABASE_URL or SUPABASE_ANON_KEY must not hand
            # every caller the shared dev identity: that would let anyone read
            # and write the "local-dev-user" profiles and spend LLM budget
            # without signing in. Refuse instead, the way admin already does.
            raise HTTPException(
                status_code=503,
                detail="Sign-in is not configured on this server.",
            )
        user = AuthUser(
            id=DEV_USER_ID, email="local@astrospace.dev",
            role="dev", auth_enabled=False,
        )
        request.state.auth_user = user
        return user

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    token = authorization.split(" ", 1)[1].strip()
    user = verify_access_token(token)
    request.state.auth_user = user
    return user


CurrentUser = Annotated[AuthUser, Depends(current_user)]
