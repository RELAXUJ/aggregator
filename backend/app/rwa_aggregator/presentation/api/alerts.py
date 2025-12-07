"""Alert subscription API endpoints.

Implements CRUD operations for price alerts:
- POST /api/alerts - Create new alert
- GET /api/alerts - List alerts (optionally by email)
- GET /api/alerts/{alert_id} - Get single alert
- DELETE /api/alerts/{alert_id} - Delete an alert
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.rwa_aggregator.application.dto.alert_dto import AlertDTO, AlertListDTO, CreateAlertRequest
from app.rwa_aggregator.application.exceptions import (
    AlertNotFoundError,
    InvalidEmailError,
    TokenNotFoundError,
)
from app.rwa_aggregator.application.use_cases.create_alert import (
    CreateAlertUseCase,
    DeleteAlertUseCase,
    GetAlertsByEmailUseCase,
)
from app.rwa_aggregator.infrastructure.db.session import get_db_session
from app.rwa_aggregator.infrastructure.repositories.sql_alert_repository import SqlAlertRepository
from app.rwa_aggregator.infrastructure.repositories.sql_token_repository import SqlTokenRepository

router = APIRouter()


@router.post("/alerts", response_model=AlertDTO, status_code=status.HTTP_201_CREATED)
async def create_alert(
    request: CreateAlertRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AlertDTO:
    """Create a new price alert subscription.

    Creates an alert that will notify the user via email when the spread
    for a token drops below the specified threshold.

    Args:
        request: Alert creation request with email, token, and threshold.
        session: Database session (injected).

    Returns:
        AlertDTO representing the newly created alert.

    Raises:
        HTTPException: 400 if email is invalid.
        HTTPException: 404 if token not found.
    """
    use_case = CreateAlertUseCase(
        token_repository=SqlTokenRepository(session),
        alert_repository=SqlAlertRepository(session),
    )

    try:
        result = await use_case.execute(request)
        await session.commit()
        return result
    except TokenNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except InvalidEmailError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        ) from e


@router.get("/alerts", response_model=AlertListDTO)
async def list_alerts(
    email: Annotated[Optional[str], Query(description="Filter alerts by email address")] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    session: AsyncSession = Depends(get_db_session),
) -> AlertListDTO:
    """List alerts, optionally filtered by email.

    Returns a paginated list of alerts. If email is provided, only alerts
    for that email address are returned.

    Args:
        email: Optional email filter.
        page: Page number (1-indexed).
        page_size: Number of alerts per page.
        session: Database session (injected).

    Returns:
        AlertListDTO with paginated alerts.

    Raises:
        HTTPException: 400 if email is required but not provided.
    """
    if email is None:
        # For now, require email filter to prevent listing all alerts
        # In production, this could be admin-only or require auth
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email parameter is required to list alerts. "
            "Provide ?email=user@example.com to filter.",
        )

    use_case = GetAlertsByEmailUseCase(
        token_repository=SqlTokenRepository(session),
        alert_repository=SqlAlertRepository(session),
    )

    alerts = await use_case.execute(email)

    # Manual pagination (could be moved to repository for large datasets)
    total = len(alerts)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_alerts = alerts[start_idx:end_idx]

    return AlertListDTO(
        alerts=paginated_alerts,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/alerts/{alert_id}", response_model=AlertDTO)
async def get_alert(
    alert_id: Annotated[int, Path(description="Alert ID")],
    session: AsyncSession = Depends(get_db_session),
) -> AlertDTO:
    """Get a single alert by ID.

    Args:
        alert_id: The alert's unique identifier.
        session: Database session (injected).

    Returns:
        AlertDTO for the requested alert.

    Raises:
        HTTPException: 404 if alert not found.
    """
    alert_repo = SqlAlertRepository(session)
    token_repo = SqlTokenRepository(session)

    alert = await alert_repo.get_by_id(alert_id)
    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with ID {alert_id} not found",
        )

    # Get token info for the DTO
    token = await token_repo.get_by_id(alert.token_id)
    token_symbol = token.symbol if token else f"Token {alert.token_id}"
    token_name = token.name if token else "Unknown Token"

    return AlertDTO(
        id=alert.id,  # type: ignore[arg-type]
        email=alert.email.value,
        base_token_symbol=token_symbol,
        base_token_name=token_name,
        quote_token_symbol="USD",
        threshold_pct=alert.threshold_pct,
        alert_type=alert.alert_type,
        status=alert.status,
        cooldown_hours=alert.cooldown_hours,
        last_triggered_at=alert.last_triggered_at,
        created_at=alert.created_at,
        can_trigger=alert.can_trigger(),
    )


@router.delete("/alerts/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: Annotated[int, Path(description="Alert ID")],
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Delete an alert by ID.

    Performs a logical delete by setting the alert status to DELETED.

    Args:
        alert_id: The alert's unique identifier.
        session: Database session (injected).

    Raises:
        HTTPException: 404 if alert not found.
    """
    use_case = DeleteAlertUseCase(
        alert_repository=SqlAlertRepository(session),
    )

    deleted = await use_case.execute(alert_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with ID {alert_id} not found",
        )

    await session.commit()
