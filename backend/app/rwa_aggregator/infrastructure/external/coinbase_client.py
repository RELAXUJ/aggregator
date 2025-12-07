"""Coinbase REST API client for fetching price quotes.

Uses the public Coinbase Exchange API for market data (no auth required).
For authenticated endpoints, use CDP JWT authentication.

Public API: https://api.exchange.coinbase.com
Rate limit: 3-10 requests/second per IP.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import httpx

from app.rwa_aggregator.application.interfaces.price_feed import (
    NormalizedQuote,
    PriceFeed,
)

logger = logging.getLogger(__name__)

# Mapping from normalized token symbols to Coinbase product IDs
# Coinbase uses hyphenated pairs like "BTC-USD"
COINBASE_SYMBOL_MAP: dict[str, str] = {
    # Major cryptocurrencies
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "XRP": "XRP-USD",
    "SOL": "SOL-USD",
    "AVAX": "AVAX-USD",
    "DOT": "DOT-USD",
    "LINK": "LINK-USD",
    "MATIC": "MATIC-USD",
    "ATOM": "ATOM-USD",
    "LTC": "LTC-USD",
    "ADA": "ADA-USD",
    # Stablecoins (note: USDC has no USD pair as it IS USD-pegged)
    "USDT": "USDT-USD",
    "DAI": "DAI-USD",
    # RWA-related tokens
    "PAXG": "PAXG-USD",  # Paxos Gold
    # Add more as needed
}

# Default timeout for HTTP requests
DEFAULT_TIMEOUT_SECONDS = 10.0


class CoinbaseClient(PriceFeed):
    """Coinbase Exchange API client implementing the PriceFeed interface.

    This client fetches real-time ticker data from Coinbase's public Exchange API.
    No authentication required for public market data endpoints.

    Attributes:
        _client: httpx AsyncClient for making HTTP requests.
        _base_url: Coinbase Exchange API base URL.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        base_url: str = "https://api.exchange.coinbase.com",
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        """Initialize the Coinbase client.

        Args:
            api_key: Optional API key (stored for future authenticated requests).
            api_secret: Optional API secret (stored for future authenticated requests).
            base_url: Coinbase Exchange API base URL.
            timeout: HTTP request timeout in seconds.
        """
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._api_secret = api_secret
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
            headers={
                "Accept": "application/json",
                "User-Agent": "RWA-Aggregator/1.0",
            },
        )

    @property
    def venue_name(self) -> str:
        """Return the venue name."""
        return "Coinbase"

    def supports_token(self, token_symbol: str) -> bool:
        """Check if Coinbase supports the given token.

        Args:
            token_symbol: Normalized token symbol.

        Returns:
            True if the token has a Coinbase product mapping.
        """
        return token_symbol.upper() in COINBASE_SYMBOL_MAP

    async def fetch_quote(self, token_symbol: str) -> Optional[NormalizedQuote]:
        """Fetch a price quote from Coinbase for the given token.

        Uses the public Exchange API ticker endpoint (no auth required).

        Args:
            token_symbol: Normalized token symbol (e.g., "BTC", "ETH", "PAXG").

        Returns:
            NormalizedQuote with bid, ask, and volume data, or None if unavailable.
        """
        symbol_upper = token_symbol.upper()
        product_id = COINBASE_SYMBOL_MAP.get(symbol_upper)

        if not product_id:
            logger.debug(f"Coinbase does not support token: {token_symbol}")
            return None

        try:
            # Use the public Exchange API ticker endpoint
            response = await self._client.get(f"/products/{product_id}/ticker")
            response.raise_for_status()
            data = response.json()

            # Response format from /products/{id}/ticker:
            # {"trade_id": 123, "price": "50000.00", "size": "0.001",
            #  "bid": "49999.00", "ask": "50001.00", "volume": "1234.56", "time": "..."}
            bid = data.get("bid")
            ask = data.get("ask")
            volume = data.get("volume")

            if not bid or not ask:
                logger.warning(f"Missing bid/ask in Coinbase response for {product_id}")
                return None

            bid_price = Decimal(str(bid))
            ask_price = Decimal(str(ask))
            volume_24h = Decimal(str(volume)) if volume else None

            return NormalizedQuote(
                venue_name=self.venue_name,
                token_symbol=symbol_upper,
                bid=bid_price,
                ask=ask_price,
                volume_24h=volume_24h,
                timestamp=datetime.now(timezone.utc),
            )

        except httpx.TimeoutException:
            logger.error(f"Timeout fetching Coinbase quote for {token_symbol}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching Coinbase quote: {e.response.status_code}")
            return None
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing Coinbase response for {token_symbol}: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error fetching Coinbase quote for {token_symbol}: {e}")
            return None

    async def fetch_order_book(
        self, token_symbol: str, limit: int = 50
    ) -> Optional[dict]:
        """Fetch order book data for deeper liquidity analysis.

        Args:
            token_symbol: Normalized token symbol.
            limit: Number of price levels to fetch (default 50).

        Returns:
            Dictionary with 'bids' and 'asks' lists, or None if unavailable.
        """
        symbol_upper = token_symbol.upper()
        product_id = COINBASE_SYMBOL_MAP.get(symbol_upper)

        if not product_id:
            return None

        try:
            # Level 2 order book (aggregated)
            response = await self._client.get(
                f"/products/{product_id}/book",
                params={"level": 2},
            )
            response.raise_for_status()
            data = response.json()

            return {
                "bids": data.get("bids", [])[:limit],
                "asks": data.get("asks", [])[:limit],
                "sequence": data.get("sequence"),
            }

        except Exception as e:
            logger.error(f"Error fetching Coinbase order book for {token_symbol}: {e}")
            return None

    async def fetch_24h_stats(self, token_symbol: str) -> Optional[dict]:
        """Fetch 24-hour statistics for a product.

        Args:
            token_symbol: Normalized token symbol.

        Returns:
            Dictionary with 24h stats, or None if unavailable.
        """
        symbol_upper = token_symbol.upper()
        product_id = COINBASE_SYMBOL_MAP.get(symbol_upper)

        if not product_id:
            return None

        try:
            response = await self._client.get(f"/products/{product_id}/stats")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching Coinbase 24h stats for {token_symbol}: {e}")
            return None

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> "CoinbaseClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
