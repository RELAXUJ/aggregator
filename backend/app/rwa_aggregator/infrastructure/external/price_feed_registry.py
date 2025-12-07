"""Price feed registry for aggregating quotes from multiple venues.

The registry manages multiple price feed clients and enables concurrent
fetching of quotes across all supported venues.
"""

import asyncio
import logging
from typing import Optional

from app.rwa_aggregator.application.interfaces.price_feed import (
    NormalizedQuote,
    PriceFeed,
)

logger = logging.getLogger(__name__)


class PriceFeedRegistry:
    """Registry that aggregates multiple price feed sources.

    This class manages all configured price feed clients and provides
    methods to fetch quotes from multiple venues concurrently.

    Attributes:
        _feeds: List of registered PriceFeed implementations.
    """

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._feeds: list[PriceFeed] = []

    def register(self, feed: PriceFeed) -> None:
        """Register a price feed client.

        Args:
            feed: PriceFeed implementation to add to the registry.
        """
        self._feeds.append(feed)
        logger.info(f"Registered price feed: {feed.venue_name}")

    def unregister(self, venue_name: str) -> bool:
        """Remove a price feed by venue name.

        Args:
            venue_name: Name of the venue to remove.

        Returns:
            True if a feed was removed, False otherwise.
        """
        for i, feed in enumerate(self._feeds):
            if feed.venue_name == venue_name:
                self._feeds.pop(i)
                logger.info(f"Unregistered price feed: {venue_name}")
                return True
        return False

    def get_feeds_for_token(self, token_symbol: str) -> list[PriceFeed]:
        """Get all feeds that support a given token.

        Args:
            token_symbol: Normalized token symbol.

        Returns:
            List of PriceFeed instances that support the token.
        """
        return [
            feed for feed in self._feeds
            if feed.supports_token(token_symbol)
        ]

    @property
    def registered_feeds(self) -> list[str]:
        """Get names of all registered feeds."""
        return [feed.venue_name for feed in self._feeds]

    async def fetch_quote(
        self, token_symbol: str, venue_name: str
    ) -> Optional[NormalizedQuote]:
        """Fetch a quote from a specific venue.

        Args:
            token_symbol: Normalized token symbol.
            venue_name: Name of the venue to query.

        Returns:
            NormalizedQuote if successful, None otherwise.
        """
        for feed in self._feeds:
            if feed.venue_name == venue_name:
                return await feed.fetch_quote(token_symbol)
        logger.warning(f"Venue not found: {venue_name}")
        return None

    async def fetch_all_quotes(
        self, token_symbol: str, timeout_seconds: float = 10.0
    ) -> list[NormalizedQuote]:
        """Fetch quotes from all venues that support the token concurrently.

        Args:
            token_symbol: Normalized token symbol.
            timeout_seconds: Maximum time to wait for all responses.

        Returns:
            List of NormalizedQuote from all responding venues.
            Failed requests are logged but not included in results.
        """
        feeds = self.get_feeds_for_token(token_symbol)

        if not feeds:
            logger.warning(f"No feeds support token: {token_symbol}")
            return []

        async def fetch_with_error_handling(feed: PriceFeed) -> Optional[NormalizedQuote]:
            """Fetch quote with error isolation."""
            try:
                return await feed.fetch_quote(token_symbol)
            except Exception as e:
                logger.error(f"Error fetching from {feed.venue_name}: {e}")
                return None

        # Fetch from all feeds concurrently with timeout
        tasks = [fetch_with_error_handling(feed) for feed in feeds]

        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=False),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.error(f"Timeout fetching quotes for {token_symbol}")
            results = []

        # Filter out None results
        quotes = [r for r in results if r is not None]
        logger.info(
            f"Fetched {len(quotes)}/{len(feeds)} quotes for {token_symbol}"
        )

        return quotes

    async def fetch_quotes_for_tokens(
        self, token_symbols: list[str], timeout_seconds: float = 15.0
    ) -> dict[str, list[NormalizedQuote]]:
        """Fetch quotes for multiple tokens from all venues.

        Args:
            token_symbols: List of token symbols to fetch.
            timeout_seconds: Maximum time to wait for all responses.

        Returns:
            Dictionary mapping token symbols to lists of quotes.
        """
        async def fetch_token_quotes(symbol: str) -> tuple[str, list[NormalizedQuote]]:
            quotes = await self.fetch_all_quotes(symbol, timeout_seconds / 2)
            return symbol, quotes

        tasks = [fetch_token_quotes(symbol) for symbol in token_symbols]

        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks),
                timeout=timeout_seconds,
            )
            return dict(results)
        except asyncio.TimeoutError:
            logger.error("Timeout fetching multi-token quotes")
            return {}

    def get_best_quote(self, quotes: list[NormalizedQuote]) -> Optional[NormalizedQuote]:
        """Find the quote with the best (tightest) spread.

        Args:
            quotes: List of quotes to compare.

        Returns:
            Quote with the smallest spread, or None if list is empty.
        """
        if not quotes:
            return None
        return min(quotes, key=lambda q: q.spread_bps)

    def get_best_bid(self, quotes: list[NormalizedQuote]) -> Optional[NormalizedQuote]:
        """Find the quote with the highest bid (best sell price).

        Args:
            quotes: List of quotes to compare.

        Returns:
            Quote with the highest bid, or None if list is empty.
        """
        if not quotes:
            return None
        return max(quotes, key=lambda q: q.bid)

    def get_best_ask(self, quotes: list[NormalizedQuote]) -> Optional[NormalizedQuote]:
        """Find the quote with the lowest ask (best buy price).

        Args:
            quotes: List of quotes to compare.

        Returns:
            Quote with the lowest ask, or None if list is empty.
        """
        if not quotes:
            return None
        return min(quotes, key=lambda q: q.ask)

    async def close_all(self) -> None:
        """Close all registered feed clients."""
        for feed in self._feeds:
            try:
                await feed.close()
                logger.debug(f"Closed feed: {feed.venue_name}")
            except Exception as e:
                logger.error(f"Error closing feed {feed.venue_name}: {e}")
        self._feeds.clear()

    async def __aenter__(self) -> "PriceFeedRegistry":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close_all()


def create_default_registry(
    kraken_enabled: bool = True,
    coinbase_enabled: bool = True,
    coinbase_api_key: Optional[str] = None,
    coinbase_api_secret: Optional[str] = None,
    bybit_enabled: bool = True,
    uniswap_enabled: bool = True,
    uniswap_network: str = "mainnet",
    thegraph_api_key: Optional[str] = None,
) -> PriceFeedRegistry:
    """Create a registry with default price feed clients.

    Factory function that creates and configures a PriceFeedRegistry
    with the standard set of price feed clients.

    Args:
        kraken_enabled: Whether to include Kraken client.
        coinbase_enabled: Whether to include Coinbase client.
        coinbase_api_key: Optional Coinbase API key.
        coinbase_api_secret: Optional Coinbase API secret.
        bybit_enabled: Whether to include Bybit client.
        uniswap_enabled: Whether to include Uniswap client.
        uniswap_network: Uniswap network (mainnet, arbitrum, etc.).
        thegraph_api_key: The Graph API key for Uniswap subgraph access.

    Returns:
        Configured PriceFeedRegistry instance.
    """
    from app.rwa_aggregator.infrastructure.external.bybit_client import BybitClient
    from app.rwa_aggregator.infrastructure.external.coinbase_client import CoinbaseClient
    from app.rwa_aggregator.infrastructure.external.kraken_client import KrakenClient
    from app.rwa_aggregator.infrastructure.external.uniswap_client import UniswapClient

    registry = PriceFeedRegistry()

    if kraken_enabled:
        registry.register(KrakenClient())

    if coinbase_enabled:
        registry.register(
            CoinbaseClient(
                api_key=coinbase_api_key,
                api_secret=coinbase_api_secret,
            )
        )

    if bybit_enabled:
        registry.register(BybitClient())

    if uniswap_enabled:
        registry.register(
            UniswapClient(
                network=uniswap_network,
                api_key=thegraph_api_key,
            )
        )

    return registry
