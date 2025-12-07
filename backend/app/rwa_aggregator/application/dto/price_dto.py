"""Data Transfer Objects for price-related API responses.

These DTOs represent the external contract for price data exposed
through the API layer. They are decoupled from domain entities and
optimized for JSON serialization.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class VenuePriceDTO(BaseModel):
    """Price data from a single venue for a token pair.

    Represents the per-venue pricing information displayed in the
    dashboard's venue comparison table.
    """

    model_config = ConfigDict(
        json_encoders={Decimal: lambda v: float(v)},
        ser_json_timedelta="float",
    )

    venue_name: str = Field(description="Display name of the venue (e.g., 'Kraken', 'Coinbase')")
    venue_id: int = Field(description="Internal venue identifier")
    base_token_symbol: str = Field(description="Base token symbol (e.g., 'USDY')")
    quote_token_symbol: str = Field(default="USD", description="Quote token symbol (e.g., 'USD')")
    bid: Decimal = Field(description="Best bid price (highest buy offer)")
    ask: Decimal = Field(description="Best ask price (lowest sell offer)")
    mid_price: Decimal = Field(description="Mid-market price ((bid + ask) / 2)")
    spread: Decimal = Field(description="Absolute spread (ask - bid)")
    spread_bps: Decimal = Field(description="Spread in basis points relative to mid price")
    volume_24h: Optional[Decimal] = Field(default=None, description="24-hour trading volume in quote currency")
    timestamp: datetime = Field(description="When the price was fetched (UTC)")
    is_stale: bool = Field(default=False, description="Whether the price is considered stale (> 60s old)")
    trade_url: Optional[str] = Field(default=None, description="Direct link to trade on this venue")


class BestPriceDTO(BaseModel):
    """Best bid and ask prices across all venues.

    Summarizes the best execution opportunities for a token pair,
    identifying which venues offer the best prices.
    """

    model_config = ConfigDict(
        json_encoders={Decimal: lambda v: float(v)},
    )

    base_token_symbol: str = Field(description="Base token symbol")
    quote_token_symbol: str = Field(default="USD", description="Quote token symbol")
    best_bid_venue: Optional[str] = Field(default=None, description="Venue with the highest bid")
    best_bid_venue_id: Optional[int] = Field(default=None, description="ID of venue with the highest bid")
    best_bid_price: Optional[Decimal] = Field(default=None, description="Highest bid price across venues")
    best_ask_venue: Optional[str] = Field(default=None, description="Venue with the lowest ask")
    best_ask_venue_id: Optional[int] = Field(default=None, description="ID of venue with the lowest ask")
    best_ask_price: Optional[Decimal] = Field(default=None, description="Lowest ask price across venues")
    effective_spread_pct: Optional[Decimal] = Field(
        default=None,
        description="Spread between best bid and best ask as percentage"
    )
    effective_spread_bps: Optional[Decimal] = Field(
        default=None,
        description="Spread between best bid and best ask in basis points"
    )


class AggregatedPricesDTO(BaseModel):
    """Complete aggregated price data for a token pair.

    Top-level response model for the dashboard's main price display,
    combining best prices with per-venue breakdowns.
    """

    model_config = ConfigDict(
        json_encoders={Decimal: lambda v: float(v)},
    )

    base_token_symbol: str = Field(description="Base token symbol being priced")
    base_token_name: str = Field(description="Human-readable base token name")
    quote_token_symbol: str = Field(default="USD", description="Quote token symbol")
    best_prices: BestPriceDTO = Field(description="Best bid/ask summary across venues")
    venues: list[VenuePriceDTO] = Field(default_factory=list, description="Per-venue price breakdown")
    num_venues: int = Field(description="Total number of venues with price data")
    num_fresh_venues: int = Field(description="Number of venues with non-stale data")
    last_updated: datetime = Field(description="Most recent price update timestamp")
