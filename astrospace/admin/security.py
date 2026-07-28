from __future__ import annotations

import os
from dataclasses import replace
from typing import Annotated

from fastapi import Depends, HTTPException

from ..api.auth import AuthUser, CurrentUser, running_on_cloud_run
from .client import AdminStorageError, get_admin_client


def _bootstrap_emails() -> set[str]:
    return {
        value.strip().lower()
        for value in os.getenv("ADMIN_EMAILS", "").split(",")
        if value.strip()
    }


def current_admin(user: CurrentUser) -> AuthUser:
    if not user.auth_enabled:
        # Auth being "off" is normal on a developer's machine (no Supabase
        # keys configured at all) and is how the console is exercised
        # locally. On Cloud Run it means SUPABASE_ANON_KEY is missing or the
        # dev bypass leaked into the deploy config — either way, silently
        # promoting the caller to admin is the fail-open that matters most:
        # it needs no bearer token at all. Refuse instead of granting.
        if running_on_cloud_run():
            raise HTTPException(
                status_code=503,
                detail="Admin console requires Supabase auth to be configured",
            )
        return replace(user, role="admin")
    try:
        record = get_admin_client().one(
            "admin_users",
            params={"user_id": f"eq.{user.id}", "active": "eq.true", "select": "role"},
        )
    except AdminStorageError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if record:
        return replace(user, role=record["role"])
    if user.email and user.email.lower() in _bootstrap_emails():
        return replace(user, role="admin")
    raise HTTPException(status_code=403, detail="Knowledge Console access is restricted")


AdminUser = Annotated[AuthUser, Depends(current_admin)]


def require_full_admin(user: AdminUser) -> AuthUser:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator permission required")
    return user


FullAdminUser = Annotated[AuthUser, Depends(require_full_admin)]
