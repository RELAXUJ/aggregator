"""Use case for fetching aggregated prices across all venues.

Implements the main dashboard data retrieval by orchestrating:
- Token validation via TokenRepository
- Price snapshot loading via PriceRepository
- Venue metadata via VenueRepository
- Best price calculation via PriceCalculator domain service
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from app.rwa_aggregator.application.dto.price_dto import (
    AggregatedPricesDTO,
    BestPriceDTO,
    VenuePriceDTO,
)
from app.rwa_aggregator.application.exceptions import (
    NoPriceDataError,
    TokenNotFoundError,
)
from app.rwa_aggregator.domain.entities.price_snapshot import PriceSnapshot
from app.rwa_aggregator.domain.entities.venue import Venue
from app.rwa_aggregator.domain.repositories.price_repository import PriceRepository
from app.rwa_aggregator.domain.repositories.token_repository import TokenRepository
from app.rwa_aggregator.domain.repositories.venue_repository import VenueRepository
from app.rwa_aggregator.domain.services.price_calculator import BestPrices, PriceCalculator


class GetAggregatedPricesUseCase:
    """Application service for retrieving aggregated price data.

    This use case orchestrates the retrieval and aggregation of price
    data from multiple venues, providing the dashboard with a unified
    view of token prices and best execution opportunities.
    """

    def __init__(
        self,
        token_repository: TokenRepository,
        price_repository: PriceRepository,
        venue_repository: VenueRepository,
        price_calculator: Optional[PriceCalculator] = None,
        max_staleness_seconds: int = 60,
    ) -> None:
        """Initialize the use case with required dependencies.

        Args:
            token_repository: Repository for token data access.
            price_repository: Repository for price snapshot access.
            venue_repository: Repository for venue data access.
            price_calculator: Domain service for best price calculation.
                If not provided, a default instance will be created.
            max_staleness_seconds: Maximum age for fresh prices (default 60s).
        """
        self._token_repository = token_repository
        self._price_repository = price_repository
        self._venue_repository = venue_repository
        self._price_calculator = price_calculator or PriceCalculator(max_staleness_seconds)
        self._max_staleness_seconds = max_staleness_seconds

    async def execute(
        self,
        base_symbol: str,
        quote_symbol: str = "USD",
        include_stale: bool = True,
    ) -> AggregatedPricesDTO:
        """Execute the aggregated prices retrieval.

        Args:
            base_symbol: The base token symbol (e.g., "USDY").
            quote_symbol: The quote token symbol (default "USD").
            include_stale: Whether to include stale venues in the response.

        Returns:
            AggregatedPricesDTO with best prices and per-venue breakdown.

        Raises:
            TokenNotFoundError: If the base token symbol is not recognized.
            NoPriceDataError: If no price data exists for the token.
        """
        # 1. Validate and fetch the token
        token = await self._token_repository.get_by_symbol(base_symbol)
        if token is None or token.id is None:
            raise TokenNotFoundError(base_symbol)

        # 2. Fetch all latest price snapshots for this token
        snapshots = await self._price_repository.get_latest_for_token(token.id)

        if not snapshots:
            raise NoPriceDataError(base_symbol)

        # 3. Load venue metadata for all venues with price data
        venue_ids = {s.venue_id for s in snapshots}
        venues_by_id: dict[int, Venue] = {}
        for venue_id in venue_ids:
            venue = await self._venue_repository.get_by_id(venue_id)
            if venue:
                venues_by_id[venue_id] = venue

        # 4. Calculate best prices using the domain service
        best_prices = self._price_calculator.calculate_best_prices(snapshots)

        # 5. Build venue price DTOs
        venue_dtos = self._build_venue_dtos(
            snapshots=snapshots,
            venues_by_id=venues_by_id,
            base_symbol=base_symbol,
            quote_symbol=quote_symbol,
            include_stale=include_stale,
        )

        # 6. Build best price DTO
        best_price_dto = self._build_best_price_dto(
            best_prices=best_prices,
            venues_by_id=venues_by_id,
            base_symbol=base_symbol,
            quote_symbol=quote_symbol,
        )

        # 7. Determine the most recent update timestamp
        last_updated = max(s.fetched_at for s in snapshots)

        # 8. Count fresh venues
        num_fresh = sum(
            1 for s in snapshots
            if not s.is_stale(self._max_staleness_seconds)
        )

        return AggregatedPricesDTO(
            base_token_symbol=base_symbol,
            base_token_name=token.name,
            quote_token_symbol=quote_symbol,
            best_prices=best_price_dto,
            venues=venue_dtos,
            num_venues=len(venue_dtos),
            num_fresh_venues=num_fresh,
            last_updated=last_updated,
        )

    def _build_venue_dtos(
        self,
        snapshots: list[PriceSnapshot],
        venues_by_id: dict[int, Venue],
        base_symbol: str,
        quote_symbol: str,
        include_stale: bool,
    ) -> list[VenuePriceDTO]:
        """Build VenuePriceDTO list from snapshots and venue metadata.

        Args:
            snapshots: List of price snapshots.
            venues_by_id: Mapping of venue ID to Venue entity.
            base_symbol: Base token symbol.
            quote_symbol: Quote token symbol.
            include_stale: Whether to include stale snapshots.

        Returns:
            List of VenuePriceDTO objects sorted by bid (highest first).
        """
        venue_dtos: list[VenuePriceDTO] = []

        for snapshot in snapshots:
            is_stale = snapshot.is_stale(self._max_staleness_seconds)

            # Skip stale if not requested
            if is_stale and not include_stale:
                continue

            venue = venues_by_id.get(snapshot.venue_id)
            venue_name = venue.name if venue else f"Venue {snapshot.venue_id}"
            trade_url = venue.get_trade_url(base_symbol) if venue else None

            # Calculate spread metrics
            mid_price = snapshot.mid
            spread = snapshot.ask - snapshot.bid
            spread_bps = (spread / mid_price * Decimal("10000")) if mid_price > 0 else Decimal("0")

            venue_dtos.append(
                VenuePriceDTO(
                    venue_name=venue_name,
                    venue_id=snapshot.venue_id,
                    base_token_symbol=base_symbol,
                    quote_token_symbol=quote_symbol,
                    bid=snapshot.bid,
                    ask=snapshot.ask,
                    mid_price=mid_price,
                    spread=spread,
                    spread_bps=spread_bps.quantize(Decimal("0.01")),
                    volume_24h=snapshot.volume_24h,
                    timestamp=snapshot.fetched_at,
                    is_stale=is_stale,
                    trade_url=trade_url,
                )
            )

        # Sort by bid price (highest first) for best execution visibility
        venue_dtos.sort(key=lambda v: v.bid, reverse=True)
        return venue_dtos

    def _build_best_price_dto(
        self,
        best_prices: BestPrices,
        venues_by_id: dict[int, Venue],
        base_symbol: str,
        quote_symbol: str,
    ) -> BestPriceDTO:
        """Build BestPriceDTO from calculated best prices.

        Args:
            best_prices: Result from PriceCalculator.
            venues_by_id: Mapping of venue ID to Venue entity.
            base_symbol: Base token symbol.
            quote_symbol: Quote token symbol.

        Returns:
            BestPriceDTO with best bid/ask information.
        """
        # Extract best bid venue info
        best_bid_venue: Optional[str] = None
        best_bid_venue_id: Optional[int] = None
        best_bid_price: Optional[Decimal] = None

        if best_prices.best_bid:
            best_bid_price = best_prices.best_bid.bid
            best_bid_venue_id = best_prices.best_bid.venue_id
            venue = venues_by_id.get(best_prices.best_bid.venue_id)
            best_bid_venue = venue.name if venue else f"Venue {best_bid_venue_id}"

        # Extract best ask venue info
        best_ask_venue: Optional[str] = None
        best_ask_venue_id: Optional[int] = None
        best_ask_price: Optional[Decimal] = None

        if best_prices.best_ask:
            best_ask_price = best_prices.best_ask.ask
            best_ask_venue_id = best_prices.best_ask.venue_id
            venue = venues_by_id.get(best_prices.best_ask.venue_id)
            best_ask_venue = venue.name if venue else f"Venue {best_ask_venue_id}"

        # Calculate effective spread in basis points
        effective_spread_pct: Optional[Decimal] = None
        effective_spread_bps: Optional[Decimal] = None

        if best_prices.effective_spread:
            effective_spread_pct = best_prices.effective_spread.percentage
            # Convert percentage to basis points (1% = 100 bps)
            effective_spread_bps = effective_spread_pct * Decimal("100")

        return BestPriceDTO(
            base_token_symbol=base_symbol,
            quote_token_symbol=quote_symbol,
            best_bid_venue=best_bid_venue,
            best_bid_venue_id=best_bid_venue_id,
            best_bid_price=best_bid_price,
            best_ask_venue=best_ask_venue,
            best_ask_venue_id=best_ask_venue_id,
            best_ask_price=best_ask_price,
            effective_spread_pct=effective_spread_pct,
            effective_spread_bps=effective_spread_bps,
        )
