"""Price aggregation API endpoints."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query
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

    Raises:
        HTTPException: 501 if price aggregation use case is not yet implemented.
    """
    # Use case not yet implemented - raise explicit error per .cursorrules
    raise HTTPException(
        status_code=501,
        detail=f"Price aggregation for {token_symbol.upper()} not yet implemented. "
        "Requires: GetAggregatedPrices use case, PriceRepository, and venue clients.",
    )


@router.get("/prices", response_model=list[AggregatedPriceResponse])
async def list_all_prices(
    include_stale: Annotated[bool, Query(description="Include stale prices")] = False,
) -> list[AggregatedPriceResponse]:
    """Get aggregated prices for all tracked tokens.

    Returns:
        List of aggregated price data for each tracked token.

    Raises:
        HTTPException: 501 if price listing use case is not yet implemented.
    """
    # Use case not yet implemented - raise explicit error per .cursorrules
    raise HTTPException(
        status_code=501,
        detail="Price listing not yet implemented. "
        "Requires: ListAllPrices use case, TokenRepository, and PriceRepository.",
    )
