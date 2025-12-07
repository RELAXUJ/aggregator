"""SQLAlchemy implementation of AlertRepository.

Provides async database operations for Alert entities using
SQLAlchemy 2.0 async patterns with asyncpg driver.
"""

from decimal import Decimal
from typing import List, Optional

from sqlalchemy import delete, select, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.rwa_aggregator.domain.entities.alert import Alert, AlertStatus, AlertType
from app.rwa_aggregator.domain.repositories.alert_repository import AlertRepository
from app.rwa_aggregator.domain.value_objects.email_address import EmailAddress
from app.rwa_aggregator.infrastructure.db.models import AlertModel


class SqlAlertRepository(AlertRepository):
    """SQLAlchemy-based implementation of the AlertRepository interface."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with a database session.

        Args:
            session: An async SQLAlchemy session.
        """
        self._session = session

    async def get_by_id(self, alert_id: int) -> Optional[Alert]:
        """Retrieve an alert by its database ID."""
        stmt = select(AlertModel).where(AlertModel.id == alert_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_active_for_token(self, token_id: int) -> List[Alert]:
        """Retrieve all active alerts for a specific token."""
        stmt = select(AlertModel).where(
            AlertModel.token_id == token_id,
            AlertModel.status == AlertStatus.ACTIVE,
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def get_by_email(self, email: str) -> List[Alert]:
        """Retrieve all alerts for a specific email address."""
        # Normalize email for comparison
        normalized_email = email.lower().strip()
        stmt = select(AlertModel).where(AlertModel.email == normalized_email)
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def get_all_active(self) -> List[Alert]:
        """Retrieve all active alerts across all tokens."""
        stmt = select(AlertModel).where(AlertModel.status == AlertStatus.ACTIVE)
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def get_all_unique_emails(self) -> List[str]:
        """Retrieve all unique email addresses that have created alerts."""
        stmt = select(distinct(AlertModel.email))
        result = await self._session.execute(stmt)
        emails = result.scalars().all()
        return list(emails)

    async def save(self, alert: Alert) -> Alert:
        """Persist an alert entity.

        Creates a new record if alert.id is None, otherwise updates existing.
        """
        if alert.id is None:
            # Insert new alert
            model = self._to_model(alert)
            self._session.add(model)
            await self._session.flush()
            await self._session.refresh(model)
            return self._to_entity(model)
        else:
            # Update existing alert
            stmt = select(AlertModel).where(AlertModel.id == alert.id)
            result = await self._session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                raise ValueError(f"Alert with id {alert.id} not found")

            model.email = alert.email.value.lower()
            model.token_id = alert.token_id
            model.threshold_pct = alert.threshold_pct
            model.alert_type = alert.alert_type
            model.status = alert.status
            model.last_triggered_at = alert.last_triggered_at
            model.cooldown_hours = alert.cooldown_hours
            # Note: created_at should not be updated

            await self._session.flush()
            return self._to_entity(model)

    async def delete(self, alert_id: int) -> bool:
        """Delete an alert by its ID.

        Uses logical delete by setting status to DELETED.
        """
        stmt = select(AlertModel).where(AlertModel.id == alert_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return False

        model.status = AlertStatus.DELETED
        await self._session.flush()
        return True

    def _to_entity(self, model: AlertModel) -> Alert:
        """Convert an AlertModel to an Alert domain entity."""
        # Ensure email is a string - handle case where it might have been stored incorrectly
        email_str = str(model.email)
        # If somehow stored as dataclass representation, extract the actual email
        if email_str.startswith("emailaddress(value="):
            import re
            match = re.search(r"value='([^']+)'", email_str)
            if match:
                email_str = match.group(1)
        
        return Alert(
            id=model.id,
            email=EmailAddress(email_str),
            token_id=model.token_id,
            threshold_pct=Decimal(str(model.threshold_pct)),
            alert_type=model.alert_type,
            status=model.status,
            last_triggered_at=model.last_triggered_at,
            created_at=model.created_at,
            cooldown_hours=model.cooldown_hours,
        )

    def _to_model(self, entity: Alert) -> AlertModel:
        """Convert an Alert domain entity to an AlertModel."""
        return AlertModel(
            id=entity.id,
            email=entity.email.value.lower(),
            token_id=entity.token_id,
            threshold_pct=entity.threshold_pct,
            alert_type=entity.alert_type,
            status=entity.status,
            last_triggered_at=entity.last_triggered_at,
            created_at=entity.created_at,
            cooldown_hours=entity.cooldown_hours,
        )
