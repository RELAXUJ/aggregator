"""Domain repository interfaces for the RWA Aggregator.

This module defines abstract repository interfaces that establish the contract
between the domain layer and persistence implementations. These interfaces:

- Allow the domain to remain independent of database/ORM specifics
- Enable infrastructure adapters to implement persistence logic
- Support dependency injection for testing with mock repositories
- Use async methods to support non-blocking I/O operations

Concrete implementations live in the infrastructure layer
(e.g., backend/app/rwa_aggregator/infrastructure/repositories/).
"""

from app.rwa_aggregator.domain.repositories.alert_repository import AlertRepository
from app.rwa_aggregator.domain.repositories.price_repository import PriceRepository
from app.rwa_aggregator.domain.repositories.token_repository import TokenRepository
from app.rwa_aggregator.domain.repositories.venue_repository import VenueRepository

__all__ = [
    "AlertRepository",
    "PriceRepository",
    "TokenRepository",
    "VenueRepository",
]
