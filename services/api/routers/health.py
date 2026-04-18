from datetime import datetime, timezone

from fastapi import APIRouter

from services.api.config import settings

router = APIRouter()


@router.get("/api/health")
def get_health() -> dict:
    return {
        "status": "ok",
        "version": "0.1.0",
        "mode": settings.app_mode,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
