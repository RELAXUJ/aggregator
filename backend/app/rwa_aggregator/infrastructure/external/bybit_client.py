"""Bybit REST API client for fetching price quotes.

Bybit V5 API documentation: https://bybit-exchange.github.io/docs/v5/intro
Public endpoint rate limit: 10 requests/second per IP.
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

# Mapping from normalized token symbols to Bybit spot trading pairs
# Bybit uses concatenated pairs like "BTCUSDT"
BYBIT_SYMBOL_MAP: dict[str, str] = {
    # RWA tokens - primary focus
    "USDY": "USDYUSDT",  # Ondo US Dollar Yield
    # Major cryptocurrencies
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "XRP": "XRPUSDT",
    "SOL": "SOLUSDT",
    "AVAX": "AVAXUSDT",
    "DOT": "DOTUSDT",
    "LINK": "LINKUSDT",
    "MATIC": "MATICUSDT",
    "ATOM": "ATOMUSDT",
    # Stablecoins
    "USDC": "USDCUSDT",
    "DAI": "DAIUSDT",
    # Gold-backed tokens
    "PAXG": "PAXGUSDT",
}

# Default timeout for HTTP requests
DEFAULT_TIMEOUT_SECONDS = 10.0


class BybitClient(PriceFeed):
    """Bybit V5 API client implementing the PriceFeed interface.

    This client fetches real-time ticker data from Bybit's public V5 API.
    No authentication required for public market data endpoints.

    Attributes:
        _client: httpx AsyncClient for making HTTP requests.
        _base_url: Bybit API base URL.
    """

    def __init__(
        self,
        base_url: str = "https://api.bybit.com",
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        """Initialize the Bybit client.

        Args:
            base_url: Bybit API base URL.
            timeout: HTTP request timeout in seconds.
        """
        self._base_url = base_url.rstrip("/")
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
        return "Bybit"

    def supports_token(self, token_symbol: str) -> bool:
        """Check if Bybit supports the given token.

        Args:
            token_symbol: Normalized token symbol.

        Returns:
            True if the token has a Bybit pair mapping.
        """
        return token_symbol.upper() in BYBIT_SYMBOL_MAP

    async def fetch_quote(self, token_symbol: str) -> Optional[NormalizedQuote]:
        """Fetch a price quote from Bybit for the given token.

        Uses the V5 public market/tickers endpoint (no auth required).

        Args:
            token_symbol: Normalized token symbol (e.g., "USDY", "BTC", "ETH").

        Returns:
            NormalizedQuote with bid, ask, and volume data, or None if unavailable.
        """
        symbol_upper = token_symbol.upper()
        bybit_symbol = BYBIT_SYMBOL_MAP.get(symbol_upper)

        if not bybit_symbol:
            logger.debug(f"Bybit does not support token: {token_symbol}")
            return None

        try:
            # Use V5 public market tickers endpoint
            response = await self._client.get(
                "/v5/market/tickers",
                params={
                    "category": "spot",
                    "symbol": bybit_symbol,
                },
            )
            response.raise_for_status()
            data = response.json()

            # Check for API errors
            if data.get("retCode") != 0:
                logger.error(f"Bybit API error: {data.get('retMsg')}")
                return None

            result_list = data.get("result", {}).get("list", [])
            if not result_list:
                logger.warning(f"No ticker data in Bybit response for {bybit_symbol}")
                return None

            ticker = result_list[0]

            # V5 response format:
            # {
            #   "symbol": "USDYUSDT",
            #   "bid1Price": "1.0265",
            #   "bid1Size": "17913.46",
            #   "ask1Price": "1.0266",
            #   "ask1Size": "2149.5",
            #   "volume24h": "67823.74",
            #   "turnover24h": "69634.12",
            #   ...
            # }
            bid = ticker.get("bid1Price")
            ask = ticker.get("ask1Price")
            volume = ticker.get("volume24h")

            if not bid or not ask:
                logger.warning(f"Missing bid/ask in Bybit response for {bybit_symbol}")
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
            logger.error(f"Timeout fetching Bybit quote for {token_symbol}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching Bybit quote: {e.response.status_code}")
            return None
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing Bybit response for {token_symbol}: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error fetching Bybit quote for {token_symbol}: {e}")
            return None

    async def fetch_order_book(
        self, token_symbol: str, limit: int = 50
    ) -> Optional[dict]:
        """Fetch order book data for deeper liquidity analysis.

        Args:
            token_symbol: Normalized token symbol.
            limit: Number of price levels to fetch (default 50, max 200).

        Returns:
            Dictionary with 'bids' and 'asks' lists, or None if unavailable.
        """
        symbol_upper = token_symbol.upper()
        bybit_symbol = BYBIT_SYMBOL_MAP.get(symbol_upper)

        if not bybit_symbol:
            return None

        try:
            response = await self._client.get(
                "/v5/market/orderbook",
                params={
                    "category": "spot",
                    "symbol": bybit_symbol,
                    "limit": min(limit, 200),
                },
            )
            response.raise_for_status()
            data = response.json()

            if data.get("retCode") != 0:
                logger.error(f"Bybit API error: {data.get('retMsg')}")
                return None

            result = data.get("result", {})
            return {
                "bids": result.get("b", []),  # [[price, size], ...]
                "asks": result.get("a", []),
                "timestamp": result.get("ts"),
            }

        except Exception as e:
            logger.error(f"Error fetching Bybit order book for {token_symbol}: {e}")
            return None

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> "BybitClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
