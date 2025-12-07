#!/usr/bin/env python3
"""Run database migrations for Railway deployment.

This script runs Alembic migrations and seeds initial data.
Safe to run multiple times (idempotent).
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alembic.config import Config
from alembic import command
from app.rwa_aggregator.infrastructure.db.session import get_async_session_local
from app.rwa_aggregator.infrastructure.db.models import TokenModel, VenueModel
from sqlalchemy import text


def run_migrations():
    """Run Alembic migrations."""
    print("=" * 50)
    print("Running database migrations...")
    print("=" * 50)
    
    # Alembic config - alembic.ini is in backend directory
    alembic_cfg = Config("alembic.ini")
    
    try:
        command.upgrade(alembic_cfg, "head")
        print("✅ Migrations completed successfully!")
        return True
    except Exception as e:
        print(f"❌ Migration error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def check_tables():
    """Check if tables exist."""
    print("\n" + "=" * 50)
    print("Checking database tables...")
    print("=" * 50)
    
    session_factory = get_async_session_local()
    async with session_factory() as session:
        result = await session.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
        )
        tables = [row[0] for row in result.fetchall()]
        
        if tables:
            print(f"✅ Found {len(tables)} tables:")
            for table in tables:
                print(f"   - {table}")
        else:
            print("❌ No tables found!")
        
        return len(tables) > 0


if __name__ == "__main__":
    print("\n🚀 Starting migration process...\n")
    
    # Run migrations
    success = run_migrations()
    
    if success:
        # Check tables
        has_tables = asyncio.run(check_tables())
        
        if has_tables:
            print("\n✅ Database is ready!")
            sys.exit(0)
        else:
            print("\n❌ Migrations ran but no tables found. Check logs above.")
            sys.exit(1)
    else:
        print("\n❌ Migrations failed. Check errors above.")
        sys.exit(1)
