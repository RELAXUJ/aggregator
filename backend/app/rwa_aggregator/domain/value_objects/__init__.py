"""Domain value objects for the RWA Aggregator.

This module exports immutable value objects used throughout the domain layer:
- Price: Monetary values with currency
- Spread: Bid-ask spread calculations
- EmailAddress: Validated email addresses for alerts
"""

from app.rwa_aggregator.domain.value_objects.email_address import EmailAddress
from app.rwa_aggregator.domain.value_objects.price import Price
from app.rwa_aggregator.domain.value_objects.spread import Spread

__all__ = ["EmailAddress", "Price", "Spread"]
