"""Tests for the web dashboard routes.

Tests the HTMX-powered dashboard and partial endpoints.
"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.rwa_aggregator.application.dto.price_dto import (
    AggregatedPricesDTO,
    BestPriceDTO,
    VenuePriceDTO,
)
from app.rwa_aggregator.application.exceptions import NoPriceDataError, TokenNotFoundError
from app.rwa_aggregator.domain.entities.token import Token, TokenCategory
from app.rwa_aggregator.presentation.web.dashboard import router


@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI app with the dashboard router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_tokens() -> list[Token]:
    """Create mock tokens for testing."""
    return [
        Token(
            id=1,
            symbol="USDY",
            name="Ondo US Dollar Yield",
            category=TokenCategory.TBILL,
            issuer="Ondo Finance",
            is_active=True,
        ),
        Token(
            id=2,
            symbol="OUSG",
            name="Ondo Short-Term US Gov Treasuries",
            category=TokenCategory.TBILL,
            issuer="Ondo Finance",
            is_active=True,
        ),
    ]


@pytest.fixture
def mock_prices() -> AggregatedPricesDTO:
    """Create mock aggregated prices for testing."""
    now = datetime.now(timezone.utc)
    return AggregatedPricesDTO(
        base_token_symbol="USDY",
        base_token_name="Ondo US Dollar Yield",
        quote_token_symbol="USD",
        best_prices=BestPriceDTO(
            base_token_symbol="USDY",
            quote_token_symbol="USD",
            best_bid_venue="Kraken",
            best_bid_venue_id=1,
            best_bid_price=Decimal("1.0012"),
            best_ask_venue="Coinbase",
            best_ask_venue_id=2,
            best_ask_price=Decimal("1.0018"),
            effective_spread_pct=Decimal("0.0599"),
            effective_spread_bps=Decimal("5.99"),
        ),
        venues=[
            VenuePriceDTO(
                venue_name="Kraken",
                venue_id=1,
                base_token_symbol="USDY",
                quote_token_symbol="USD",
                bid=Decimal("1.0012"),
                ask=Decimal("1.0020"),
                mid_price=Decimal("1.0016"),
                spread=Decimal("0.0008"),
                spread_bps=Decimal("7.99"),
                volume_24h=Decimal("1250000"),
                timestamp=now,
                is_stale=False,
                trade_url="https://trade.kraken.com/charts/KRAKEN:USDY-USD",
            ),
        ],
        num_venues=1,
        num_fresh_venues=1,
        last_updated=now,
    )


class TestDashboard:
    """Tests for GET / (main dashboard)."""

    def test_dashboard_renders(
        self,
        client: TestClient,
        mock_tokens: list[Token],
        mock_prices: AggregatedPricesDTO,
    ) -> None:
        """Test that dashboard page renders successfully."""
        with (
            patch(
                "app.rwa_aggregator.presentation.web.dashboard.SqlTokenRepository"
            ) as mock_token_repo_class,
            patch(
                "app.rwa_aggregator.presentation.web.dashboard._create_use_case"
            ) as mock_create,
        ):
            mock_token_repo = AsyncMock()
            mock_token_repo.get_all_active.return_value = mock_tokens
            mock_token_repo_class.return_value = mock_token_repo

            mock_use_case = AsyncMock()
            mock_use_case.execute.return_value = mock_prices
            mock_create.return_value = mock_use_case

            response = client.get("/")

            assert response.status_code == 200
            assert "text/html" in response.headers["content-type"]

    def test_dashboard_contains_token_selector(
        self,
        client: TestClient,
        mock_tokens: list[Token],
        mock_prices: AggregatedPricesDTO,
    ) -> None:
        """Test that dashboard contains token selector with all tokens."""
        with (
            patch(
                "app.rwa_aggregator.presentation.web.dashboard.SqlTokenRepository"
            ) as mock_token_repo_class,
            patch(
                "app.rwa_aggregator.presentation.web.dashboard._create_use_case"
            ) as mock_create,
        ):
            mock_token_repo = AsyncMock()
            mock_token_repo.get_all_active.return_value = mock_tokens
            mock_token_repo_class.return_value = mock_token_repo

            mock_use_case = AsyncMock()
            mock_use_case.execute.return_value = mock_prices
            mock_create.return_value = mock_use_case

            response = client.get("/")

            assert response.status_code == 200
            html = response.text
            # Check for token selector
            assert "token-selector" in html
            # Check for token options
            assert "USDY" in html
            assert "OUSG" in html

    def test_dashboard_with_token_param(
        self,
        client: TestClient,
        mock_tokens: list[Token],
        mock_prices: AggregatedPricesDTO,
    ) -> None:
        """Test dashboard with specific token parameter."""
        with (
            patch(
                "app.rwa_aggregator.presentation.web.dashboard.SqlTokenRepository"
            ) as mock_token_repo_class,
            patch(
                "app.rwa_aggregator.presentation.web.dashboard._create_use_case"
            ) as mock_create,
        ):
            mock_token_repo = AsyncMock()
            mock_token_repo.get_all_active.return_value = mock_tokens
            mock_token_repo_class.return_value = mock_token_repo

            mock_use_case = AsyncMock()
            mock_use_case.execute.return_value = mock_prices
            mock_create.return_value = mock_use_case

            response = client.get("/?token=OUSG")

            assert response.status_code == 200
            mock_use_case.execute.assert_called_once()
            call_args = mock_use_case.execute.call_args
            assert call_args.kwargs["base_symbol"] == "OUSG"

    def test_dashboard_handles_no_tokens(self, client: TestClient) -> None:
        """Test dashboard gracefully handles no tokens."""
        with patch(
            "app.rwa_aggregator.presentation.web.dashboard.SqlTokenRepository"
        ) as mock_token_repo_class:
            mock_token_repo = AsyncMock()
            mock_token_repo.get_all_active.return_value = []
            mock_token_repo_class.return_value = mock_token_repo

            response = client.get("/")

            assert response.status_code == 200
            assert "No tokens available" in response.text or "No Price Data" in response.text


class TestPriceTablePartial:
    """Tests for GET /partials/price-table/{token_symbol}."""

    def test_price_table_renders(
        self,
        client: TestClient,
        mock_prices: AggregatedPricesDTO,
    ) -> None:
        """Test that price table partial renders successfully."""
        with patch(
            "app.rwa_aggregator.presentation.web.dashboard._create_use_case"
        ) as mock_create:
            mock_use_case = AsyncMock()
            mock_use_case.execute.return_value = mock_prices
            mock_create.return_value = mock_use_case

            response = client.get("/partials/price-table/USDY")

            assert response.status_code == 200
            assert "text/html" in response.headers["content-type"]

    def test_price_table_contains_venue_data(
        self,
        client: TestClient,
        mock_prices: AggregatedPricesDTO,
    ) -> None:
        """Test that price table contains venue data."""
        with patch(
            "app.rwa_aggregator.presentation.web.dashboard._create_use_case"
        ) as mock_create:
            mock_use_case = AsyncMock()
            mock_use_case.execute.return_value = mock_prices
            mock_create.return_value = mock_use_case

            response = client.get("/partials/price-table/USDY")

            assert response.status_code == 200
            html = response.text
            # Check for venue name
            assert "Kraken" in html
            # Check for bid/ask prices
            assert "1.0012" in html
            assert "1.0020" in html

    def test_price_table_token_not_found(self, client: TestClient) -> None:
        """Test error handling when token is not found."""
        with patch(
            "app.rwa_aggregator.presentation.web.dashboard._create_use_case"
        ) as mock_create:
            mock_use_case = AsyncMock()
            mock_use_case.execute.side_effect = TokenNotFoundError("INVALID")
            mock_create.return_value = mock_use_case

            response = client.get("/partials/price-table/INVALID")

            assert response.status_code == 200  # Returns HTML error message
            assert "not found" in response.text.lower()

    def test_price_table_no_price_data(self, client: TestClient) -> None:
        """Test error handling when no price data available."""
        with patch(
            "app.rwa_aggregator.presentation.web.dashboard._create_use_case"
        ) as mock_create:
            mock_use_case = AsyncMock()
            mock_use_case.execute.side_effect = NoPriceDataError("USDY")
            mock_create.return_value = mock_use_case

            response = client.get("/partials/price-table/USDY")

            assert response.status_code == 200  # Returns HTML error message
            assert "no price data" in response.text.lower()


class TestKpiCardsPartial:
    """Tests for GET /partials/kpi-cards/{token_symbol}."""

    def test_kpi_cards_renders(
        self,
        client: TestClient,
        mock_prices: AggregatedPricesDTO,
    ) -> None:
        """Test that KPI cards partial renders successfully."""
        with patch(
            "app.rwa_aggregator.presentation.web.dashboard._create_use_case"
        ) as mock_create:
            mock_use_case = AsyncMock()
            mock_use_case.execute.return_value = mock_prices
            mock_create.return_value = mock_use_case

            response = client.get("/partials/kpi-cards/USDY")

            assert response.status_code == 200
            assert "text/html" in response.headers["content-type"]

    def test_kpi_cards_contains_best_prices(
        self,
        client: TestClient,
        mock_prices: AggregatedPricesDTO,
    ) -> None:
        """Test that KPI cards contain best price data."""
        with patch(
            "app.rwa_aggregator.presentation.web.dashboard._create_use_case"
        ) as mock_create:
            mock_use_case = AsyncMock()
            mock_use_case.execute.return_value = mock_prices
            mock_create.return_value = mock_use_case

            response = client.get("/partials/kpi-cards/USDY")

            assert response.status_code == 200
            html = response.text
            # Check for best bid/ask labels
            assert "Best Bid" in html
            assert "Best Ask" in html
            # Check for prices
            assert "1.0012" in html
            assert "1.0018" in html
