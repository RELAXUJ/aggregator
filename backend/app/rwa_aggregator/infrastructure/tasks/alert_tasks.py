"""Celery tasks for alert checking and notification."""

import logging

from app.rwa_aggregator.infrastructure.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="check_alerts")
def check_alerts(self) -> dict:
    """Check all active alerts against current prices.

    This task runs on a schedule (every 5 minutes by default) and:
    1. Loads all active alerts from database
    2. Gets current prices from cache
    3. Evaluates alert conditions
    4. Sends notifications for triggered alerts
    5. Updates alert status (cooldown, last triggered)

    Returns:
        Summary of alert check results.

    Raises:
        NotImplementedError: Task requires repositories and email service.
    """
    logger.error(
        "check_alerts task called but not implemented. "
        "Requires: AlertRepository, PriceRepository, AlertPolicy, and EmailSender."
    )
    raise NotImplementedError(
        "check_alerts requires: "
        "1) AlertRepository to get active alerts, "
        "2) PriceRepository/Redis to get current prices, "
        "3) AlertPolicy domain service for condition evaluation, "
        "4) EmailSender for notifications"
    )


@celery_app.task(bind=True, name="send_alert_notification")
def send_alert_notification(self, alert_id: str, current_price: str) -> dict:
    """Send notification for a triggered alert.

    Args:
        alert_id: The alert that was triggered.
        current_price: The price that triggered the alert.

    Returns:
        Notification delivery status.

    Raises:
        NotImplementedError: Task requires email service implementation.
    """
    logger.error(
        f"send_alert_notification({alert_id}) called but not implemented. "
        "Requires: AlertRepository and SendGrid EmailSender."
    )
    raise NotImplementedError(
        f"send_alert_notification({alert_id}) requires: "
        "1) AlertRepository to get alert details, "
        "2) SendGrid EmailSender to send notification"
    )


