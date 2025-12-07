"""Tests for the prices API router.

Tests GET /api/prices and GET /api/prices/{token_symbol} endpoints.
"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

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
from app.rwa_aggregator.presentation.api.prices import router


@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI app with the prices router."""
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_aggregated_prices() -> AggregatedPricesDTO:
    """Create a mock AggregatedPricesDTO for testing."""
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
            VenuePriceDTO(
                venue_name="Coinbase",
                venue_id=2,
                base_token_symbol="USDY",
                quote_token_symbol="USD",
                bid=Decimal("1.0010"),
                ask=Decimal("1.0018"),
                mid_price=Decimal("1.0014"),
                spread=Decimal("0.0008"),
                spread_bps=Decimal("7.99"),
                volume_24h=Decimal("850000"),
                timestamp=now,
                is_stale=False,
                trade_url="https://www.coinbase.com/advanced-trade/spot/USDY-USD",
            ),
        ],
        num_venues=2,
        num_fresh_venues=2,
        last_updated=now,
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
        chain="ethereum",
        contract_address="0x...",
        is_active=True,
    )


class TestGetAggregatedPrices:
    """Tests for GET /api/prices/{token_symbol}."""

    def test_get_prices_success(
        self,
        client: TestClient,
        mock_aggregated_prices: AggregatedPricesDTO,
    ) -> None:
        """Test successful price retrieval for a token."""
        with patch(
            "app.rwa_aggregator.presentation.api.prices._create_use_case"
        ) as mock_create:
            mock_use_case = AsyncMock()
            mock_use_case.execute.return_value = mock_aggregated_prices
            mock_create.return_value = mock_use_case

            response = client.get("/api/prices/USDY")

            assert response.status_code == 200
            data = response.json()
            assert data["base_token_symbol"] == "USDY"
            assert data["best_prices"]["best_bid_price"] == 1.0012
            assert data["best_prices"]["best_ask_price"] == 1.0018
            assert len(data["venues"]) == 2

    def test_get_prices_token_not_found(self, client: TestClient) -> None:
        """Test 404 response when token doesn't exist."""
        with patch(
            "app.rwa_aggregator.presentation.api.prices._create_use_case"
        ) as mock_create:
            mock_use_case = AsyncMock()
            mock_use_case.execute.side_effect = TokenNotFoundError("INVALID")
            mock_create.return_value = mock_use_case

            response = client.get("/api/prices/INVALID")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    def test_get_prices_no_price_data(self, client: TestClient) -> None:
        """Test 404 response when no price data exists."""
        with patch(
            "app.rwa_aggregator.presentation.api.prices._create_use_case"
        ) as mock_create:
            mock_use_case = AsyncMock()
            mock_use_case.execute.side_effect = NoPriceDataError("USDY")
            mock_create.return_value = mock_use_case

            response = client.get("/api/prices/USDY")

            assert response.status_code == 404
            assert "no price data" in response.json()["detail"].lower()

    def test_get_prices_case_insensitive(
        self,
        client: TestClient,
        mock_aggregated_prices: AggregatedPricesDTO,
    ) -> None:
        """Test that token symbol is case-insensitive."""
        with patch(
            "app.rwa_aggregator.presentation.api.prices._create_use_case"
        ) as mock_create:
            mock_use_case = AsyncMock()
            mock_use_case.execute.return_value = mock_aggregated_prices
            mock_create.return_value = mock_use_case

            response = client.get("/api/prices/usdy")

            assert response.status_code == 200
            mock_use_case.execute.assert_called_once()
            call_args = mock_use_case.execute.call_args
            assert call_args.kwargs["base_symbol"] == "USDY"


class TestListAllPrices:
    """Tests for GET /api/prices."""

    def test_list_prices_success(
        self,
        client: TestClient,
        mock_aggregated_prices: AggregatedPricesDTO,
        mock_token: Token,
    ) -> None:
        """Test successful listing of all prices."""
        with (
            patch(
                "app.rwa_aggregator.presentation.api.prices.SqlTokenRepository"
            ) as mock_repo_class,
            patch(
                "app.rwa_aggregator.presentation.api.prices._create_use_case"
            ) as mock_create,
        ):
            # Setup mock token repository
            mock_repo = AsyncMock()
            mock_repo.get_all_active.return_value = [mock_token]
            mock_repo_class.return_value = mock_repo

            # Setup mock use case
            mock_use_case = AsyncMock()
            mock_use_case.execute.return_value = mock_aggregated_prices
            mock_create.return_value = mock_use_case

            response = client.get("/api/prices")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["base_token_symbol"] == "USDY"

    def test_list_prices_empty(self, client: TestClient) -> None:
        """Test empty list when no tokens exist."""
        with patch(
            "app.rwa_aggregator.presentation.api.prices.SqlTokenRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_all_active.return_value = []
            mock_repo_class.return_value = mock_repo

            response = client.get("/api/prices")

            assert response.status_code == 200
            assert response.json() == []

    def test_list_prices_skips_tokens_without_data(
        self,
        client: TestClient,
        mock_aggregated_prices: AggregatedPricesDTO,
        mock_token: Token,
    ) -> None:
        """Test that tokens without price data are skipped."""
        token_with_no_data = Token(
            id=2,
            symbol="OUSG",
            name="Ondo Short-Term US Gov Treasuries",
            category=TokenCategory.TBILL,
            issuer="Ondo Finance",
            is_active=True,
        )

        with (
            patch(
                "app.rwa_aggregator.presentation.api.prices.SqlTokenRepository"
            ) as mock_repo_class,
            patch(
                "app.rwa_aggregator.presentation.api.prices._create_use_case"
            ) as mock_create,
        ):
            mock_repo = AsyncMock()
            mock_repo.get_all_active.return_value = [mock_token, token_with_no_data]
            mock_repo_class.return_value = mock_repo

            mock_use_case = AsyncMock()
            # First call succeeds, second raises NoPriceDataError
            mock_use_case.execute.side_effect = [
                mock_aggregated_prices,
                NoPriceDataError("OUSG"),
            ]
            mock_create.return_value = mock_use_case

            response = client.get("/api/prices")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["base_token_symbol"] == "USDY"
