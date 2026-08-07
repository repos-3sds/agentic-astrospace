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


def _admin_role_from_database_url(user_id: str) -> str | None:
    """Fallback for admin checks when the Supabase REST secret is absent.

    The admin console normally uses the Supabase service-role REST client. A
    deploy can have authenticated Supabase sessions and a Postgres DATABASE_URL
    without also carrying the service-role key; in that case the access check
    should still be able to read the same `admin_users` row through the app's
    already-configured SQLAlchemy engine. This does not grant access from email
    or profile data — only an active row for the authenticated Supabase user id
    passes.
    """
    database_url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not database_url or not database_url.startswith(("postgres://", "postgresql://", "postgresql+")):
        return None
    try:
        from sqlalchemy import text

        from ..db.database import SessionLocal

        with SessionLocal() as db:
            row = db.execute(
                text(
                    """
                    select role
                    from public.admin_users
                    where user_id = :user_id and active = true
                    limit 1
                    """
                ),
                {"user_id": user_id},
            ).fetchone()
    except Exception:
        return None
    return row[0] if row else None


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
        role = _admin_role_from_database_url(user.id)
        if role:
            return replace(user, role=role)
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
