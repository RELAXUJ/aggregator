"""Abstract repository interface for Alert entities."""

from abc import ABC, abstractmethod
from typing import List, Optional

from ..entities.alert import Alert, AlertStatus


class AlertRepository(ABC):
    """Abstract repository for Alert persistence operations.

    "Active" alerts refer to those with status == AlertStatus.ACTIVE.
    All methods are async to support non-blocking I/O in the
    infrastructure layer.
    """

    @abstractmethod
    async def get_by_id(self, alert_id: int) -> Optional[Alert]:
        """Retrieve an alert by its database ID.

        Args:
            alert_id: The unique identifier of the alert.

        Returns:
            The Alert entity if found, None otherwise.
        """
        pass

    @abstractmethod
    async def get_active_for_token(self, token_id: int) -> List[Alert]:
        """Retrieve all active alerts for a specific token.

        Used during price updates to check which alerts may need
        to be triggered based on new spread values.

        Args:
            token_id: The ID of the token to get alerts for.

        Returns:
            List of Alert entities with status == ACTIVE for the token.
        """
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> List[Alert]:
        """Retrieve all alerts for a specific email address.

        Args:
            email: The email address to search for.

        Returns:
            List of Alert entities associated with the email.
        """
        pass

    @abstractmethod
    async def get_all_active(self) -> List[Alert]:
        """Retrieve all active alerts across all tokens.

        Used for batch processing of alerts during price polling.

        Returns:
            List of Alert entities with status == ACTIVE.
        """
        pass

    @abstractmethod
    async def save(self, alert: Alert) -> Alert:
        """Persist an alert entity.

        For new alerts (id is None), this creates a new record.
        For existing alerts, this updates the existing record
        (e.g., updating last_triggered_at or status).

        Args:
            alert: The Alert entity to save.

        Returns:
            The saved Alert entity with its ID populated.
        """
        pass

    @abstractmethod
    async def delete(self, alert_id: int) -> bool:
        """Delete an alert by its ID.

        Implementations may choose logical delete (setting status
        to DELETED) or physical delete depending on data retention
        requirements.

        Args:
            alert_id: The ID of the alert to delete.

        Returns:
            True if the alert was deleted, False if not found.
        """
        pass
