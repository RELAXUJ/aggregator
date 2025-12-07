"""Spread value object for bid-ask spread calculations."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Self


@dataclass(frozen=True)
class Spread:
    """Immutable value object representing a bid-ask spread percentage.

    The percentage is stored with 4 decimal places precision to align
    with the database schema (spread_pct DECIMAL(10, 4)).

    Attributes:
        percentage: The spread as a percentage (e.g., 0.06 means 0.06%).
    """

    percentage: Decimal

    @classmethod
    def calculate(cls, bid: Decimal, ask: Decimal) -> Self:
        """Calculate spread from bid and ask prices.

        Formula: spread_pct = ((ask - bid) / mid) * 100
        where mid = (bid + ask) / 2

        Args:
            bid: The bid price (must be positive).
            ask: The ask price (must be positive).

        Returns:
            A new Spread instance with the calculated percentage.

        Raises:
            ValueError: If bid or ask is not positive.
        """
        if bid <= 0 or ask <= 0:
            raise ValueError("Bid and ask must be positive")

        mid = (bid + ask) / 2
        spread_pct = ((ask - bid) / mid) * 100
        return cls(spread_pct.quantize(Decimal("0.0001")))

    def is_below_threshold(self, threshold_pct: Decimal) -> bool:
        """Check if the spread is below a given threshold.

        Used for alert logic to determine if spread is tight enough
        to trigger a notification.

        Args:
            threshold_pct: The threshold percentage to compare against.

        Returns:
            True if the spread percentage is below the threshold.
        """
        return self.percentage < threshold_pct
