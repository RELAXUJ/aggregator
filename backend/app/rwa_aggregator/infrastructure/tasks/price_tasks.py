"""Celery tasks for price fetching and aggregation."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from app.core.config import get_settings
from app.rwa_aggregator.domain.entities.price_snapshot import PriceSnapshot
from app.rwa_aggregator.domain.entities.token import MarketType
from app.rwa_aggregator.infrastructure.db.session import get_async_session_local
from app.rwa_aggregator.infrastructure.external.price_feed_registry import (
    create_default_registry,
)
from app.rwa_aggregator.infrastructure.repositories.sql_price_repository import (
    SqlPriceRepository,
)
from app.rwa_aggregator.infrastructure.repositories.sql_token_repository import (
    SqlTokenRepository,
)
from app.rwa_aggregator.infrastructure.repositories.sql_venue_repository import (
    SqlVenueRepository,
)
from app.rwa_aggregator.infrastructure.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _fetch_all_prices_async() -> dict[str, Any]:
    """Async implementation of price fetching.

    Returns:
        Summary of fetched prices.
    """
    settings = get_settings()
    results = {
        "tokens_processed": 0,
        "snapshots_created": 0,
        "errors": [],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Create price feed registry with configured clients
    registry = create_default_registry(
        kraken_enabled=True,
        coinbase_enabled=True,
        coinbase_api_key=settings.coinbase_api_key or None,
        coinbase_api_secret=settings.coinbase_api_secret or None,
        bybit_enabled=True,
        uniswap_enabled=True,
        thegraph_api_key=settings.thegraph_api_key or None,
    )

    session_factory = get_async_session_local()

    async with session_factory() as session:
        token_repo = SqlTokenRepository(session)
        venue_repo = SqlVenueRepository(session)
        price_repo = SqlPriceRepository(session)

        # Get all active tokens
        tokens = await token_repo.get_all_active()
        logger.info(f"Fetching prices for {len(tokens)} tokens")

        # Build venue name -> id map
        venues = await venue_repo.get_all_active()
        venue_map = {v.name: v.id for v in venues}
        logger.debug(f"Venue map: {venue_map}")

        for token in tokens:
            # Skip NAV-only tokens - they don't have active trading pairs
            if token.market_type == MarketType.NAV_ONLY:
                logger.info(
                    f"Skipping {token.symbol} - NAV-only token (no active trading pairs)"
                )
                continue

            try:
                # Fetch quotes from all venues for this token
                quotes = await registry.fetch_all_quotes(token.symbol)
                logger.info(
                    f"Received {len(quotes)} quotes for {token.symbol}"
                )

                snapshots_to_save = []
                for quote in quotes:
                    # Map venue name to ID
                    venue_id = venue_map.get(quote.venue_name)
                    if venue_id is None:
                        logger.warning(
                            f"Venue '{quote.venue_name}' not found in database, skipping"
                        )
                        continue

                    # Create PriceSnapshot entity
                    snapshot = PriceSnapshot(
                        id=None,
                        token_id=token.id,
                        venue_id=venue_id,
                        bid=quote.bid,
                        ask=quote.ask,
                        volume_24h=quote.volume_24h,
                        fetched_at=quote.timestamp,
                    )
                    snapshots_to_save.append(snapshot)

                # Batch save all snapshots for this token
                if snapshots_to_save:
                    saved = await price_repo.save_batch(snapshots_to_save)
                    results["snapshots_created"] += len(saved)
                    logger.info(
                        f"Saved {len(saved)} snapshots for {token.symbol}"
                    )

                results["tokens_processed"] += 1

            except Exception as e:
                error_msg = f"Error fetching {token.symbol}: {str(e)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)

        # Commit all changes
        await session.commit()

    # Clean up registry
    await registry.close_all()

    logger.info(
        f"Price fetch complete: {results['tokens_processed']} tokens, "
        f"{results['snapshots_created']} snapshots"
    )
    return results


@celery_app.task(
    bind=True,
    name="app.rwa_aggregator.infrastructure.tasks.price_tasks.fetch_all_prices",
)
def fetch_all_prices(self) -> dict:
    """Fetch prices from all configured venues for all tracked tokens.

    This task runs on a schedule (every 30s by default) and:
    1. Fetches prices from each venue (CEX, DEX)
    2. Persists snapshots to PostgreSQL for historical data

    Returns:
        Summary of fetched prices.
    """
    logger.info("Starting fetch_all_prices task")
    try:
        result = asyncio.run(_fetch_all_prices_async())
        return result
    except Exception as e:
        logger.exception(f"fetch_all_prices failed: {e}")
        raise


async def _fetch_price_for_token_async(token_symbol: str) -> dict[str, Any]:
    """Async implementation of single token price fetching.

    Args:
        token_symbol: The token symbol to fetch prices for.

    Returns:
        Price data from all venues.
    """
    settings = get_settings()
    results = {
        "token": token_symbol,
        "snapshots_created": 0,
        "quotes": [],
        "errors": [],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    registry = create_default_registry(
        kraken_enabled=True,
        coinbase_enabled=True,
        coinbase_api_key=settings.coinbase_api_key or None,
        coinbase_api_secret=settings.coinbase_api_secret or None,
        bybit_enabled=True,
        uniswap_enabled=True,
        thegraph_api_key=settings.thegraph_api_key or None,
    )

    session_factory = get_async_session_local()

    async with session_factory() as session:
        token_repo = SqlTokenRepository(session)
        venue_repo = SqlVenueRepository(session)
        price_repo = SqlPriceRepository(session)

        # Get token by symbol
        token = await token_repo.get_by_symbol(token_symbol)
        if not token:
            results["errors"].append(f"Token {token_symbol} not found")
            return results

        # Check if token is NAV-only
        if token.market_type == MarketType.NAV_ONLY:
            results["errors"].append(
                f"Token {token_symbol} is NAV-only (no active trading pairs)"
            )
            await registry.close_all()
            return results

        # Build venue name -> id map
        venues = await venue_repo.get_all_active()
        venue_map = {v.name: v.id for v in venues}

        # Fetch quotes
        quotes = await registry.fetch_all_quotes(token.symbol)

        snapshots_to_save = []
        for quote in quotes:
            venue_id = venue_map.get(quote.venue_name)
            if venue_id is None:
                continue

            snapshot = PriceSnapshot(
                id=None,
                token_id=token.id,
                venue_id=venue_id,
                bid=quote.bid,
                ask=quote.ask,
                volume_24h=quote.volume_24h,
                fetched_at=quote.timestamp,
            )
            snapshots_to_save.append(snapshot)

            results["quotes"].append({
                "venue": quote.venue_name,
                "bid": str(quote.bid),
                "ask": str(quote.ask),
                "spread_bps": str(quote.spread_bps),
            })

        if snapshots_to_save:
            saved = await price_repo.save_batch(snapshots_to_save)
            results["snapshots_created"] = len(saved)

        await session.commit()

    await registry.close_all()
    return results


@celery_app.task(
    bind=True,
    name="app.rwa_aggregator.infrastructure.tasks.price_tasks.fetch_price_for_token",
)
def fetch_price_for_token(self, token_symbol: str) -> dict:
    """Fetch price for a specific token from all venues.

    Args:
        token_symbol: The token symbol to fetch prices for.

    Returns:
        Price data from all venues.
    """
    logger.info(f"Starting fetch_price_for_token task for {token_symbol}")
    try:
        result = asyncio.run(_fetch_price_for_token_async(token_symbol))
        return result
    except Exception as e:
        logger.exception(f"fetch_price_for_token failed: {e}")
        raise
