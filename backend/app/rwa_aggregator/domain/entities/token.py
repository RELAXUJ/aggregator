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
    """

    id: Optional[int]
    symbol: str
    name: str
    category: TokenCategory
    issuer: str
    chain: Optional[str] = None
    contract_address: Optional[str] = None
    is_active: bool = True

    def deactivate(self) -> None:
        """Mark the token as inactive (stop tracking)."""
        self.is_active = False

    def activate(self) -> None:
        """Mark the token as active (resume tracking)."""
        self.is_active = True
