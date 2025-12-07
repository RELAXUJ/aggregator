#!/usr/bin/env python
"""Test script to verify price feed API connections.

Run from the backend directory:
    python -m scripts.test_price_feeds

Or with specific feeds:
    python -m scripts.test_price_feeds --kraken --coinbase
"""

import argparse
import asyncio
import logging
import os
import sys
from decimal import Decimal

# Add parent to path for imports
sys.path.insert(0, ".")

# Default API key for The Graph (can be overridden via --thegraph-key or THEGRAPH_API_KEY env var)
DEFAULT_THEGRAPH_API_KEY = "37c26010270315607fc2333c3dbabe1b"

from app.rwa_aggregator.infrastructure.external import (
    CoinbaseClient,
    KrakenClient,
    PriceFeedRegistry,
    UniswapClient,
    create_default_registry,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def test_kraken():
    """Test Kraken API connection."""
    print("\n" + "=" * 50)
    print("Testing Kraken API")
    print("=" * 50)

    async with KrakenClient() as client:
        # Test tokens
        test_tokens = ["BTC", "ETH", "USDC", "PAXG"]

        for token in test_tokens:
            if client.supports_token(token):
                print(f"\nFetching {token} from Kraken...")
                quote = await client.fetch_quote(token)
                if quote:
                    print(f"  ✓ {token}")
                    print(f"    Bid: ${quote.bid:,.4f}")
                    print(f"    Ask: ${quote.ask:,.4f}")
                    print(f"    Mid: ${quote.mid_price:,.4f}")
                    print(f"    Spread: {quote.spread_bps:.2f} bps")
                    if quote.volume_24h:
                        print(f"    24h Volume: {quote.volume_24h:,.2f}")
                else:
                    print(f"  ✗ {token} - No data returned")
            else:
                print(f"  - {token} - Not supported")

    print("\n✓ Kraken test completed")


async def test_coinbase(api_key: str = None, api_secret: str = None):
    """Test Coinbase API connection."""
    print("\n" + "=" * 50)
    print("Testing Coinbase API")
    print("=" * 50)

    async with CoinbaseClient(api_key=api_key, api_secret=api_secret) as client:
        # Test tokens
        test_tokens = ["BTC", "ETH", "USDC", "PAXG"]

        for token in test_tokens:
            if client.supports_token(token):
                print(f"\nFetching {token} from Coinbase...")
                quote = await client.fetch_quote(token)
                if quote:
                    print(f"  ✓ {token}")
                    print(f"    Bid: ${quote.bid:,.4f}")
                    print(f"    Ask: ${quote.ask:,.4f}")
                    print(f"    Mid: ${quote.mid_price:,.4f}")
                    print(f"    Spread: {quote.spread_bps:.2f} bps")
                    if quote.volume_24h:
                        print(f"    24h Volume: {quote.volume_24h:,.2f}")
                else:
                    print(f"  ✗ {token} - No data returned")
            else:
                print(f"  - {token} - Not supported")

    print("\n✓ Coinbase test completed")


async def test_uniswap(api_key: str = None):
    """Test Uniswap Subgraph connection."""
    print("\n" + "=" * 50)
    print("Testing Uniswap V3 Subgraph")
    print("=" * 50)

    if api_key:
        print(f"\n  Using The Graph API key: {api_key[:8]}...")
    else:
        print("\n  ⚠ No API key provided. Get one from https://thegraph.com/studio/")

    async with UniswapClient(network="mainnet", api_key=api_key) as client:
        # Test tokens (tokens that have liquidity pools)
        test_tokens = ["ETH", "USDC", "WBTC", "DAI"]

        for token in test_tokens:
            if client.supports_token(token):
                print(f"\nFetching {token} from Uniswap...")
                quote = await client.fetch_quote(token)
                if quote:
                    print(f"  ✓ {token}")
                    print(f"    Bid: ${quote.bid:,.4f}")
                    print(f"    Ask: ${quote.ask:,.4f}")
                    print(f"    Mid: ${quote.mid_price:,.4f}")
                    print(f"    Spread: {quote.spread_bps:.2f} bps")
                    if quote.volume_24h:
                        print(f"    24h Volume: ${quote.volume_24h:,.2f}")
                else:
                    print(f"  ✗ {token} - No pool data found")
            else:
                print(f"  - {token} - No known address")

    print("\n✓ Uniswap test completed")


async def test_registry(thegraph_api_key: str = None):
    """Test the PriceFeedRegistry with all feeds."""
    print("\n" + "=" * 50)
    print("Testing Price Feed Registry (All Sources)")
    print("=" * 50)

    registry = create_default_registry(thegraph_api_key=thegraph_api_key)

    try:
        print(f"\nRegistered feeds: {registry.registered_feeds}")

        # Test aggregated quote fetching
        test_token = "ETH"
        print(f"\nFetching {test_token} from all sources...")

        quotes = await registry.fetch_all_quotes(test_token)

        print(f"\nReceived {len(quotes)} quotes:")
        for quote in quotes:
            print(f"\n  {quote.venue_name}:")
            print(f"    Bid: ${quote.bid:,.4f}")
            print(f"    Ask: ${quote.ask:,.4f}")
            print(f"    Spread: {quote.spread_bps:.2f} bps")

        if quotes:
            # Find best prices
            best_bid_quote = registry.get_best_bid(quotes)
            best_ask_quote = registry.get_best_ask(quotes)
            best_spread_quote = registry.get_best_quote(quotes)

            print(f"\n  Best Execution Analysis:")
            if best_bid_quote:
                print(f"    Best Bid (sell here): ${best_bid_quote.bid:,.4f} @ {best_bid_quote.venue_name}")
            if best_ask_quote:
                print(f"    Best Ask (buy here): ${best_ask_quote.ask:,.4f} @ {best_ask_quote.venue_name}")
            if best_spread_quote:
                print(f"    Tightest Spread: {best_spread_quote.spread_bps:.2f} bps @ {best_spread_quote.venue_name}")

    finally:
        await registry.close_all()

    print("\n✓ Registry test completed")


async def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="Test price feed API connections")
    parser.add_argument("--kraken", action="store_true", help="Test Kraken only")
    parser.add_argument("--coinbase", action="store_true", help="Test Coinbase only")
    parser.add_argument("--uniswap", action="store_true", help="Test Uniswap only")
    parser.add_argument("--registry", action="store_true", help="Test Registry only")
    parser.add_argument("--coinbase-key", help="Coinbase API key")
    parser.add_argument("--coinbase-secret", help="Coinbase API secret")
    parser.add_argument("--thegraph-key", help="The Graph API key for Uniswap")

    args = parser.parse_args()

    # Get The Graph API key from: CLI arg > env var > default
    thegraph_key = args.thegraph_key or os.environ.get("THEGRAPH_API_KEY") or DEFAULT_THEGRAPH_API_KEY

    # If no specific feed selected, test all
    test_all = not any([args.kraken, args.coinbase, args.uniswap, args.registry])

    print("=" * 50)
    print("RWA Liquidity Aggregator - Price Feed Test")
    print("=" * 50)

    try:
        if test_all or args.kraken:
            await test_kraken()

        if test_all or args.coinbase:
            await test_coinbase(args.coinbase_key, args.coinbase_secret)

        if test_all or args.uniswap:
            await test_uniswap(thegraph_key)

        if test_all or args.registry:
            await test_registry(thegraph_key)

        print("\n" + "=" * 50)
        print("All tests completed successfully!")
        print("=" * 50)

    except Exception as e:
        logger.exception(f"Test failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
