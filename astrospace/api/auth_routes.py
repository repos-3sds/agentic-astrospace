from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db, crud
from .auth import DEV_USER_ID, CurrentUser, auth_config

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/config")
def config():
    cfg = auth_config()
    return {
        "enabled": cfg["enabled"],
        "supabase_url": cfg["url"],
        "supabase_anon_key": cfg["anon_key"],
    }


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
