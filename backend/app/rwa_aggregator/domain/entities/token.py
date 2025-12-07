"""Token entity representing an RWA token being tracked."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class TokenCategory(Enum):
    """Categories for RWA tokens matching dashboard filters."""

    TBILL = "tbill"
    PRIVATE_CREDIT = "private_credit"
    REAL_ESTATE = "real_estate"
    EQUITY = "equity"


class MarketType(Enum):
    """Market type indicating whether a token has active trading pairs.

    This enum drives several behavioral branches across the application:

    TRADABLE:
        - Real spot pairs exist on exchanges (e.g., USDY/USDT on Bybit, USDY/USDC on DEXs)
        - Price fetcher tasks will query venues for bid/ask data
        - Dashboard shows full order book table with bid/ask/spread per venue
        - Alerts can be created and evaluated for spread thresholds
        - CSV export is available with venue price data

    NAV_ONLY:
        - No active orderbook; only NAV/AUM info available (e.g., OUSG, BENJI)
        - Price fetcher tasks skip these tokens (no external API calls)
        - Dashboard shows informational card with issuer, category, chain metadata
        - Alerts cannot be created (no spread data to trigger on)
        - CSV export shows "No price data" message

    Use Cases:
        - USDY → TRADABLE (has USDY/USDT on Bybit, USDY/USDC on DEXs)
        - OUSG → NAV_ONLY (24h volume ≈ 0, exchanges suspended trading)
        - BENJI → NAV_ONLY (tokenized MMF with P2P transfers, no spot trading)
    """

    TRADABLE = "tradable"
    NAV_ONLY = "nav_only"


@dataclass
class Token:
    """Domain entity representing a tokenized Real-World Asset.

    Attributes:
        id: Database identifier (None for unsaved entities).
        symbol: Token ticker symbol (e.g., USDY, BENJI).
        name: Human-readable token name.
        category: Asset category for filtering.
        issuer: Token issuer name (e.g., Ondo Finance).
        chain: Blockchain where token is deployed.
        contract_address: Smart contract address.
        is_active: Whether the token is actively tracked.
        market_type: Whether the token has active trading pairs or is NAV-only.
    """

    id: Optional[int]
    symbol: str
    name: str
    category: TokenCategory
    issuer: str
    chain: Optional[str] = None
    contract_address: Optional[str] = None
    is_active: bool = True
    market_type: MarketType = MarketType.TRADABLE

    def deactivate(self) -> None:
        """Mark the token as inactive (stop tracking)."""
        self.is_active = False

    def activate(self) -> None:
        """Mark the token as active (resume tracking)."""
        self.is_active = True

    @property
    def is_tradable(self) -> bool:
        """Check if token has active trading pairs on exchanges.

        Returns:
            True if market_type is TRADABLE, meaning bid/ask/spread
            data can be fetched and alerts can be configured.
        """
        return self.market_type == MarketType.TRADABLE

    @property
    def is_nav_only(self) -> bool:
        """Check if token is informational only (no active trading).

        Returns:
            True if market_type is NAV_ONLY, meaning only metadata
            like issuer, category, chain should be displayed.
        """
        return self.market_type == MarketType.NAV_ONLY
