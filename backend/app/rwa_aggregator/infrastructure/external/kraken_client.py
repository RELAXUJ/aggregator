"""Kraken REST API client for fetching price quotes.

Kraken API documentation: https://docs.kraken.com/rest/
Public endpoint rate limit: ~1 request per second.
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

# Mapping from normalized token symbols to Kraken trading pairs
# Kraken uses their own pair naming convention (e.g., XXBTZUSD for BTC/USD)
KRAKEN_SYMBOL_MAP: dict[str, str] = {
    # Major cryptocurrencies
    "BTC": "XXBTZUSD",
    "ETH": "XETHZUSD",
    "XRP": "XXRPZUSD",
    "SOL": "SOLUSD",
    "AVAX": "AVAXUSD",
    "DOT": "DOTUSD",
    "LINK": "LINKUSD",
    "MATIC": "MATICUSD",
    "ATOM": "ATOMUSD",
    # Stablecoins
    "USDT": "USDTZUSD",
    "USDC": "USDCUSD",
    "DAI": "DAIUSD",
    "EURC": "EURCEUR",
    # RWA tokens (if listed on Kraken)
    "PAXG": "PAXGUSD",  # Paxos Gold
    "USDY": "USDYUSD",  # Ondo USDY (if listed)
    # Euro pairs
    "EURZ": "EURZEUR",
}

# Default timeout for HTTP requests
DEFAULT_TIMEOUT_SECONDS = 10.0


class KrakenClient(PriceFeed):
    """Kraken REST API client implementing the PriceFeed interface.

    This client fetches real-time ticker data from Kraken's public API.
    No authentication is required for public market data endpoints.

    Attributes:
        _client: httpx AsyncClient for making HTTP requests.
        _base_url: Kraken API base URL.
    """

    def __init__(
        self,
        base_url: str = "https://api.kraken.com",
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        """Initialize the Kraken client.

        Args:
            base_url: Kraken API base URL.
            timeout: HTTP request timeout in seconds.
        """
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
            headers={"Accept": "application/json"},
        )

    @property
    def venue_name(self) -> str:
        """Return the venue name."""
        return "Kraken"

    def supports_token(self, token_symbol: str) -> bool:
        """Check if Kraken supports the given token.

        Args:
            token_symbol: Normalized token symbol.

        Returns:
            True if the token has a Kraken pair mapping.
        """
        return token_symbol.upper() in KRAKEN_SYMBOL_MAP

    async def fetch_quote(self, token_symbol: str) -> Optional[NormalizedQuote]:
        """Fetch a price quote from Kraken for the given token.

        Args:
            token_symbol: Normalized token symbol (e.g., "BTC", "ETH", "PAXG").

        Returns:
            NormalizedQuote with bid, ask, and volume data, or None if unavailable.
        """
        symbol_upper = token_symbol.upper()
        kraken_pair = KRAKEN_SYMBOL_MAP.get(symbol_upper)

        if not kraken_pair:
            logger.debug(f"Kraken does not support token: {token_symbol}")
            return None

        try:
            response = await self._client.get(
                "/0/public/Ticker",
                params={"pair": kraken_pair},
            )
            response.raise_for_status()
            data = response.json()

            # Check for API errors
            if data.get("error") and len(data["error"]) > 0:
                logger.error(f"Kraken API error: {data['error']}")
                return None

            result = data.get("result", {})
            if not result:
                logger.warning(f"No result in Kraken response for {kraken_pair}")
                return None

            # The result key may not exactly match the request pair
            # (Kraken sometimes returns different key formats)
            ticker_data = None
            for key in result:
                ticker_data = result[key]
                break

            if not ticker_data:
                logger.warning(f"No ticker data in Kraken response for {kraken_pair}")
                return None

            # Extract bid, ask, and volume from Kraken response format:
            # a: [ask_price, whole_lot_volume, lot_volume]
            # b: [bid_price, whole_lot_volume, lot_volume]
            # v: [today_volume, 24h_volume]
            ask_price = Decimal(ticker_data["a"][0])
            bid_price = Decimal(ticker_data["b"][0])
            volume_24h = Decimal(ticker_data["v"][1])  # 24h volume

            return NormalizedQuote(
                venue_name=self.venue_name,
                token_symbol=symbol_upper,
                bid=bid_price,
                ask=ask_price,
                volume_24h=volume_24h,
                timestamp=datetime.now(timezone.utc),
            )

        except httpx.TimeoutException:
            logger.error(f"Timeout fetching Kraken quote for {token_symbol}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching Kraken quote: {e.response.status_code}")
            return None
        except (KeyError, IndexError, ValueError) as e:
            logger.error(f"Error parsing Kraken response for {token_symbol}: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error fetching Kraken quote for {token_symbol}: {e}")
            return None

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> "KrakenClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
