from typing import Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..db import crud
from .auth import CurrentUser

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


class PanchangaPlace(BaseModel):
    city: str
    nation: str
    timezone: str
    label: str


class UserSettingsPayload(BaseModel):
    chart_style: Literal["south", "north", "eastern"] = "south"
    ayanamsha: Literal["lahiri", "raman", "krishnamurti"] = "lahiri"
    node_type: Literal["mean", "true"] = "mean"
    timezone_mode: Literal["browser", "panchanga_place"] = "browser"
    panchanga_place: Optional[PanchangaPlace] = None
    language: str = "en"
    regional_format: str = "en-IN"


def _settings_to_dict(settings) -> dict:
    return {
        "user_id": settings.user_id,
        "chart_style": settings.chart_style,
        "ayanamsha": settings.ayanamsha,
        "node_type": settings.node_type,
        "timezone_mode": settings.timezone_mode,
        "panchanga_place": settings.panchanga_place,
        "language": settings.language,
        "regional_format": settings.regional_format,
        "created_at": settings.created_at.isoformat() if settings.created_at else None,
        "updated_at": settings.updated_at.isoformat() if settings.updated_at else None,
    }


def _default_settings(user_id: str) -> dict:
    return {
        "user_id": user_id,
        **UserSettingsPayload().model_dump(),
        "created_at": None,
        "updated_at": None,
        "exists": False,
    }


@router.get("")
def get_settings(user: CurrentUser, db: Session = Depends(get_db)):
    settings = crud.get_user_settings(db, user.id)
    if not settings:
        return _default_settings(user.id)
    return {**_settings_to_dict(settings), "exists": True}


@router.put("")
def save_settings(body: UserSettingsPayload, user: CurrentUser, db: Session = Depends(get_db)):
    settings = crud.upsert_user_settings(db, user.id, body.model_dump())
    return {**_settings_to_dict(settings), "exists": True}
