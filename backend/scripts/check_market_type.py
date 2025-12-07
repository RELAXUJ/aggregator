#!/usr/bin/env python3
"""Check market_type values for tokens in the database."""

import asyncio
import sys
sys.path.insert(0, ".")

from app.rwa_aggregator.infrastructure.db.session import get_async_session_local
from sqlalchemy import text


async def check():
    """Check market_type values."""
    session_factory = get_async_session_local()
    async with session_factory() as session:
        result = await session.execute(
            text("SELECT symbol, name, market_type FROM tokens ORDER BY symbol")
        )
        print("Token market_type values in database:")
        print("-" * 50)
        for row in result.fetchall():
            print(f"  {row[0]}: market_type = {row[2]}")


if __name__ == "__main__":
    asyncio.run(check())
