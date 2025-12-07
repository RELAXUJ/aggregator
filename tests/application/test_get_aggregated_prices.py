"""Unit tests for GetAggregatedPricesUseCase."""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.rwa_aggregator.application.exceptions import NoPriceDataError, TokenNotFoundError
from app.rwa_aggregator.application.use_cases.get_aggregated_prices import (
    GetAggregatedPricesUseCase,
)
from app.rwa_aggregator.domain.entities.price_snapshot import PriceSnapshot
from app.rwa_aggregator.domain.entities.token import Token, TokenCategory
from app.rwa_aggregator.domain.entities.venue import ApiType, Venue, VenueType
from app.rwa_aggregator.domain.services.price_calculator import PriceCalculator


@pytest.fixture
def mock_token_repository() -> AsyncMock:
    """Create a mock token repository."""
    return AsyncMock()


@pytest.fixture
def mock_price_repository() -> AsyncMock:
    """Create a mock price repository."""
    return AsyncMock()


@pytest.fixture
def mock_venue_repository() -> AsyncMock:
    """Create a mock venue repository."""
    return AsyncMock()


@pytest.fixture
def price_calculator() -> PriceCalculator:
    """Create a real price calculator."""
    return PriceCalculator(max_staleness_seconds=60)


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
def sample_venues() -> dict[int, Venue]:
    """Create sample venues for testing."""
    return {
        1: Venue(
            id=1,
            name="Kraken",
            venue_type=VenueType.CEX,
            api_type=ApiType.REST,
            base_url="https://api.kraken.com",
            trade_url_template="https://kraken.com/trade/{symbol}",
            is_active=True,
        ),
        2: Venue(
            id=2,
            name="Coinbase",
            venue_type=VenueType.CEX,
            api_type=ApiType.REST,
            base_url="https://api.coinbase.com",
            trade_url_template="https://coinbase.com/trade/{symbol}",
            is_active=True,
        ),
    }


@pytest.fixture
def sample_snapshots() -> list[PriceSnapshot]:
    """Create sample price snapshots for testing."""
    now = datetime.now(timezone.utc)
    return [
        PriceSnapshot(
            id=1,
            token_id=1,
            venue_id=1,
            bid=Decimal("1.0010"),
            ask=Decimal("1.0015"),
            volume_24h=Decimal("1000000"),
            fetched_at=now,
        ),
        PriceSnapshot(
            id=2,
            token_id=1,
            venue_id=2,
            bid=Decimal("1.0012"),
            ask=Decimal("1.0018"),
            volume_24h=Decimal("500000"),
            fetched_at=now,
        ),
    ]


@pytest.fixture
def use_case(
    mock_token_repository: AsyncMock,
    mock_price_repository: AsyncMock,
    mock_venue_repository: AsyncMock,
    price_calculator: PriceCalculator,
) -> GetAggregatedPricesUseCase:
    """Create the use case with mocked dependencies."""
    return GetAggregatedPricesUseCase(
        token_repository=mock_token_repository,
        price_repository=mock_price_repository,
        venue_repository=mock_venue_repository,
        price_calculator=price_calculator,
    )


class TestGetAggregatedPricesUseCase:
    """Tests for GetAggregatedPricesUseCase."""

    @pytest.mark.asyncio
    async def test_execute_returns_aggregated_prices(
        self,
        use_case: GetAggregatedPricesUseCase,
        mock_token_repository: AsyncMock,
        mock_price_repository: AsyncMock,
        mock_venue_repository: AsyncMock,
        sample_token: Token,
        sample_venues: dict[int, Venue],
        sample_snapshots: list[PriceSnapshot],
    ) -> None:
        """Test successful aggregated price retrieval."""
        # Arrange
        mock_token_repository.get_by_symbol.return_value = sample_token
        mock_price_repository.get_latest_for_token.return_value = sample_snapshots
        mock_venue_repository.get_by_id.side_effect = lambda vid: sample_venues.get(vid)

        # Act
        result = await use_case.execute("USDY")

        # Assert
        assert result.base_token_symbol == "USDY"
        assert result.base_token_name == "Ondo US Dollar Yield"
        assert result.quote_token_symbol == "USD"
        assert result.num_venues == 2
        assert result.num_fresh_venues == 2
        assert len(result.venues) == 2

        # Best prices should be calculated correctly
        # Best bid is from Coinbase (1.0012), best ask is from Kraken (1.0015)
        assert result.best_prices.best_bid_price == Decimal("1.0012")
        assert result.best_prices.best_bid_venue == "Coinbase"
        assert result.best_prices.best_ask_price == Decimal("1.0015")
        assert result.best_prices.best_ask_venue == "Kraken"

    @pytest.mark.asyncio
    async def test_execute_raises_token_not_found(
        self,
        use_case: GetAggregatedPricesUseCase,
        mock_token_repository: AsyncMock,
    ) -> None:
        """Test that TokenNotFoundError is raised for unknown tokens."""
        # Arrange
        mock_token_repository.get_by_symbol.return_value = None

        # Act & Assert
        with pytest.raises(TokenNotFoundError) as exc_info:
            await use_case.execute("UNKNOWN")

        assert exc_info.value.symbol == "UNKNOWN"

    @pytest.mark.asyncio
    async def test_execute_raises_no_price_data(
        self,
        use_case: GetAggregatedPricesUseCase,
        mock_token_repository: AsyncMock,
        mock_price_repository: AsyncMock,
        sample_token: Token,
    ) -> None:
        """Test that NoPriceDataError is raised when no prices exist."""
        # Arrange
        mock_token_repository.get_by_symbol.return_value = sample_token
        mock_price_repository.get_latest_for_token.return_value = []

        # Act & Assert
        with pytest.raises(NoPriceDataError) as exc_info:
            await use_case.execute("USDY")

        assert exc_info.value.token_symbol == "USDY"

    @pytest.mark.asyncio
    async def test_execute_handles_missing_venue_metadata(
        self,
        use_case: GetAggregatedPricesUseCase,
        mock_token_repository: AsyncMock,
        mock_price_repository: AsyncMock,
        mock_venue_repository: AsyncMock,
        sample_token: Token,
        sample_snapshots: list[PriceSnapshot],
    ) -> None:
        """Test graceful handling when venue metadata is missing."""
        # Arrange
        mock_token_repository.get_by_symbol.return_value = sample_token
        mock_price_repository.get_latest_for_token.return_value = sample_snapshots
        mock_venue_repository.get_by_id.return_value = None  # No venue found

        # Act
        result = await use_case.execute("USDY")

        # Assert - should use fallback venue names
        assert result.num_venues == 2
        assert any("Venue" in v.venue_name for v in result.venues)

    @pytest.mark.asyncio
    async def test_execute_excludes_stale_when_requested(
        self,
        mock_token_repository: AsyncMock,
        mock_price_repository: AsyncMock,
        mock_venue_repository: AsyncMock,
        sample_token: Token,
        sample_venues: dict[int, Venue],
    ) -> None:
        """Test that stale venues are excluded when include_stale=False."""
        # Arrange - create one fresh and one stale snapshot
        now = datetime.now(timezone.utc)
        from datetime import timedelta

        snapshots = [
            PriceSnapshot(
                id=1,
                token_id=1,
                venue_id=1,
                bid=Decimal("1.0010"),
                ask=Decimal("1.0015"),
                fetched_at=now,  # Fresh
            ),
            PriceSnapshot(
                id=2,
                token_id=1,
                venue_id=2,
                bid=Decimal("1.0012"),
                ask=Decimal("1.0018"),
                fetched_at=now - timedelta(seconds=120),  # Stale (> 60s)
            ),
        ]

        mock_token_repository.get_by_symbol.return_value = sample_token
        mock_price_repository.get_latest_for_token.return_value = snapshots
        mock_venue_repository.get_by_id.side_effect = lambda vid: sample_venues.get(vid)

        use_case = GetAggregatedPricesUseCase(
            token_repository=mock_token_repository,
            price_repository=mock_price_repository,
            venue_repository=mock_venue_repository,
            max_staleness_seconds=60,
        )

        # Act
        result = await use_case.execute("USDY", include_stale=False)

        # Assert - only fresh venue should be included
        assert result.num_venues == 1
        assert result.venues[0].venue_name == "Kraken"

    @pytest.mark.asyncio
    async def test_venues_sorted_by_bid_descending(
        self,
        use_case: GetAggregatedPricesUseCase,
        mock_token_repository: AsyncMock,
        mock_price_repository: AsyncMock,
        mock_venue_repository: AsyncMock,
        sample_token: Token,
        sample_venues: dict[int, Venue],
        sample_snapshots: list[PriceSnapshot],
    ) -> None:
        """Test that venue list is sorted by bid price (highest first)."""
        # Arrange
        mock_token_repository.get_by_symbol.return_value = sample_token
        mock_price_repository.get_latest_for_token.return_value = sample_snapshots
        mock_venue_repository.get_by_id.side_effect = lambda vid: sample_venues.get(vid)

        # Act
        result = await use_case.execute("USDY")

        # Assert - Coinbase has higher bid (1.0012) so should be first
        assert result.venues[0].venue_name == "Coinbase"
        assert result.venues[1].venue_name == "Kraken"
