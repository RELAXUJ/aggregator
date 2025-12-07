#!/usr/bin/env python3
"""Seed the database with initial tokens and venues for MVP.

Run from backend directory:
    python scripts/seed_data.py

This script is idempotent - safe to run multiple times.
"""

import asyncio
import sys

sys.path.insert(0, ".")

from sqlalchemy import select

from app.rwa_aggregator.infrastructure.db.session import get_async_session_local
from app.rwa_aggregator.infrastructure.db.models import TokenModel, VenueModel
from app.rwa_aggregator.domain.entities.token import TokenCategory
from app.rwa_aggregator.domain.entities.venue import VenueType, ApiType


# MVP Tokens per specification
TOKENS = [
    {
        "symbol": "USDY",
        "name": "Ondo US Dollar Yield",
        "category": TokenCategory.TBILL,
        "issuer": "Ondo Finance",
        "chain": "Ethereum",
        "contract_address": "0x96F6eF951840721AdBF46Ac996b59E0235CB985C",
    },
    {
        "symbol": "OUSG",
        "name": "Ondo Short-Term US Gov Treasuries",
        "category": TokenCategory.TBILL,
        "issuer": "Ondo Finance",
        "chain": "Ethereum",
        "contract_address": "0x1B19C19393e2d034D8Ff31ff34c81252FcBbee92",
    },
    {
        "symbol": "BENJI",
        "name": "Franklin OnChain US Gov Money Fund",
        "category": TokenCategory.TBILL,
        "issuer": "Franklin Templeton",
        "chain": "Stellar",
        "contract_address": None,  # Stellar-based
    },
    # Test tokens with real exchange data (for infrastructure verification)
    {
        "symbol": "ETH",
        "name": "Ethereum (Test Token)",
        "category": TokenCategory.EQUITY,  # Using EQUITY as placeholder
        "issuer": "Ethereum Foundation",
        "chain": "Ethereum",
        "contract_address": None,
    },
    {
        "symbol": "PAXG",
        "name": "Paxos Gold (RWA - Gold)",
        "category": TokenCategory.EQUITY,
        "issuer": "Paxos",
        "chain": "Ethereum",
        "contract_address": "0x45804880De22913dAFE09f4980848ECE6EcbAf78",
    },
]

# MVP Venues per specification
VENUES = [
    {
        "name": "Kraken",
        "venue_type": VenueType.CEX,
        "api_type": ApiType.REST,
        "base_url": "https://api.kraken.com",
        "trade_url_template": "https://www.kraken.com/trade/{symbol}-USD",
    },
    {
        "name": "Coinbase",
        "venue_type": VenueType.CEX,
        "api_type": ApiType.REST,
        "base_url": "https://api.exchange.coinbase.com",
        "trade_url_template": "https://www.coinbase.com/advanced-trade/{symbol}-USD",
    },
    {
        "name": "Uniswap V3",
        "venue_type": VenueType.DEX,
        "api_type": ApiType.SUBGRAPH,
        "base_url": "https://gateway.thegraph.com/api/subgraphs/id/5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV",
        "trade_url_template": "https://app.uniswap.org/swap?inputCurrency=ETH&outputCurrency={symbol}",
    },
]


async def seed_tokens(session) -> int:
    """Seed tokens, skipping existing ones. Returns count of new tokens."""
    created = 0
    for token_data in TOKENS:
        # Check if token already exists
        stmt = select(TokenModel).where(TokenModel.symbol == token_data["symbol"])
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            print(f"  ⏭️  Token {token_data['symbol']} already exists (id={existing.id})")
            continue

        token = TokenModel(
            symbol=token_data["symbol"],
            name=token_data["name"],
            category=token_data["category"],
            issuer=token_data["issuer"],
            chain=token_data.get("chain"),
            contract_address=token_data.get("contract_address"),
            is_active=True,
        )
        session.add(token)
        created += 1
        print(f"  ✅ Created token: {token_data['symbol']} ({token_data['name']})")

    return created


async def seed_venues(session) -> int:
    """Seed venues, skipping existing ones. Returns count of new venues."""
    created = 0
    for venue_data in VENUES:
        # Check if venue already exists
        stmt = select(VenueModel).where(VenueModel.name == venue_data["name"])
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            print(f"  ⏭️  Venue {venue_data['name']} already exists (id={existing.id})")
            continue

        venue = VenueModel(
            name=venue_data["name"],
            venue_type=venue_data["venue_type"],
            api_type=venue_data["api_type"],
            base_url=venue_data["base_url"],
            trade_url_template=venue_data.get("trade_url_template"),
            is_active=True,
        )
        session.add(venue)
        created += 1
        print(f"  ✅ Created venue: {venue_data['name']} ({venue_data['venue_type'].value})")

    return created


async def seed():
    """Run all seed operations."""
    print("\n" + "=" * 50)
    print("RWA Aggregator - Database Seeding")
    print("=" * 50)

    session_factory = get_async_session_local()
    async with session_factory() as session:
        print("\n📦 Seeding Tokens...")
        tokens_created = await seed_tokens(session)

        print("\n🏛️  Seeding Venues...")
        venues_created = await seed_venues(session)

        await session.commit()

        print("\n" + "-" * 50)
        print(f"✅ Seeding complete!")
        print(f"   Tokens created: {tokens_created}")
        print(f"   Venues created: {venues_created}")
        print("=" * 50 + "\n")

        # Verify final counts
        tokens_result = await session.execute(select(TokenModel))
        venues_result = await session.execute(select(VenueModel))
        print(f"📊 Total tokens in database: {len(tokens_result.scalars().all())}")
        print(f"📊 Total venues in database: {len(venues_result.scalars().all())}")


if __name__ == "__main__":
    asyncio.run(seed())
