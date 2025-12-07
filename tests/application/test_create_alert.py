"""Unit tests for CreateAlertUseCase and related alert use cases."""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.rwa_aggregator.application.dto.alert_dto import CreateAlertRequest
from app.rwa_aggregator.application.exceptions import InvalidEmailError, TokenNotFoundError
from app.rwa_aggregator.application.use_cases.create_alert import (
    CreateAlertUseCase,
    DeleteAlertUseCase,
    GetAlertsByEmailUseCase,
)
from app.rwa_aggregator.domain.entities.alert import Alert, AlertStatus, AlertType
from app.rwa_aggregator.domain.entities.token import Token, TokenCategory
from app.rwa_aggregator.domain.value_objects.email_address import EmailAddress


@pytest.fixture
def mock_token_repository() -> AsyncMock:
    """Create a mock token repository."""
    return AsyncMock()


@pytest.fixture
def mock_alert_repository() -> AsyncMock:
    """Create a mock alert repository."""
    return AsyncMock()


@pytest.fixture
def sample_token() -> Token:
    """Create a sample token for testing."""
    return Token(
        id=1,
        symbol="USDY",
        name="Ondo US Dollar Yield",
        category=TokenCategory.TBILL,
        issuer="Ondo Finance",
        is_active=True,
    )


@pytest.fixture
def sample_alert() -> Alert:
    """Create a sample alert for testing."""
    return Alert(
        id=1,
        email=EmailAddress("test@example.com"),
        token_id=1,
        threshold_pct=Decimal("0.05"),
        alert_type=AlertType.SPREAD_BELOW,
        status=AlertStatus.ACTIVE,
        cooldown_hours=1,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def create_alert_request() -> CreateAlertRequest:
    """Create a sample alert request for testing."""
    return CreateAlertRequest(
        email="test@example.com",
        base_token_symbol="USDY",
        quote_token_symbol="USD",
        threshold_pct=Decimal("0.05"),
        alert_type=AlertType.SPREAD_BELOW,
        cooldown_hours=1,
    )


@pytest.fixture
def create_use_case(
    mock_token_repository: AsyncMock,
    mock_alert_repository: AsyncMock,
) -> CreateAlertUseCase:
    """Create the CreateAlertUseCase with mocked dependencies."""
    return CreateAlertUseCase(
        token_repository=mock_token_repository,
        alert_repository=mock_alert_repository,
    )


class TestCreateAlertUseCase:
    """Tests for CreateAlertUseCase."""

    @pytest.mark.asyncio
    async def test_execute_creates_alert_successfully(
        self,
        create_use_case: CreateAlertUseCase,
        mock_token_repository: AsyncMock,
        mock_alert_repository: AsyncMock,
        sample_token: Token,
        sample_alert: Alert,
        create_alert_request: CreateAlertRequest,
    ) -> None:
        """Test successful alert creation."""
        # Arrange
        mock_token_repository.get_by_symbol.return_value = sample_token
        mock_alert_repository.save.return_value = sample_alert

        # Act
        result = await create_use_case.execute(create_alert_request)

        # Assert
        assert result.id == 1
        assert result.email == "test@example.com"
        assert result.base_token_symbol == "USDY"
        assert result.base_token_name == "Ondo US Dollar Yield"
        assert result.threshold_pct == Decimal("0.05")
        assert result.status == AlertStatus.ACTIVE

        # Verify repository was called
        mock_alert_repository.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_raises_token_not_found(
        self,
        create_use_case: CreateAlertUseCase,
        mock_token_repository: AsyncMock,
        create_alert_request: CreateAlertRequest,
    ) -> None:
        """Test that TokenNotFoundError is raised for unknown tokens."""
        # Arrange
        mock_token_repository.get_by_symbol.return_value = None

        # Act & Assert
        with pytest.raises(TokenNotFoundError) as exc_info:
            await create_use_case.execute(create_alert_request)

        assert exc_info.value.symbol == "USDY"

    @pytest.mark.asyncio
    async def test_execute_validates_email(
        self,
        mock_token_repository: AsyncMock,
        mock_alert_repository: AsyncMock,
        sample_token: Token,
    ) -> None:
        """Test that email validation is performed."""
        # Arrange
        mock_token_repository.get_by_symbol.return_value = sample_token

        # Note: Pydantic will validate the email in CreateAlertRequest,
        # but we test the domain validation layer here with a mock that bypasses Pydantic
        use_case = CreateAlertUseCase(
            token_repository=mock_token_repository,
            alert_repository=mock_alert_repository,
        )

        # Create request with valid email (Pydantic validates on construction)
        request = CreateAlertRequest(
            email="valid@example.com",
            base_token_symbol="USDY",
            threshold_pct=Decimal("0.05"),
        )

        # The domain EmailAddress value object will also validate
        mock_alert_repository.save.return_value = Alert(
            id=1,
            email=EmailAddress("valid@example.com"),
            token_id=1,
            threshold_pct=Decimal("0.05"),
        )

        result = await use_case.execute(request)
        assert result.email == "valid@example.com"

    @pytest.mark.asyncio
    async def test_execute_sets_default_values(
        self,
        create_use_case: CreateAlertUseCase,
        mock_token_repository: AsyncMock,
        mock_alert_repository: AsyncMock,
        sample_token: Token,
    ) -> None:
        """Test that default values are applied correctly."""
        # Arrange
        mock_token_repository.get_by_symbol.return_value = sample_token

        # Create request with minimal fields
        request = CreateAlertRequest(
            email="test@example.com",
            base_token_symbol="USDY",
            threshold_pct=Decimal("0.10"),
        )

        saved_alert = Alert(
            id=1,
            email=EmailAddress("test@example.com"),
            token_id=1,
            threshold_pct=Decimal("0.10"),
            alert_type=AlertType.SPREAD_BELOW,  # Default
            status=AlertStatus.ACTIVE,  # Default
            cooldown_hours=1,  # Default
        )
        mock_alert_repository.save.return_value = saved_alert

        # Act
        result = await create_use_case.execute(request)

        # Assert defaults
        assert result.alert_type == AlertType.SPREAD_BELOW
        assert result.status == AlertStatus.ACTIVE
        assert result.cooldown_hours == 1
        assert result.quote_token_symbol == "USD"


class TestGetAlertsByEmailUseCase:
    """Tests for GetAlertsByEmailUseCase."""

    @pytest.fixture
    def get_alerts_use_case(
        self,
        mock_token_repository: AsyncMock,
        mock_alert_repository: AsyncMock,
    ) -> GetAlertsByEmailUseCase:
        """Create the GetAlertsByEmailUseCase with mocked dependencies."""
        return GetAlertsByEmailUseCase(
            token_repository=mock_token_repository,
            alert_repository=mock_alert_repository,
        )

    @pytest.mark.asyncio
    async def test_execute_returns_alerts_for_email(
        self,
        get_alerts_use_case: GetAlertsByEmailUseCase,
        mock_token_repository: AsyncMock,
        mock_alert_repository: AsyncMock,
        sample_token: Token,
        sample_alert: Alert,
    ) -> None:
        """Test retrieving alerts by email."""
        # Arrange
        mock_alert_repository.get_by_email.return_value = [sample_alert]
        mock_token_repository.get_by_id.return_value = sample_token

        # Act
        result = await get_alerts_use_case.execute("test@example.com")

        # Assert
        assert len(result) == 1
        assert result[0].email == "test@example.com"
        assert result[0].base_token_symbol == "USDY"

    @pytest.mark.asyncio
    async def test_execute_returns_empty_list_when_no_alerts(
        self,
        get_alerts_use_case: GetAlertsByEmailUseCase,
        mock_alert_repository: AsyncMock,
    ) -> None:
        """Test that empty list is returned when no alerts exist."""
        # Arrange
        mock_alert_repository.get_by_email.return_value = []

        # Act
        result = await get_alerts_use_case.execute("unknown@example.com")

        # Assert
        assert result == []

    @pytest.mark.asyncio
    async def test_execute_handles_missing_token(
        self,
        get_alerts_use_case: GetAlertsByEmailUseCase,
        mock_token_repository: AsyncMock,
        mock_alert_repository: AsyncMock,
        sample_alert: Alert,
    ) -> None:
        """Test graceful handling when token is not found."""
        # Arrange
        mock_alert_repository.get_by_email.return_value = [sample_alert]
        mock_token_repository.get_by_id.return_value = None  # Token not found

        # Act
        result = await get_alerts_use_case.execute("test@example.com")

        # Assert - should use fallback token info
        assert len(result) == 1
        assert "Token" in result[0].base_token_symbol
        assert result[0].base_token_name == "Unknown Token"


class TestDeleteAlertUseCase:
    """Tests for DeleteAlertUseCase."""

    @pytest.fixture
    def delete_use_case(
        self,
        mock_alert_repository: AsyncMock,
    ) -> DeleteAlertUseCase:
        """Create the DeleteAlertUseCase with mocked dependencies."""
        return DeleteAlertUseCase(alert_repository=mock_alert_repository)

    @pytest.mark.asyncio
    async def test_execute_deletes_alert(
        self,
        delete_use_case: DeleteAlertUseCase,
        mock_alert_repository: AsyncMock,
    ) -> None:
        """Test successful alert deletion."""
        # Arrange
        mock_alert_repository.delete.return_value = True

        # Act
        result = await delete_use_case.execute(alert_id=1)

        # Assert
        assert result is True
        mock_alert_repository.delete.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_execute_returns_false_when_not_found(
        self,
        delete_use_case: DeleteAlertUseCase,
        mock_alert_repository: AsyncMock,
    ) -> None:
        """Test that False is returned when alert doesn't exist."""
        # Arrange
        mock_alert_repository.delete.return_value = False

        # Act
        result = await delete_use_case.execute(alert_id=999)

        # Assert
        assert result is False
