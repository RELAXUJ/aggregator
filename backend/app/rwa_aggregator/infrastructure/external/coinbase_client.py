"""Coinbase REST API client for fetching price quotes.

Coinbase API documentation: https://docs.cloud.coinbase.com/advanced-trade-api/docs/
Uses the Advanced Trade API (v3) which is the current recommended API.
Public endpoints rate limit: 3-10 requests/second per IP.
"""

import hashlib
import hmac
import logging
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import httpx

from backend.app.rwa_aggregator.application.interfaces.price_feed import (
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
    # Stablecoins
    "USDT": "USDT-USD",
    "USDC": "USDC-USD",
    "DAI": "DAI-USD",
    # RWA-related tokens
    "PAXG": "PAXG-USD",  # Paxos Gold
    # Add more as needed
}

# Default timeout for HTTP requests
DEFAULT_TIMEOUT_SECONDS = 10.0


class CoinbaseClient(PriceFeed):
    """Coinbase REST API client implementing the PriceFeed interface.

    This client fetches real-time ticker data from Coinbase's Advanced Trade API.
    Public endpoints can be used without authentication, but authenticated
    requests have higher rate limits.

    Attributes:
        _client: httpx AsyncClient for making HTTP requests.
        _base_url: Coinbase API base URL.
        _api_key: Optional API key for authenticated requests.
        _api_secret: Optional API secret for authenticated requests.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        base_url: str = "https://api.coinbase.com",
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        """Initialize the Coinbase client.

        Args:
            api_key: Optional Coinbase API key (CDP key ID).
            api_secret: Optional Coinbase API secret (CDP private key).
            base_url: Coinbase API base URL.
            timeout: HTTP request timeout in seconds.
        """
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._api_secret = api_secret
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
            headers={"Accept": "application/json"},
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

    def _generate_auth_headers(self, method: str, path: str, body: str = "") -> dict[str, str]:
        """Generate authentication headers for Coinbase API.

        Args:
            method: HTTP method (GET, POST, etc.).
            path: API endpoint path.
            body: Request body (empty string for GET requests).

        Returns:
            Dictionary of authentication headers.
        """
        if not self._api_key or not self._api_secret:
            return {}

        timestamp = str(int(time.time()))
        message = timestamp + method.upper() + path + body
        
        # Sign the message with HMAC-SHA256
        signature = hmac.new(
            self._api_secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return {
            "CB-ACCESS-KEY": self._api_key,
            "CB-ACCESS-SIGN": signature,
            "CB-ACCESS-TIMESTAMP": timestamp,
        }

    async def fetch_quote(self, token_symbol: str) -> Optional[NormalizedQuote]:
        """Fetch a price quote from Coinbase for the given token.

        Uses the Advanced Trade API product ticker endpoint.

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

        # Use the Advanced Trade API to get best bid/ask
        path = f"/api/v3/brokerage/products/{product_id}"

        try:
            headers = self._generate_auth_headers("GET", path)
            response = await self._client.get(path, headers=headers)
            response.raise_for_status()
            data = response.json()

            # Response structure from /api/v3/brokerage/products/{id}
            # Returns price, bid, ask, volume directly
            bid = data.get("bid") or data.get("price")
            ask = data.get("ask") or data.get("price")
            volume_24h = data.get("volume_24h")

            if not bid or not ask:
                logger.warning(f"Missing bid/ask in Coinbase response for {product_id}")
                return None

            bid_price = Decimal(str(bid))
            ask_price = Decimal(str(ask))
            volume = Decimal(str(volume_24h)) if volume_24h else None

            return NormalizedQuote(
                venue_name=self.venue_name,
                token_symbol=symbol_upper,
                bid=bid_price,
                ask=ask_price,
                volume_24h=volume,
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
        self, token_symbol: str, limit: int = 20
    ) -> Optional[dict]:
        """Fetch order book data for deeper liquidity analysis.

        Args:
            token_symbol: Normalized token symbol.
            limit: Number of price levels to fetch (default 20).

        Returns:
            Dictionary with 'bids' and 'asks' lists, or None if unavailable.
        """
        symbol_upper = token_symbol.upper()
        product_id = COINBASE_SYMBOL_MAP.get(symbol_upper)

        if not product_id:
            return None

        path = f"/api/v3/brokerage/products/{product_id}/book"

        try:
            headers = self._generate_auth_headers("GET", path)
            response = await self._client.get(
                path, 
                params={"limit": limit},
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

            pricebook = data.get("pricebook", {})
            return {
                "bids": pricebook.get("bids", []),
                "asks": pricebook.get("asks", []),
                "timestamp": pricebook.get("time"),
            }

        except Exception as e:
            logger.error(f"Error fetching Coinbase order book for {token_symbol}: {e}")
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
