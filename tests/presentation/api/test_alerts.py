"""Tests for the alerts API router.

Tests CRUD operations for price alert subscriptions.
"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.rwa_aggregator.application.dto.alert_dto import AlertDTO
from app.rwa_aggregator.application.exceptions import InvalidEmailError, TokenNotFoundError
from app.rwa_aggregator.domain.entities.alert import Alert, AlertStatus, AlertType
from app.rwa_aggregator.domain.entities.token import Token, TokenCategory
from app.rwa_aggregator.domain.value_objects.email_address import EmailAddress
from app.rwa_aggregator.presentation.api.alerts import router


@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI app with the alerts router."""
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_alert_dto() -> AlertDTO:
    """Create a mock AlertDTO for testing."""
    return AlertDTO(
        id=1,
        email="user@example.com",
        base_token_symbol="USDY",
        base_token_name="Ondo US Dollar Yield",
        quote_token_symbol="USD",
        threshold_pct=Decimal("2.00"),
        alert_type=AlertType.SPREAD_BELOW,
        status=AlertStatus.ACTIVE,
        cooldown_hours=1,
        last_triggered_at=None,
        created_at=datetime.now(timezone.utc),
        can_trigger=True,
    )


@pytest.fixture
def mock_alert() -> Alert:
    """Create a mock Alert domain entity for testing."""
    return Alert(
        id=1,
        email=EmailAddress("user@example.com"),
        token_id=1,
        threshold_pct=Decimal("2.00"),
        alert_type=AlertType.SPREAD_BELOW,
        status=AlertStatus.ACTIVE,
        cooldown_hours=1,
        last_triggered_at=None,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_token() -> Token:
    """Create a mock Token for testing."""
    return Token(
        id=1,
        symbol="USDY",
        name="Ondo US Dollar Yield",
        category=TokenCategory.TBILL,
        issuer="Ondo Finance",
        is_active=True,
    )


class TestCreateAlert:
    """Tests for POST /api/alerts."""

    def test_create_alert_success(
        self,
        client: TestClient,
        mock_alert_dto: AlertDTO,
    ) -> None:
        """Test successful alert creation."""
        with patch(
            "app.rwa_aggregator.presentation.api.alerts.CreateAlertUseCase"
        ) as mock_use_case_class:
            mock_use_case = AsyncMock()
            mock_use_case.execute.return_value = mock_alert_dto
            mock_use_case_class.return_value = mock_use_case

            response = client.post(
                "/api/alerts",
                json={
                    "email": "user@example.com",
                    "base_token_symbol": "USDY",
                    "threshold_pct": 2.00,
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert data["email"] == "user@example.com"
            assert data["base_token_symbol"] == "USDY"
            assert data["status"] == "active"

    def test_create_alert_invalid_email(self, client: TestClient) -> None:
        """Test 400 response for invalid email."""
        with patch(
            "app.rwa_aggregator.presentation.api.alerts.CreateAlertUseCase"
        ) as mock_use_case_class:
            mock_use_case = AsyncMock()
            mock_use_case.execute.side_effect = InvalidEmailError("invalid-email")
            mock_use_case_class.return_value = mock_use_case

            response = client.post(
                "/api/alerts",
                json={
                    "email": "invalid-email",
                    "base_token_symbol": "USDY",
                    "threshold_pct": 2.00,
                },
            )

            # Pydantic validation catches invalid email before hitting use case
            assert response.status_code == 422

    def test_create_alert_token_not_found(self, client: TestClient) -> None:
        """Test 404 response when token doesn't exist."""
        with patch(
            "app.rwa_aggregator.presentation.api.alerts.CreateAlertUseCase"
        ) as mock_use_case_class:
            mock_use_case = AsyncMock()
            mock_use_case.execute.side_effect = TokenNotFoundError("INVALID")
            mock_use_case_class.return_value = mock_use_case

            response = client.post(
                "/api/alerts",
                json={
                    "email": "user@example.com",
                    "base_token_symbol": "INVALID",
                    "threshold_pct": 2.00,
                },
            )

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()


class TestListAlerts:
    """Tests for GET /api/alerts."""

    def test_list_alerts_requires_email(self, client: TestClient) -> None:
        """Test that email query parameter is required."""
        response = client.get("/api/alerts")

        assert response.status_code == 400
        assert "email" in response.json()["detail"].lower()

    def test_list_alerts_by_email(
        self,
        client: TestClient,
        mock_alert_dto: AlertDTO,
    ) -> None:
        """Test listing alerts filtered by email."""
        with patch(
            "app.rwa_aggregator.presentation.api.alerts.GetAlertsByEmailUseCase"
        ) as mock_use_case_class:
            mock_use_case = AsyncMock()
            mock_use_case.execute.return_value = [mock_alert_dto]
            mock_use_case_class.return_value = mock_use_case

            response = client.get("/api/alerts?email=user@example.com")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert len(data["alerts"]) == 1
            assert data["alerts"][0]["email"] == "user@example.com"

    def test_list_alerts_pagination(
        self,
        client: TestClient,
        mock_alert_dto: AlertDTO,
    ) -> None:
        """Test pagination parameters."""
        alerts = [mock_alert_dto] * 25  # 25 alerts

        with patch(
            "app.rwa_aggregator.presentation.api.alerts.GetAlertsByEmailUseCase"
        ) as mock_use_case_class:
            mock_use_case = AsyncMock()
            mock_use_case.execute.return_value = alerts
            mock_use_case_class.return_value = mock_use_case

            response = client.get("/api/alerts?email=user@example.com&page=2&page_size=10")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 25
            assert data["page"] == 2
            assert data["page_size"] == 10
            assert len(data["alerts"]) == 10


class TestGetAlert:
    """Tests for GET /api/alerts/{alert_id}."""

    def test_get_alert_success(
        self,
        client: TestClient,
        mock_alert: Alert,
        mock_token: Token,
    ) -> None:
        """Test successful alert retrieval."""
        with (
            patch(
                "app.rwa_aggregator.presentation.api.alerts.SqlAlertRepository"
            ) as mock_alert_repo_class,
            patch(
                "app.rwa_aggregator.presentation.api.alerts.SqlTokenRepository"
            ) as mock_token_repo_class,
        ):
            mock_alert_repo = AsyncMock()
            mock_alert_repo.get_by_id.return_value = mock_alert
            mock_alert_repo_class.return_value = mock_alert_repo

            mock_token_repo = AsyncMock()
            mock_token_repo.get_by_id.return_value = mock_token
            mock_token_repo_class.return_value = mock_token_repo

            response = client.get("/api/alerts/1")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
            assert data["email"] == "user@example.com"

    def test_get_alert_not_found(self, client: TestClient) -> None:
        """Test 404 response when alert doesn't exist."""
        with patch(
            "app.rwa_aggregator.presentation.api.alerts.SqlAlertRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = None
            mock_repo_class.return_value = mock_repo

            response = client.get("/api/alerts/999")

            assert response.status_code == 404


class TestDeleteAlert:
    """Tests for DELETE /api/alerts/{alert_id}."""

    def test_delete_alert_success(self, client: TestClient) -> None:
        """Test successful alert deletion."""
        with patch(
            "app.rwa_aggregator.presentation.api.alerts.DeleteAlertUseCase"
        ) as mock_use_case_class:
            mock_use_case = AsyncMock()
            mock_use_case.execute.return_value = True
            mock_use_case_class.return_value = mock_use_case

            response = client.delete("/api/alerts/1")

            assert response.status_code == 204

    def test_delete_alert_not_found(self, client: TestClient) -> None:
        """Test 404 response when alert doesn't exist."""
        with patch(
            "app.rwa_aggregator.presentation.api.alerts.DeleteAlertUseCase"
        ) as mock_use_case_class:
            mock_use_case = AsyncMock()
            mock_use_case.execute.return_value = False
            mock_use_case_class.return_value = mock_use_case

            response = client.delete("/api/alerts/999")

            assert response.status_code == 404
