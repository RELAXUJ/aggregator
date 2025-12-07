#!/usr/bin/env python3
"""Test script to manually run the price fetcher task.

Run from backend directory:
    python scripts/test_price_fetcher.py

This script runs the price fetcher once and displays results.
"""

import asyncio
import sys

sys.path.insert(0, ".")

from app.rwa_aggregator.infrastructure.tasks.price_tasks import _fetch_all_prices_async


async def main():
    print("\n" + "=" * 60)
    print("RWA Aggregator - Manual Price Fetch Test")
    print("=" * 60 + "\n")

    print("Fetching prices from all venues...")
    result = await _fetch_all_prices_async()

    print("\n" + "-" * 60)
    print("Results:")
    print(f"  Tokens processed: {result['tokens_processed']}")
    print(f"  Snapshots created: {result['snapshots_created']}")
    print(f"  Timestamp: {result['timestamp']}")

    if result['errors']:
        print(f"\n  Errors ({len(result['errors'])}):")
        for error in result['errors']:
            print(f"    - {error}")
    else:
        print("\n  ✅ No errors!")

    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
