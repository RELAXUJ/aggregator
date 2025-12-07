#!/usr/bin/env python3
"""Quick database state check script."""

import asyncio
import sys
sys.path.insert(0, ".")

from app.rwa_aggregator.infrastructure.db.session import get_async_session_local
from sqlalchemy import text


async def check_db():
    """Check database connection and tables."""
    session_factory = get_async_session_local()
    async with session_factory() as session:
        # Check connection
        result = await session.execute(text("SELECT 1"))
        print(f"✓ Database connection OK")
        
        # Check tables exist
        result = await session.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """))
        tables = [row[0] for row in result.fetchall()]
        print(f"✓ Tables found: {tables}")
        
        # Count rows in each relevant table
        for table in ['tokens', 'venues', 'price_snapshots', 'alerts']:
            if table in tables:
                result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                print(f"  - {table}: {count} rows")


if __name__ == "__main__":
    asyncio.run(check_db())
