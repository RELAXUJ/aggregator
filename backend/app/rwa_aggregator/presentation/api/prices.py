"""Price aggregation API endpoints."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Path, Query
from pydantic import BaseModel

router = APIRouter()


class VenuePrice(BaseModel):
    """Price data from a single venue."""

    venue: str
    venue_type: str  # CEX, DEX, ISSUER
    bid: Decimal | None
    ask: Decimal | None
    mid: Decimal | None
    timestamp: datetime
    is_stale: bool = False


class AggregatedPriceResponse(BaseModel):
    """Aggregated price response across all venues."""

    token_symbol: str
    best_bid: Decimal | None
    best_bid_venue: str | None
    best_ask: Decimal | None
    best_ask_venue: str | None
    mid_price: Decimal | None
    spread_bps: Decimal | None
    venue_count: int
    venues: list[VenuePrice]
    aggregated_at: datetime


@router.get("/prices/{token_symbol}", response_model=AggregatedPriceResponse)
async def get_aggregated_prices(
    token_symbol: Annotated[str, Path(description="Token symbol (e.g., USDC, PAXG)")],
    include_stale: Annotated[bool, Query(description="Include stale prices")] = False,
) -> AggregatedPriceResponse:
    """Get aggregated prices for a token across all venues.

    Args:
        token_symbol: The token symbol to query.
        include_stale: Whether to include prices older than staleness threshold.

    Returns:
        Aggregated price data with best bid/ask and per-venue breakdown.
    """
    # TODO: Replace with actual use case call
    # This is placeholder data for initial testing

    now = datetime.now(timezone.utc)

    # Mock venue data for skeleton validation
    mock_venues = [
        VenuePrice(
            venue="Kraken",
            venue_type="CEX",
            bid=Decimal("0.9998"),
            ask=Decimal("1.0002"),
            mid=Decimal("1.0000"),
            timestamp=now,
            is_stale=False,
        ),
        VenuePrice(
            venue="Coinbase",
            venue_type="CEX",
            bid=Decimal("0.9997"),
            ask=Decimal("1.0001"),
            mid=Decimal("0.9999"),
            timestamp=now,
            is_stale=False,
        ),
    ]

    return AggregatedPriceResponse(
        token_symbol=token_symbol.upper(),
        best_bid=Decimal("0.9998"),
        best_bid_venue="Kraken",
        best_ask=Decimal("1.0001"),
        best_ask_venue="Coinbase",
        mid_price=Decimal("0.99995"),
        spread_bps=Decimal("3.0"),
        venue_count=len(mock_venues),
        venues=mock_venues,
        aggregated_at=now,
    )


@router.get("/prices", response_model=list[AggregatedPriceResponse])
async def list_all_prices() -> list[AggregatedPriceResponse]:
    """Get aggregated prices for all tracked tokens.

    Returns:
        List of aggregated price data for each tracked token.
    """
    # TODO: Replace with actual use case call
    # This calls the single-token endpoint for each tracked token

    tokens = ["USDC", "PAXG", "ONDO"]
    results = []

    for token in tokens:
        result = await get_aggregated_prices(token)
        results.append(result)

    return results
