"""Health check endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    timestamp: datetime
    version: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check application health status.

    Returns:
        Health status with timestamp and version.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc),
        version="0.1.0",
    )


@router.get("/ready")
async def readiness_check() -> dict[str, str]:
    """Check if application is ready to serve requests.

    This endpoint can be extended to check database, Redis, etc.

    Returns:
        Readiness status.
    """
    # TODO: Add database and Redis connectivity checks
    return {"status": "ready"}


