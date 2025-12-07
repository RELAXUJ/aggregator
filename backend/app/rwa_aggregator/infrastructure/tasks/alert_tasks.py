"""Celery tasks for alert checking and notification."""

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from app.core.config import get_settings
from app.rwa_aggregator.domain.services.alert_policy import AlertPolicy
from app.rwa_aggregator.domain.services.price_calculator import PriceCalculator
from app.rwa_aggregator.infrastructure.db.session import get_async_session_local
from app.rwa_aggregator.infrastructure.repositories.sql_alert_repository import (
    SqlAlertRepository,
)
from app.rwa_aggregator.infrastructure.repositories.sql_price_repository import (
    SqlPriceRepository,
)
from app.rwa_aggregator.infrastructure.repositories.sql_token_repository import (
    SqlTokenRepository,
)
from app.rwa_aggregator.infrastructure.repositories.sql_venue_repository import (
    SqlVenueRepository,
)
from app.rwa_aggregator.infrastructure.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _send_alert_email(
    to_email: str,
    token_symbol: str,
    current_spread: Decimal,
    best_bid_venue: str,
    best_bid_price: Decimal,
    best_ask_venue: str,
    best_ask_price: Decimal,
) -> bool:
    """Send alert email via Postmark or log to console in dev mode.

    Returns:
        True if email was sent successfully.
    """
    settings = get_settings()

    # Build email content
    subject = f"🔔 {token_symbol} Spread Alert: {current_spread:.2f}%"
    html_body = f"""
    <h2>{token_symbol} Spread Alert</h2>
    <p>The spread has dropped to <strong>{current_spread:.2f}%</strong></p>
    <ul>
        <li>Best Bid: ${best_bid_price:.4f} on {best_bid_venue}</li>
        <li>Best Ask: ${best_ask_price:.4f} on {best_ask_venue}</li>
    </ul>
    <p>Time to trade!</p>
    """
    text_body = f"""
{token_symbol} Spread Alert

The spread has dropped to {current_spread:.2f}%

Best Bid: ${best_bid_price:.4f} on {best_bid_venue}
Best Ask: ${best_ask_price:.4f} on {best_ask_venue}

Time to trade!
    """.strip()

    if not settings.postmark_api_token:
        # Dev mode - just log
        logger.info(
            f"[DEV MODE] Alert email to {to_email}:\n"
            f"  Subject: {subject}\n"
            f"  Token: {token_symbol}\n"
            f"  Spread: {current_spread:.2f}%\n"
            f"  Best Bid: ${best_bid_price:.4f} @ {best_bid_venue}\n"
            f"  Best Ask: ${best_ask_price:.4f} @ {best_ask_venue}"
        )
        return True

    # Send via Postmark
    try:
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.postmarkapp.com/email",
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "X-Postmark-Server-Token": settings.postmark_api_token,
                },
                json={
                    "From": settings.alert_from_email,
                    "To": to_email,
                    "Subject": subject,
                    "HtmlBody": html_body,
                    "TextBody": text_body,
                    "MessageStream": "outbound",  # Default transactional stream
                },
                timeout=10.0,
            )

            if response.status_code != 200:
                logger.error(
                    f"Postmark error: {response.status_code} - {response.text}"
                )
                return False

            logger.info(f"Alert email sent to {to_email} for {token_symbol}")
            return True

    except Exception as e:
        logger.exception(f"Failed to send email: {e}")
        return False


async def _check_alerts_async() -> dict[str, Any]:
    """Async implementation of alert checking.

    Returns:
        Summary of alert check results.
    """
    settings = get_settings()
    results = {
        "alerts_checked": 0,
        "alerts_triggered": 0,
        "emails_sent": 0,
        "errors": [],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    session_factory = get_async_session_local()

    async with session_factory() as session:
        alert_repo = SqlAlertRepository(session)
        price_repo = SqlPriceRepository(session)
        token_repo = SqlTokenRepository(session)
        venue_repo = SqlVenueRepository(session)

        calculator = PriceCalculator(
            max_staleness_seconds=settings.staleness_threshold_seconds
        )
        policy = AlertPolicy()

        # Get all active alerts
        alerts = await alert_repo.get_all_active()
        logger.info(f"Checking {len(alerts)} active alerts")

        # Build venue ID -> name map for display
        venues = await venue_repo.get_all_active()
        venue_names = {v.id: v.name for v in venues}

        for alert in alerts:
            results["alerts_checked"] += 1

            try:
                # Get token info to check if tradable
                token = await token_repo.get_by_id(alert.token_id)
                if not token:
                    logger.debug(f"Token not found for alert token_id={alert.token_id}")
                    continue

                # Skip NAV-only tokens - they don't have price data
                if token.is_nav_only:
                    logger.debug(
                        f"Skipping alert for NAV-only token {token.symbol} "
                        f"(token_id={alert.token_id})"
                    )
                    continue

                # Get current prices for the token
                snapshots = await price_repo.get_latest_for_token(alert.token_id)

                if not snapshots:
                    logger.debug(f"No price data for token_id={alert.token_id}")
                    continue

                # Calculate best prices
                best_prices = calculator.calculate_best_prices(snapshots)

                if not best_prices.effective_spread:
                    logger.debug(
                        f"No fresh spread data for token_id={alert.token_id}"
                    )
                    continue

                # For simplicity, we don't track previous spread in this implementation
                # Just check if current spread is below threshold
                current_spread = best_prices.effective_spread

                # Check if alert should trigger
                # Note: We pass None for previous_spread, so it will trigger if below threshold
                if policy.should_trigger(alert, current_spread, None):
                    # Token info already fetched above for NAV-only check
                    # Get venue names
                    best_bid_venue = venue_names.get(
                        best_prices.best_bid.venue_id, "Unknown"
                    )
                    best_ask_venue = venue_names.get(
                        best_prices.best_ask.venue_id, "Unknown"
                    )

                    # Send notification
                    email_sent = await _send_alert_email(
                        to_email=str(alert.email),
                        token_symbol=token.symbol,
                        current_spread=current_spread.percentage,
                        best_bid_venue=best_bid_venue,
                        best_bid_price=best_prices.best_bid.bid,
                        best_ask_venue=best_ask_venue,
                        best_ask_price=best_prices.best_ask.ask,
                    )

                    if email_sent:
                        results["emails_sent"] += 1

                    # Mark alert as triggered (updates cooldown)
                    alert.mark_triggered()
                    await alert_repo.save(alert)
                    results["alerts_triggered"] += 1

                    logger.info(
                        f"Alert triggered for {token.symbol}: "
                        f"spread {current_spread.percentage:.2f}% < threshold {alert.threshold_pct}%"
                    )

            except Exception as e:
                error_msg = f"Error checking alert {alert.id}: {str(e)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)

        await session.commit()

    logger.info(
        f"Alert check complete: {results['alerts_checked']} checked, "
        f"{results['alerts_triggered']} triggered, {results['emails_sent']} emails sent"
    )
    return results


@celery_app.task(
    bind=True,
    name="app.rwa_aggregator.infrastructure.tasks.alert_tasks.check_alerts",
)
def check_alerts(self) -> dict:
    """Check all active alerts against current prices.

    This task runs on a schedule (every 5 minutes by default) and:
    1. Loads all active alerts from database
    2. Gets current prices for each alert's token
    3. Evaluates alert conditions using AlertPolicy
    4. Sends notifications for triggered alerts
    5. Updates alert status (cooldown, last triggered)

    Returns:
        Summary of alert check results.
    """
    logger.info("Starting check_alerts task")
    try:
        result = asyncio.run(_check_alerts_async())
        return result
    except Exception as e:
        logger.exception(f"check_alerts failed: {e}")
        raise


@celery_app.task(
    bind=True,
    name="app.rwa_aggregator.infrastructure.tasks.alert_tasks.send_alert_notification",
)
def send_alert_notification(
    self, alert_id: int, token_symbol: str, current_spread: str
) -> dict:
    """Send notification for a triggered alert.

    Args:
        alert_id: The alert that was triggered.
        token_symbol: The token symbol.
        current_spread: The spread that triggered the alert.

    Returns:
        Notification delivery status.
    """
    logger.info(f"send_alert_notification called for alert {alert_id}")

    async def _send():
        session_factory = get_async_session_local()
        async with session_factory() as session:
            alert_repo = SqlAlertRepository(session)
            alert = await alert_repo.get_by_id(alert_id)

            if not alert:
                return {"success": False, "error": f"Alert {alert_id} not found"}

            # For manual notification, just log
            logger.info(
                f"Manual notification: Alert {alert_id} for {token_symbol} "
                f"triggered at spread {current_spread}"
            )

            return {
                "success": True,
                "alert_id": alert_id,
                "token": token_symbol,
                "spread": current_spread,
            }

    try:
        return asyncio.run(_send())
    except Exception as e:
        logger.exception(f"send_alert_notification failed: {e}")
        raise
