"""SQLAlchemy implementation of PriceRepository.

Provides async database operations for PriceSnapshot entities using
SQLAlchemy 2.0 async patterns with asyncpg driver.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import and_, desc, distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.rwa_aggregator.domain.entities.price_snapshot import PriceSnapshot
from app.rwa_aggregator.domain.repositories.price_repository import PriceRepository
from app.rwa_aggregator.infrastructure.db.models import PriceSnapshotModel


class SqlPriceRepository(PriceRepository):
    """SQLAlchemy-based implementation of the PriceRepository interface."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with a database session.

        Args:
            session: An async SQLAlchemy session.
        """
        self._session = session

    async def get_latest_for_token(self, token_id: int) -> List[PriceSnapshot]:
        """Get the latest price snapshot from each venue for a token.

        Uses a correlated subquery to efficiently find the most recent
        snapshot per venue.
        """
        # Subquery to get max fetched_at per venue for this token
        latest_subq = (
            select(
                PriceSnapshotModel.venue_id,
                PriceSnapshotModel.token_id,
                # Use func.max for aggregate
                PriceSnapshotModel.fetched_at,
            )
            .where(PriceSnapshotModel.token_id == token_id)
            .group_by(PriceSnapshotModel.venue_id, PriceSnapshotModel.token_id)
        ).subquery()

        # Alternative approach: use DISTINCT ON equivalent via window functions
        # For better cross-database compatibility, use row_number approach
        from sqlalchemy import func

        # Get distinct venue_ids for this token
        venue_ids_stmt = select(distinct(PriceSnapshotModel.venue_id)).where(
            PriceSnapshotModel.token_id == token_id
        )
        venue_result = await self._session.execute(venue_ids_stmt)
        venue_ids = [row[0] for row in venue_result.fetchall()]

        snapshots = []
        for venue_id in venue_ids:
            snapshot = await self.get_latest_for_token_venue(token_id, venue_id)
            if snapshot:
                snapshots.append(snapshot)

        return snapshots

    async def get_latest_for_token_venue(
        self, token_id: int, venue_id: int
    ) -> Optional[PriceSnapshot]:
        """Get the latest price snapshot for a specific token-venue pair."""
        stmt = (
            select(PriceSnapshotModel)
            .where(
                PriceSnapshotModel.token_id == token_id,
                PriceSnapshotModel.venue_id == venue_id,
            )
            .order_by(desc(PriceSnapshotModel.fetched_at))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, snapshot: PriceSnapshot) -> PriceSnapshot:
        """Persist a single price snapshot."""
        model = self._to_model(snapshot)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def save_batch(self, snapshots: List[PriceSnapshot]) -> List[PriceSnapshot]:
        """Persist multiple price snapshots in a single operation."""
        if not snapshots:
            return []

        models = [self._to_model(s) for s in snapshots]
        self._session.add_all(models)
        await self._session.flush()

        # Refresh all models to get generated IDs
        for model in models:
            await self._session.refresh(model)

        return [self._to_entity(m) for m in models]

    async def get_history(
        self,
        token_id: int,
        venue_id: int,
        start: datetime,
        end: datetime,
    ) -> List[PriceSnapshot]:
        """Get historical price snapshots for a token-venue pair.

        Returns snapshots within the time range, ordered by fetched_at ascending.
        """
        stmt = (
            select(PriceSnapshotModel)
            .where(
                PriceSnapshotModel.token_id == token_id,
                PriceSnapshotModel.venue_id == venue_id,
                PriceSnapshotModel.fetched_at >= start,
                PriceSnapshotModel.fetched_at <= end,
            )
            .order_by(PriceSnapshotModel.fetched_at.asc())
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    def _to_entity(self, model: PriceSnapshotModel) -> PriceSnapshot:
        """Convert a PriceSnapshotModel to a PriceSnapshot domain entity."""
        return PriceSnapshot(
            id=model.id,
            token_id=model.token_id,
            venue_id=model.venue_id,
            bid=Decimal(str(model.bid)),
            ask=Decimal(str(model.ask)),
            volume_24h=Decimal(str(model.volume_24h)) if model.volume_24h else None,
            fetched_at=model.fetched_at,
        )

    def _to_model(self, entity: PriceSnapshot) -> PriceSnapshotModel:
        """Convert a PriceSnapshot domain entity to a PriceSnapshotModel."""
        return PriceSnapshotModel(
            id=entity.id,
            token_id=entity.token_id,
            venue_id=entity.venue_id,
            bid=entity.bid,
            ask=entity.ask,
            mid=entity.mid,  # Calculated property
            spread_pct=entity.spread.percentage,  # From Spread value object
            volume_24h=entity.volume_24h,
            fetched_at=entity.fetched_at,
        )
