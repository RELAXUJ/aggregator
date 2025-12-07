"""Venue entity representing a trading platform or exchange."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class VenueType(Enum):
    """Types of trading venues."""

    CEX = "cex"
    DEX = "dex"
    ISSUER = "issuer"


class ApiType(Enum):
    """Types of APIs used to fetch price data."""

    REST = "rest"
    WEBSOCKET = "websocket"
    SUBGRAPH = "subgraph"


@dataclass
class Venue:
    """Domain entity representing a price source venue.

    Attributes:
        id: Database identifier (None for unsaved entities).
        name: Venue display name (e.g., Kraken, Uniswap V3).
        venue_type: Type of venue (CEX, DEX, or issuer).
        api_type: Type of API used to fetch data.
        base_url: Base URL for the venue's API.
        trade_url_template: URL template for trading links with {symbol} placeholder.
        is_active: Whether the venue is actively polled.
    """

    id: Optional[int]
    name: str
    venue_type: VenueType
    api_type: ApiType
    base_url: str
    trade_url_template: Optional[str] = None
    is_active: bool = True

    def get_trade_url(self, token_symbol: str) -> Optional[str]:
        """Generate a trading URL for a specific token.

        Args:
            token_symbol: The token symbol to include in the URL.

        Returns:
            The formatted trade URL, or None if no template is configured.
        """
        if self.trade_url_template:
            return self.trade_url_template.format(symbol=token_symbol)
        return None

    def deactivate(self) -> None:
        """Mark the venue as inactive (stop polling)."""
        self.is_active = False

    def activate(self) -> None:
        """Mark the venue as active (resume polling)."""
        self.is_active = True
