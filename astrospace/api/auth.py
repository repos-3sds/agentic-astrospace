import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated

import requests
from fastapi import Depends, Header, HTTPException, Request

DEV_USER_ID = "local-dev-user"


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


@lru_cache(maxsize=1)
def auth_config() -> dict:
    return {
        "enabled": supabase_configured(),
        "url": os.getenv("SUPABASE_URL"),
        "anon_key": os.getenv("SUPABASE_ANON_KEY"),
    }


def current_user(
    request: Request,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> AuthUser:
    if not supabase_configured():
        user = AuthUser(
            id=DEV_USER_ID, email="local@astrospace.dev",
            role="dev", auth_enabled=False,
        )
        request.state.auth_user = user
        return user

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    token = authorization.split(" ", 1)[1].strip()
    try:
        response = requests.get(
            f"{os.environ['SUPABASE_URL'].rstrip('/')}/auth/v1/user",
            headers={
                "apikey": os.environ["SUPABASE_ANON_KEY"],
                "Authorization": f"Bearer {token}",
            },
            timeout=8,
        )
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Supabase auth unavailable: {e}")

    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    payload = response.json()
    user_id = payload.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid Supabase user payload")
    user = AuthUser(
        id=user_id,
        email=payload.get("email"),
        role=payload.get("role"),
        auth_enabled=True,
    )
    request.state.auth_user = user
    return user


CurrentUser = Annotated[AuthUser, Depends(current_user)]
