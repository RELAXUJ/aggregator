"""EmailAddress value object for validated email storage."""

import re
from dataclasses import dataclass


# Simple but effective email regex pattern
_EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)


@dataclass(frozen=True)
class EmailAddress:
    """Immutable value object representing a validated email address.

    Attributes:
        value: The validated email address string.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate email format after initialization."""
        if not _EMAIL_PATTERN.match(self.value):
            raise ValueError(f"Invalid email address: {self.value}")
