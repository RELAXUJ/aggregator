"""Alert entity representing a user's price alert subscription."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional

from app.rwa_aggregator.domain.value_objects.email_address import EmailAddress


class AlertType(Enum):
    """Types of price alerts."""

    SPREAD_BELOW = "spread_below"
    DAILY_SUMMARY = "daily_summary"


class AlertStatus(Enum):
    """Status of an alert subscription."""

    ACTIVE = "active"
    PAUSED = "paused"
    DELETED = "deleted"


@dataclass
class Alert:
    """Domain entity representing a user's alert configuration.

    Attributes:
        id: Database identifier (None for unsaved entities).
        email: Validated email address to send alerts to.
        token_id: ID of the token to monitor.
        threshold_pct: Spread percentage threshold that triggers the alert.
        alert_type: Type of alert (default: spread below threshold).
        status: Current status of the alert.
        last_triggered_at: Timestamp when the alert was last sent.
        created_at: Timestamp when the alert was created.
        cooldown_hours: Minimum hours between triggers to prevent spam.
    """

    id: Optional[int]
    email: EmailAddress
    token_id: int
    threshold_pct: Decimal
    alert_type: AlertType = AlertType.SPREAD_BELOW
    status: AlertStatus = AlertStatus.ACTIVE
    last_triggered_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    cooldown_hours: int = 1

    def can_trigger(self) -> bool:
        """Check if the alert is eligible to trigger.

        Must be active and past the cooldown period since last trigger.

        Returns:
            True if the alert can trigger.
        """
        if self.status != AlertStatus.ACTIVE:
            return False

        if self.last_triggered_at is None:
            return True

        cooldown_end = self.last_triggered_at + timedelta(hours=self.cooldown_hours)
        return datetime.now(timezone.utc) > cooldown_end

    def mark_triggered(self) -> None:
        """Update the last triggered timestamp to now."""
        self.last_triggered_at = datetime.now(timezone.utc)

    def pause(self) -> None:
        """Pause the alert (stop monitoring)."""
        self.status = AlertStatus.PAUSED

    def activate(self) -> None:
        """Activate the alert (resume monitoring)."""
        self.status = AlertStatus.ACTIVE
