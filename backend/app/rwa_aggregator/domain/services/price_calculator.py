"""Price calculator domain service for best price aggregation.

Implements F-002: Best Price Calculation from the MVP specification.
- F-002.1: Best bid = highest bid across venues with data < 60s old
- F-002.2: Best ask = lowest ask across venues with data < 60s old
- F-002.3: Effective spread = (best_ask - best_bid) / mid * 100
- F-002.4: Exclude stale venues from calculation
"""

from dataclasses import dataclass
from typing import Optional

from app.rwa_aggregator.domain.entities.price_snapshot import PriceSnapshot
from app.rwa_aggregator.domain.value_objects.spread import Spread


@dataclass
class BestPrices:
    """Result of best price calculation across venues.

    Attributes:
        best_bid: The PriceSnapshot with the highest bid price, or None if no fresh data.
        best_ask: The PriceSnapshot with the lowest ask price, or None if no fresh data.
        effective_spread: The spread between best_bid and best_ask, or None if unavailable.
        venues_count: The number of fresh venues used in the calculation.
    """

    best_bid: Optional[PriceSnapshot]
    best_ask: Optional[PriceSnapshot]
    effective_spread: Optional[Spread]
    venues_count: int


class PriceCalculator:
    """Domain service for calculating best prices across multiple venues.

    This service implements pure domain logic with no infrastructure dependencies.
    It filters out stale price data and identifies the best execution opportunities.

    Attributes:
        max_staleness_seconds: Maximum age in seconds before a price is considered stale.
    """

    def __init__(self, max_staleness_seconds: int = 60) -> None:
        """Initialize the price calculator.

        Args:
            max_staleness_seconds: Maximum age for fresh prices (default 60s per F-002.1/F-002.2).
        """
        self._max_staleness_seconds = max_staleness_seconds

    def calculate_best_prices(self, snapshots: list[PriceSnapshot]) -> BestPrices:
        """Calculate best bid, best ask, and effective spread across venues.

        Filters out stale snapshots and computes:
        - Best bid: highest bid among fresh snapshots
        - Best ask: lowest ask among fresh snapshots
        - Effective spread: spread between best bid and best ask prices

        Args:
            snapshots: List of price snapshots from various venues.

        Returns:
            BestPrices containing best bid, best ask, effective spread, and venue count.
        """
        # Filter out stale snapshots per F-002.1/F-002.2/F-002.4
        fresh_snapshots = [
            s for s in snapshots if not s.is_stale(self._max_staleness_seconds)
        ]

        if not fresh_snapshots:
            return BestPrices(
                best_bid=None,
                best_ask=None,
                effective_spread=None,
                venues_count=0,
            )

        # Best bid = highest bid price (F-002.1)
        best_bid = max(fresh_snapshots, key=lambda s: s.bid)

        # Best ask = lowest ask price (F-002.2)
        best_ask = min(fresh_snapshots, key=lambda s: s.ask)

        # Effective spread calculated from best bid and best ask (F-002.3)
        effective_spread = Spread.calculate(best_bid.bid, best_ask.ask)

        return BestPrices(
            best_bid=best_bid,
            best_ask=best_ask,
            effective_spread=effective_spread,
            venues_count=len(fresh_snapshots),
        )
