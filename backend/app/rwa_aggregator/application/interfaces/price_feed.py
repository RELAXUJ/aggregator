"""Price feed interface for fetching normalized price quotes from external venues."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class NormalizedQuote:
    """A normalized price quote from any venue.

    This dataclass provides a unified representation of price data
    regardless of the source (CEX, DEX, or issuer).

    Attributes:
        venue_name: Name of the venue providing the quote (e.g., "Kraken", "Coinbase").
        token_symbol: Normalized token symbol (e.g., "USDY", "PAXG").
        bid: Best bid price (highest buy offer).
        ask: Best ask price (lowest sell offer).
        volume_24h: 24-hour trading volume in quote currency.
        timestamp: When the quote was fetched.
    """

    venue_name: str
    token_symbol: str
    bid: Decimal
    ask: Decimal
    volume_24h: Optional[Decimal]
    timestamp: datetime

    @property
    def mid_price(self) -> Decimal:
        """Calculate the mid-market price."""
        return (self.bid + self.ask) / Decimal("2")

    @property
    def spread(self) -> Decimal:
        """Calculate the absolute spread (ask - bid)."""
        return self.ask - self.bid

    @property
    def spread_bps(self) -> Decimal:
        """Calculate the spread in basis points relative to mid price."""
        mid = self.mid_price
        if mid == 0:
            return Decimal("0")
        return (self.spread / mid) * Decimal("10000")


class PriceFeed(ABC):
    """Abstract base class for price feed implementations.

    Each price feed adapter (Kraken, Coinbase, Uniswap, etc.) must implement
    this interface to provide a unified way to fetch price quotes.
    """

    @property
    @abstractmethod
    def venue_name(self) -> str:
        """Return the name of this venue."""
        ...

    @abstractmethod
    async def fetch_quote(self, token_symbol: str) -> Optional[NormalizedQuote]:
        """Fetch a normalized price quote for the given token.

        Args:
            token_symbol: The normalized token symbol (e.g., "USDY", "PAXG").

        Returns:
            A NormalizedQuote if the token is supported and data is available,
            None if the token is not supported or an error occurred.
        """
        ...

    @abstractmethod
    def supports_token(self, token_symbol: str) -> bool:
        """Check if this feed supports the given token.

        Args:
            token_symbol: The normalized token symbol.

        Returns:
            True if the token is supported by this feed, False otherwise.
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close any open connections or resources."""
        ...
