from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from python.core.database import get_session
from python.core.models import AppSettings
from python.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/api/settings")
def get_app_settings(session: Session = Depends(get_session)) -> dict[str, Any]:
    """Return current application settings from DB."""
    app_settings = session.exec(select(AppSettings)).first()
    if not app_settings:
        raise HTTPException(status_code=404, detail="App settings not initialized")
    return app_settings.model_dump()


@router.put("/api/settings")
def update_app_settings(
    updates: dict[str, Any],
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Update application settings."""
    app_settings = session.exec(select(AppSettings)).first()
    if not app_settings:
        raise HTTPException(status_code=404, detail="App settings not initialized")

    before_mode = app_settings.current_mode

    for field, value in updates.items():
        if hasattr(app_settings, field):
            setattr(app_settings, field, value)

    session.add(app_settings)
    session.commit()
    session.refresh(app_settings)

    if "current_mode" in updates and updates["current_mode"] != before_mode:
        logger.info(
            "mode_changed",
            before=before_mode,
            after=app_settings.current_mode,
        )

    return app_settings.model_dump()
