"""Abstract repository interface for PriceSnapshot entities."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from ..entities.price_snapshot import PriceSnapshot


class PriceRepository(ABC):
    """Abstract repository for PriceSnapshot persistence operations.

    All methods are async to support non-blocking I/O in the
    infrastructure layer. History queries return results ordered
    by fetched_at ascending (oldest first) unless noted otherwise.
    """

    @abstractmethod
    async def get_latest_for_token(self, token_id: int) -> List[PriceSnapshot]:
        """Get the latest price snapshot from each venue for a token.

        Returns one snapshot per venue, representing the most recent
        price observation from each active venue.

        Args:
            token_id: The ID of the token to get prices for.

        Returns:
            List of PriceSnapshot entities, one per venue with data.
        """
        pass

    @abstractmethod
    async def get_latest_for_token_venue(
        self, token_id: int, venue_id: int
    ) -> Optional[PriceSnapshot]:
        """Get the latest price snapshot for a specific token-venue pair.

        Args:
            token_id: The ID of the token.
            venue_id: The ID of the venue.

        Returns:
            The most recent PriceSnapshot if found, None otherwise.
        """
        pass

    @abstractmethod
    async def save(self, snapshot: PriceSnapshot) -> PriceSnapshot:
        """Persist a single price snapshot.

        Args:
            snapshot: The PriceSnapshot entity to save.

        Returns:
            The saved PriceSnapshot entity with its ID populated.
        """
        pass

    @abstractmethod
    async def save_batch(self, snapshots: List[PriceSnapshot]) -> List[PriceSnapshot]:
        """Persist multiple price snapshots in a single operation.

        Used for efficient bulk inserts when fetching prices from
        multiple venues simultaneously.

        Args:
            snapshots: List of PriceSnapshot entities to save.

        Returns:
            List of saved PriceSnapshot entities with IDs populated.
        """
        pass

    @abstractmethod
    async def get_history(
        self,
        token_id: int,
        venue_id: int,
        start: datetime,
        end: datetime,
    ) -> List[PriceSnapshot]:
        """Get historical price snapshots for a token-venue pair.

        Returns snapshots within the specified time range, ordered
        by fetched_at ascending (oldest first).

        Args:
            token_id: The ID of the token.
            venue_id: The ID of the venue.
            start: The start of the time range (inclusive).
            end: The end of the time range (inclusive).

        Returns:
            List of PriceSnapshot entities ordered by fetched_at ascending.
        """
        pass
