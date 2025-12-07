"""Price value object for representing monetary values."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Self


@dataclass(frozen=True)
class Price:
    """Immutable value object representing a price with currency.

    Attributes:
        value: The decimal price value (must be non-negative).
        currency: The currency code (default: USD).
    """

    value: Decimal
    currency: str = "USD"

    def __post_init__(self) -> None:
        """Validate price constraints after initialization."""
        if self.value < 0:
            raise ValueError("Price cannot be negative")

    @classmethod
    def from_string(cls, value: str, currency: str = "USD") -> Self:
        """Create a Price from a string representation.

        Args:
            value: String representation of the price (e.g., "1.0012").
            currency: Currency code (default: USD).

        Returns:
            A new Price instance.

        Raises:
            ValueError: If the value cannot be parsed as a Decimal.
        """
        return cls(Decimal(value), currency)
