from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..db import get_db, crud
from .auth import DEV_USER_ID, CurrentUser, auth_config

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

NATIVE_AUTH_CALLBACK = "app.astrospace.mobile://auth/callback"


@router.get("/config")
def config():
    cfg = auth_config()
    return {
        "enabled": cfg["enabled"],
        "supabase_url": cfg["url"],
        "supabase_anon_key": cfg["anon_key"],
    }


@router.get("/native-callback")
def native_callback(request: Request):
    """Bridge Supabase's HTTPS OAuth callback into the native app scheme.

    Some hosted auth/provider combinations accept the custom mobile scheme in
    `redirectTo`, but others fall back to the Site URL unless the redirect is a
    normal HTTPS URL. This route gives Supabase an allow-list friendly HTTPS
    target, then immediately hands the PKCE code/error back to Capacitor.
    """
    query = urlencode(list(request.query_params.multi_items()))
    destination = NATIVE_AUTH_CALLBACK + (f"?{query}" if query else "")
    return RedirectResponse(destination, status_code=302)


@router.get("/migration/local")
def local_migration_status(user: CurrentUser, db: Session = Depends(get_db)):
    if not user.auth_enabled:
        return {"available": False, "local_kundlis": 0, "message": "Sign in first to claim local data."}
    local_count = crud.count_kundlis(db, DEV_USER_ID)
    return {
        "available": local_count > 0,
        "local_kundlis": local_count,
        "message": (
            f"{local_count} local kundli(s) can be moved into your signed-in account."
            if local_count
            else "No local workspace data is waiting to be claimed."
        ),
    }


@router.post("/migration/local/claim")
def claim_local_workspace(user: CurrentUser, db: Session = Depends(get_db)):
    if not user.auth_enabled:
        raise HTTPException(status_code=401, detail="Sign in before claiming local data")
    moved = crud.transfer_kundlis(db, DEV_USER_ID, user.id)
    return {
        "moved_kundlis": moved,
        "message": f"Moved {moved} local kundli(s) into your signed-in account.",
    }
