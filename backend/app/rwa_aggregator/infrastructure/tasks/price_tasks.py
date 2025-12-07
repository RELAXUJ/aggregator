"""Celery tasks for price fetching and aggregation."""

import logging

from app.rwa_aggregator.infrastructure.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="fetch_all_prices")
def fetch_all_prices(self) -> dict:
    """Fetch prices from all configured venues for all tracked tokens.

    This task runs on a schedule (every 30s by default) and:
    1. Fetches prices from each venue (CEX, DEX, issuer)
    2. Stores snapshots in Redis cache
    3. Persists to PostgreSQL for historical data

    Returns:
        Summary of fetched prices.

    Raises:
        NotImplementedError: Task requires venue clients and repositories.
    """
    logger.error(
        "fetch_all_prices task called but not implemented. "
        "Requires: TokenRepository, PriceRepository, and venue clients (Kraken, Coinbase, etc.)"
    )
    raise NotImplementedError(
        "fetch_all_prices requires: "
        "1) TokenRepository to get tracked tokens, "
        "2) Venue clients (KrakenClient, CoinbaseClient, etc.), "
        "3) PriceRepository to persist snapshots, "
        "4) Redis client for caching"
    )


@celery_app.task(bind=True, name="fetch_price_for_token")
def fetch_price_for_token(self, token_symbol: str) -> dict:
    """Fetch price for a specific token from all venues.

    Args:
        token_symbol: The token symbol to fetch prices for.

    Returns:
        Price data from all venues.

    Raises:
        NotImplementedError: Task requires venue clients and repositories.
    """
    logger.error(
        f"fetch_price_for_token({token_symbol}) called but not implemented. "
        "Requires venue clients and PriceRepository."
    )
    raise NotImplementedError(
        f"fetch_price_for_token({token_symbol}) requires: "
        "1) Venue clients (KrakenClient, CoinbaseClient, etc.), "
        "2) PriceRepository to persist snapshots, "
        "3) Redis client for caching"
    )
