"""Abstract repository interface for Venue entities."""

from abc import ABC, abstractmethod
from typing import List, Optional

from ..entities.venue import Venue


class VenueRepository(ABC):
    """Abstract repository for Venue persistence operations.

    Implementations should apply is_active filtering consistently
    with entity semantics. All methods are async to support
    non-blocking I/O in the infrastructure layer.
    """

    @abstractmethod
    async def get_by_id(self, venue_id: int) -> Optional[Venue]:
        """Retrieve a venue by its database ID.

        Args:
            venue_id: The unique identifier of the venue.

        Returns:
            The Venue entity if found, None otherwise.
        """
        pass

    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[Venue]:
        """Retrieve a venue by its display name.

        Args:
            name: The venue name (e.g., "Kraken", "Uniswap V3").

        Returns:
            The Venue entity if found, None otherwise.
        """
        pass

    @abstractmethod
    async def get_all_active(self) -> List[Venue]:
        """Retrieve all venues that are currently active.

        Returns:
            List of Venue entities where is_active is True.
        """
        pass

    @abstractmethod
    async def get_venues_for_token(self, token_id: int) -> List[Venue]:
        """Retrieve all active venues that provide prices for a token.

        Args:
            token_id: The ID of the token to find venues for.

        Returns:
            List of active Venue entities that have price data for the token.
        """
        pass

    @abstractmethod
    async def save(self, venue: Venue) -> Venue:
        """Persist a venue entity.

        For new venues (id is None), this creates a new record.
        For existing venues, this updates the existing record.

        Args:
            venue: The Venue entity to save.

        Returns:
            The saved Venue entity with its ID populated.
        """
        pass
