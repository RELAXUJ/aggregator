#!/usr/bin/env python3
"""Test script to check RIO token availability across all providers.

This script tests if RIO token is available on various exchanges by trying
common pair formats. It bypasses the symbol maps to directly query APIs.

Run from backend directory:
    python scripts/test_rio_token.py
"""

import asyncio
import logging
import sys
from decimal import Decimal

import httpx

# Add parent to path for imports
sys.path.insert(0, ".")

from app.rwa_aggregator.infrastructure.external import (
    CoinbaseClient,
    KrakenClient,
    UniswapClient,
)
from app.rwa_aggregator.infrastructure.external.bybit_client import BybitClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def test_bybit_rio():
    """Test RIO token on Bybit with common pair formats."""
    print("\n" + "=" * 60)
    print("Testing RIO on Bybit")
    print("=" * 60)

    # Common Bybit pair formats to try
    pair_formats = ["RIOUSDT", "RIO/USDT", "RIO-USDT"]

    async with BybitClient() as client:
        for pair_format in pair_formats:
            try:
                print(f"\nTrying pair format: {pair_format}")
                response = await client._client.get(
                    "/v5/market/tickers",
                    params={
                        "category": "spot",
                        "symbol": pair_format.replace("/", "").replace("-", ""),
                    },
                )
                response.raise_for_status()
                data = response.json()

                if data.get("retCode") == 0:
                    result_list = data.get("result", {}).get("list", [])
                    if result_list:
                        ticker = result_list[0]
                        bid = ticker.get("bid1Price")
                        ask = ticker.get("ask1Price")
                        volume = ticker.get("volume24h")

                        if bid and ask:
                            print(f"  ✅ SUCCESS! Found RIO on Bybit")
                            print(f"     Pair: {pair_format}")
                            print(f"     Bid: ${Decimal(str(bid)):,.4f}")
                            print(f"     Ask: ${Decimal(str(ask)):,.4f}")
                            print(f"     Spread: ${Decimal(str(ask)) - Decimal(str(bid)):,.4f}")
                            if volume:
                                print(f"     24h Volume: {Decimal(str(volume)):,.2f}")
                            return True
                    else:
                        print(f"  ❌ No data returned for {pair_format}")
                else:
                    error_msg = data.get("retMsg", "Unknown error")
                    print(f"  ❌ API Error: {error_msg}")

            except httpx.HTTPStatusError as e:
                print(f"  ❌ HTTP {e.response.status_code} for {pair_format}")
            except Exception as e:
                print(f"  ❌ Error testing {pair_format}: {e}")

    print("\n  ⚠ RIO not found on Bybit with tested formats")
    return False


async def test_kraken_rio():
    """Test RIO token on Kraken with common pair formats."""
    print("\n" + "=" * 60)
    print("Testing RIO on Kraken")
    print("=" * 60)

    # Common Kraken pair formats to try
    pair_formats = ["RIOUSD", "XRIOZUSD", "RIOZUSD"]

    async with KrakenClient() as client:
        for pair_format in pair_formats:
            try:
                print(f"\nTrying pair format: {pair_format}")
                response = await client._client.get(
                    "/0/public/Ticker",
                    params={"pair": pair_format},
                )
                response.raise_for_status()
                data = response.json()

                if not data.get("error") or len(data["error"]) == 0:
                    result = data.get("result", {})
                    if result:
                        # Get first ticker data
                        ticker_data = None
                        for key in result:
                            ticker_data = result[key]
                            break

                        if ticker_data:
                            ask_price = Decimal(ticker_data["a"][0])
                            bid_price = Decimal(ticker_data["b"][0])
                            volume_24h = Decimal(ticker_data["v"][1])

                            print(f"  ✅ SUCCESS! Found RIO on Kraken")
                            print(f"     Pair: {pair_format}")
                            print(f"     Bid: ${bid_price:,.4f}")
                            print(f"     Ask: ${ask_price:,.4f}")
                            print(f"     Spread: ${ask_price - bid_price:,.4f}")
                            print(f"     24h Volume: {volume_24h:,.2f}")
                            return True
                    else:
                        print(f"  ❌ No result in response for {pair_format}")
                else:
                    error_msg = data.get("error", ["Unknown error"])[0]
                    print(f"  ❌ API Error: {error_msg}")

            except httpx.HTTPStatusError as e:
                print(f"  ❌ HTTP {e.response.status_code} for {pair_format}")
            except Exception as e:
                print(f"  ❌ Error testing {pair_format}: {e}")

    print("\n  ⚠ RIO not found on Kraken with tested formats")
    return False


async def test_coinbase_rio():
    """Test RIO token on Coinbase with common pair formats."""
    print("\n" + "=" * 60)
    print("Testing RIO on Coinbase")
    print("=" * 60)

    # Common Coinbase pair formats to try
    pair_formats = ["RIO-USD", "RIO-USDT", "RIO-USDC"]

    async with CoinbaseClient() as client:
        for pair_format in pair_formats:
            try:
                print(f"\nTrying pair format: {pair_format}")
                response = await client._client.get(f"/products/{pair_format}/ticker")
                response.raise_for_status()
                data = response.json()

                bid = data.get("bid")
                ask = data.get("ask")
                volume = data.get("volume")

                if bid and ask:
                    bid_price = Decimal(str(bid))
                    ask_price = Decimal(str(ask))
                    volume_24h = Decimal(str(volume)) if volume else None

                    print(f"  ✅ SUCCESS! Found RIO on Coinbase")
                    print(f"     Pair: {pair_format}")
                    print(f"     Bid: ${bid_price:,.4f}")
                    print(f"     Ask: ${ask_price:,.4f}")
                    print(f"     Spread: ${ask_price - bid_price:,.4f}")
                    if volume_24h:
                        print(f"     24h Volume: {volume_24h:,.2f}")
                    return True
                else:
                    print(f"  ❌ Missing bid/ask in response for {pair_format}")

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    print(f"  ❌ Product not found: {pair_format}")
                else:
                    print(f"  ❌ HTTP {e.response.status_code} for {pair_format}")
            except Exception as e:
                print(f"  ❌ Error testing {pair_format}: {e}")

    print("\n  ⚠ RIO not found on Coinbase with tested formats")
    return False


async def test_uniswap_rio():
    """Test RIO token on Uniswap (requires token address)."""
    print("\n" + "=" * 60)
    print("Testing RIO on Uniswap V3")
    print("=" * 60)

    print("\n  ⚠ Uniswap requires token contract address")
    print("     To test RIO on Uniswap, we need:")
    print("     1. RIO token contract address")
    print("     2. Check if there's a liquidity pool")
    print("     3. Query The Graph subgraph for pool data")
    print("\n     If you have the RIO contract address, we can add it to the test.")

    # Note: UniswapClient uses token addresses, not symbols
    # We would need the RIO contract address to test this properly
    return False


async def list_available_pairs_bybit():
    """List available trading pairs on Bybit to search for RIO."""
    print("\n" + "=" * 60)
    print("Searching Bybit for RIO-related pairs")
    print("=" * 60)

    try:
        async with httpx.AsyncClient() as client:
            # Get all spot trading pairs
            response = await client.get(
                "https://api.bybit.com/v5/market/instruments-info",
                params={"category": "spot"},
            )
            response.raise_for_status()
            data = response.json()

            if data.get("retCode") == 0:
                result = data.get("result", {})
                instruments = result.get("list", [])

                # Search for RIO in symbol names
                rio_pairs = [
                    inst
                    for inst in instruments
                    if "RIO" in inst.get("symbol", "").upper()
                ]

                if rio_pairs:
                    print(f"\n  ✅ Found {len(rio_pairs)} RIO-related pairs on Bybit:")
                    for pair in rio_pairs:
                        symbol = pair.get("symbol", "")
                        status = pair.get("status", "")
                        print(f"     - {symbol} (Status: {status})")
                    return True
                else:
                    print("\n  ❌ No RIO pairs found in Bybit instruments list")
            else:
                print(f"\n  ❌ API Error: {data.get('retMsg', 'Unknown error')}")

    except Exception as e:
        print(f"\n  ❌ Error searching Bybit: {e}")

    return False


async def list_available_pairs_coinbase():
    """List available trading pairs on Coinbase to search for RIO."""
    print("\n" + "=" * 60)
    print("Searching Coinbase for RIO-related pairs")
    print("=" * 60)

    try:
        async with httpx.AsyncClient() as client:
            # Get all products
            response = await client.get(
                "https://api.exchange.coinbase.com/products"
            )
            response.raise_for_status()
            products = response.json()

            # Search for RIO in product IDs
            rio_products = [
                p for p in products if "RIO" in p.get("id", "").upper()
            ]

            if rio_products:
                print(f"\n  ✅ Found {len(rio_products)} RIO-related products on Coinbase:")
                for product in rio_products:
                    product_id = product.get("id", "")
                    status = product.get("status", "")
                    print(f"     - {product_id} (Status: {status})")
                return True
            else:
                print("\n  ❌ No RIO products found in Coinbase products list")

    except Exception as e:
        print(f"\n  ❌ Error searching Coinbase: {e}")

    return False


async def main():
    """Main test runner."""
    print("=" * 60)
    print("RIO Token Availability Test")
    print("Testing across all configured providers")
    print("=" * 60)

    results = {}

    # Test direct pair queries
    print("\n" + "=" * 60)
    print("PHASE 1: Direct Pair Format Testing")
    print("=" * 60)

    results["bybit"] = await test_bybit_rio()
    results["kraken"] = await test_kraken_rio()
    results["coinbase"] = await test_coinbase_rio()
    results["uniswap"] = await test_uniswap_rio()

    # Search available pairs
    print("\n" + "=" * 60)
    print("PHASE 2: Searching Available Pairs")
    print("=" * 60)

    results["bybit_search"] = await list_available_pairs_bybit()
    results["coinbase_search"] = await list_available_pairs_coinbase()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    found_any = any(results.values())
    if found_any:
        print("\n✅ RIO token IS available on at least one provider!")
        print("\nProviders with RIO:")
        for provider, found in results.items():
            if found:
                print(f"  - {provider}")
    else:
        print("\n❌ RIO token NOT found on any tested provider")
        print("\nNext steps:")
        print("  1. Verify RIO token symbol is correct")
        print("  2. Check if RIO is listed under a different symbol")
        print("  3. Verify the exchange/platform where RIO is traded")
        print("  4. If RIO is on a DEX, provide the contract address")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
