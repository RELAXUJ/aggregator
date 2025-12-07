"""Supported tradable pairs configuration for the RWA aggregator.

This module defines which RWA token pairs are actively tradable on exchanges
and which venues support them. This serves as the source of truth for:
- Which pairs appear in the main spread dashboard
- Which venues to query for each pair
- Quote currency for price normalization

Pairs listed here should have:
- Active orderbook with real bid/ask data
- Sufficient liquidity for meaningful spreads
- Supported by at least one configured price feed client

For NAV-only tokens (OUSG, BENJI), see the MarketType.NAV_ONLY handling
in domain/entities/token.py.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class QuoteCurrency(Enum):
    """Quote currencies used for pricing RWA tokens."""

    USD = "USD"    # Direct USD pairs (e.g., PAXG/USD on Kraken)
    USDT = "USDT"  # Tether pairs (e.g., USDY/USDT on Bybit)
    USDC = "USDC"  # Circle USD pairs (e.g., USDY/USDC on DEXs)


@dataclass(frozen=True)
class TradablePair:
    """Configuration for a tradable RWA token pair.

    Attributes:
        base_symbol: The RWA token symbol (e.g., "USDY", "PAXG").
        quote_currency: The quote currency for pricing.
        venues: List of venue names that support this pair.
        is_primary: Whether this is the primary pair for the base token.
        description: Human-readable description of the pair.
    """

    base_symbol: str
    quote_currency: QuoteCurrency
    venues: tuple[str, ...]
    is_primary: bool = True
    description: Optional[str] = None


# ==============================================================================
# SUPPORTED TRADABLE PAIRS
# ==============================================================================
# These pairs have active orderbooks and are shown in the main spread dashboard.
# The price fetcher queries all configured venues for these base tokens.

SUPPORTED_TRADABLE_PAIRS: dict[str, TradablePair] = {
    # ------------------------------------------------------------------
    # RWA STABLECOIN PAIRS - Primary focus for the aggregator
    # ------------------------------------------------------------------
    "USDY/USDT": TradablePair(
        base_symbol="USDY",
        quote_currency=QuoteCurrency.USDT,
        venues=("Bybit",),
        is_primary=True,
        description="Ondo US Dollar Yield token - primary CEX pair on Bybit",
    ),
    "USDY/USDC": TradablePair(
        base_symbol="USDY",
        quote_currency=QuoteCurrency.USDC,
        venues=("Uniswap V3 (Mainnet)",),
        is_primary=False,
        description="Ondo US Dollar Yield token - DEX pair on Uniswap",
    ),
    # ------------------------------------------------------------------
    # COMMODITY-BACKED RWA TOKENS
    # ------------------------------------------------------------------
    "PAXG/USD": TradablePair(
        base_symbol="PAXG",
        quote_currency=QuoteCurrency.USD,
        venues=("Kraken", "Coinbase"),
        is_primary=True,
        description="Paxos Gold - tokenized physical gold",
    ),
    "PAXG/USDT": TradablePair(
        base_symbol="PAXG",
        quote_currency=QuoteCurrency.USDT,
        venues=("Bybit",),
        is_primary=False,
        description="Paxos Gold - USDT pair on Bybit",
    ),
    # ------------------------------------------------------------------
    # TEST/INFRASTRUCTURE PAIRS (for verification)
    # ------------------------------------------------------------------
    "ETH/USD": TradablePair(
        base_symbol="ETH",
        quote_currency=QuoteCurrency.USD,
        venues=("Kraken", "Coinbase"),
        is_primary=True,
        description="Ethereum - high-liquidity test pair for infrastructure",
    ),
    "ETH/USDT": TradablePair(
        base_symbol="ETH",
        quote_currency=QuoteCurrency.USDT,
        venues=("Bybit",),
        is_primary=False,
        description="Ethereum - USDT pair on Bybit",
    ),
}


# ==============================================================================
# NAV-ONLY ASSETS (Informational Only)
# ==============================================================================
# These tokens do NOT have active trading pairs. They are displayed in the
# informational section of the dashboard with metadata only (no bid/ask/spread).
# Defined here for documentation; actual handling is via MarketType.NAV_ONLY.

NAV_ONLY_ASSETS = {
    "OUSG": {
        "name": "Ondo Short-Term US Gov Treasuries",
        "issuer": "Ondo Finance",
        "category": "tbill",
        "status": "Secondary market dormant - 24h volume ≈ 0",
        "note": "Exchanges suspended trading; NAV/AUM only",
    },
    "BENJI": {
        "name": "Franklin OnChain US Gov Money Fund",
        "issuer": "Franklin Templeton",
        "category": "tbill",
        "status": "No spot trading pairs - fund token with P2P transfers",
        "note": "Tokenized MMF; focus on NAV, not orderbook",
    },
}


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def get_tradable_base_symbols() -> set[str]:
    """Get all unique base symbols that are tradable.

    Returns:
        Set of base token symbols with active trading pairs.
    """
    return {pair.base_symbol for pair in SUPPORTED_TRADABLE_PAIRS.values()}


def get_pairs_for_base(base_symbol: str) -> list[TradablePair]:
    """Get all tradable pairs for a given base token.

    Args:
        base_symbol: The base token symbol (e.g., "USDY").

    Returns:
        List of TradablePair configs for this base token.
    """
    return [
        pair
        for pair in SUPPORTED_TRADABLE_PAIRS.values()
        if pair.base_symbol == base_symbol.upper()
    ]


def get_primary_pair_for_base(base_symbol: str) -> Optional[TradablePair]:
    """Get the primary tradable pair for a base token.

    Args:
        base_symbol: The base token symbol.

    Returns:
        The primary TradablePair, or None if not found.
    """
    for pair in SUPPORTED_TRADABLE_PAIRS.values():
        if pair.base_symbol == base_symbol.upper() and pair.is_primary:
            return pair
    return None


def get_venues_for_base(base_symbol: str) -> set[str]:
    """Get all venues that support a given base token.

    Args:
        base_symbol: The base token symbol.

    Returns:
        Set of venue names that support trading this token.
    """
    venues = set()
    for pair in get_pairs_for_base(base_symbol):
        venues.update(pair.venues)
    return venues


def is_tradable_symbol(base_symbol: str) -> bool:
    """Check if a symbol has active trading pairs.

    Args:
        base_symbol: The token symbol to check.

    Returns:
        True if the symbol has at least one tradable pair.
    """
    return base_symbol.upper() in get_tradable_base_symbols()
