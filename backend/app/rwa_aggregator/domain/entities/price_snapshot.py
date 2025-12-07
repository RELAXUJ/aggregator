"""PriceSnapshot entity representing a point-in-time price observation."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from app.rwa_aggregator.domain.value_objects.spread import Spread


@dataclass
class PriceSnapshot:
    """Domain entity representing a price observation from a specific venue.

    Attributes:
        id: Database identifier (None for unsaved entities).
        token_id: ID of the token being priced.
        venue_id: ID of the venue providing the price.
        bid: Best bid price.
        ask: Best ask price.
        volume_24h: 24-hour trading volume (optional).
        fetched_at: UTC timestamp when the price was fetched.
    """

    id: Optional[int]
    token_id: int
    venue_id: int
    bid: Decimal
    ask: Decimal
    volume_24h: Optional[Decimal] = None
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def mid(self) -> Decimal:
        """Calculate mid price from bid and ask."""
        return (self.bid + self.ask) / 2

    @property
    def spread(self) -> Spread:
        """Calculate spread value object from bid and ask."""
        return Spread.calculate(self.bid, self.ask)

    def is_stale(self, max_age_seconds: int = 60) -> bool:
        """Check if the price snapshot is considered stale.

        Args:
            max_age_seconds: Maximum age in seconds before considered stale.

        Returns:
            True if the snapshot is older than max_age_seconds.
        """
        age = (datetime.now(timezone.utc) - self.fetched_at).total_seconds()
        return age > max_age_seconds
