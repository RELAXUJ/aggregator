"""Use case for creating price alert subscriptions.

Implements alert creation by orchestrating:
- Token validation via TokenRepository
- Email validation via EmailAddress value object
- Alert persistence via AlertRepository
"""

from typing import Optional

from app.rwa_aggregator.application.dto.alert_dto import AlertDTO, CreateAlertRequest
from app.rwa_aggregator.application.exceptions import (
    InvalidEmailError,
    TokenNotFoundError,
    TokenNotTradableError,
)
from app.rwa_aggregator.domain.entities.alert import Alert, AlertStatus, AlertType
from app.rwa_aggregator.domain.entities.token import MarketType
from app.rwa_aggregator.domain.repositories.alert_repository import AlertRepository
from app.rwa_aggregator.domain.repositories.token_repository import TokenRepository
from app.rwa_aggregator.domain.value_objects.email_address import EmailAddress


class CreateAlertUseCase:
    """Application service for creating price alert subscriptions.

    This use case validates the alert request, creates a new Alert entity,
    and persists it to the database. It handles email and token validation
    before creating the alert.
    """

    def __init__(
        self,
        token_repository: TokenRepository,
        alert_repository: AlertRepository,
    ) -> None:
        """Initialize the use case with required dependencies.

        Args:
            token_repository: Repository for token data access.
            alert_repository: Repository for alert persistence.
        """
        self._token_repository = token_repository
        self._alert_repository = alert_repository

    async def execute(self, request: CreateAlertRequest) -> AlertDTO:
        """Execute the alert creation.

        Args:
            request: CreateAlertRequest with alert configuration.

        Returns:
            AlertDTO representing the created alert.

        Raises:
            TokenNotFoundError: If the base token symbol is not recognized.
            TokenNotTradableError: If the token is NAV-only (no active trading pairs).
            InvalidEmailError: If the email address is invalid.
        """
        # 1. Validate and fetch the token
        token = await self._token_repository.get_by_symbol(request.base_token_symbol)
        if token is None or token.id is None:
            raise TokenNotFoundError(request.base_token_symbol)

        # 2. Check that token is tradable (has active trading pairs)
        # NAV-only tokens don't have bid/ask spreads, so alerts don't make sense
        if token.market_type == MarketType.NAV_ONLY:
            raise TokenNotTradableError(request.base_token_symbol)

        # 3. Validate email using domain value object
        try:
            email_address = EmailAddress(request.email)
        except ValueError as e:
            raise InvalidEmailError(request.email) from e

        # 4. Create the Alert domain entity
        alert = Alert(
            id=None,  # Will be assigned by the database
            email=email_address,
            token_id=token.id,
            threshold_pct=request.threshold_pct,
            alert_type=request.alert_type,
            status=AlertStatus.ACTIVE,
            cooldown_hours=request.cooldown_hours,
        )

        # 5. Persist the alert
        saved_alert = await self._alert_repository.save(alert)

        # 6. Build and return the DTO
        return self._build_alert_dto(
            alert=saved_alert,
            token_symbol=request.base_token_symbol,
            token_name=token.name,
            quote_symbol=request.quote_token_symbol,
        )

    def _build_alert_dto(
        self,
        alert: Alert,
        token_symbol: str,
        token_name: str,
        quote_symbol: str,
    ) -> AlertDTO:
        """Build AlertDTO from Alert entity and token info.

        Args:
            alert: The saved Alert entity.
            token_symbol: Base token symbol.
            token_name: Human-readable token name.
            quote_symbol: Quote token symbol.

        Returns:
            AlertDTO with all alert information.
        """
        return AlertDTO(
            id=alert.id,  # type: ignore[arg-type]
            email=alert.email.value,
            base_token_symbol=token_symbol,
            base_token_name=token_name,
            quote_token_symbol=quote_symbol,
            threshold_pct=alert.threshold_pct,
            alert_type=alert.alert_type,
            status=alert.status,
            cooldown_hours=alert.cooldown_hours,
            last_triggered_at=alert.last_triggered_at,
            created_at=alert.created_at,
            can_trigger=alert.can_trigger(),
        )


class GetAlertsByEmailUseCase:
    """Application service for retrieving alerts by email address.

    This use case fetches all alerts associated with a given email,
    enriching them with token information for display.
    """

    def __init__(
        self,
        token_repository: TokenRepository,
        alert_repository: AlertRepository,
    ) -> None:
        """Initialize the use case with required dependencies.

        Args:
            token_repository: Repository for token data access.
            alert_repository: Repository for alert retrieval.
        """
        self._token_repository = token_repository
        self._alert_repository = alert_repository

    async def execute(self, email: str) -> list[AlertDTO]:
        """Execute the alert retrieval by email.

        Args:
            email: Email address to search for.

        Returns:
            List of AlertDTO objects for the given email.
        """
        alerts = await self._alert_repository.get_by_email(email)

        if not alerts:
            return []

        # Build a cache of token info for efficiency
        token_cache: dict[int, tuple[str, str]] = {}

        alert_dtos: list[AlertDTO] = []
        for alert in alerts:
            # Get token info (cached)
            if alert.token_id not in token_cache:
                token = await self._token_repository.get_by_id(alert.token_id)
                if token:
                    token_cache[alert.token_id] = (token.symbol, token.name)
                else:
                    token_cache[alert.token_id] = (f"Token {alert.token_id}", "Unknown Token")

            token_symbol, token_name = token_cache[alert.token_id]

            alert_dtos.append(
                AlertDTO(
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
            )

        return alert_dtos


class DeleteAlertUseCase:
    """Application service for deleting an alert.

    This use case handles alert deletion by ID.
    """

    def __init__(self, alert_repository: AlertRepository) -> None:
        """Initialize the use case with required dependencies.

        Args:
            alert_repository: Repository for alert operations.
        """
        self._alert_repository = alert_repository

    async def execute(self, alert_id: int) -> bool:
        """Execute the alert deletion.

        Args:
            alert_id: ID of the alert to delete.

        Returns:
            True if the alert was deleted, False if not found.
        """
        return await self._alert_repository.delete(alert_id)
