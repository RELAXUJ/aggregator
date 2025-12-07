"""SQLAlchemy implementation of VenueRepository.

Provides async database operations for Venue entities using
SQLAlchemy 2.0 async patterns with asyncpg driver.
"""

from typing import List, Optional

from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.rwa_aggregator.domain.entities.venue import ApiType, Venue, VenueType
from app.rwa_aggregator.domain.repositories.venue_repository import VenueRepository
from app.rwa_aggregator.infrastructure.db.models import PriceSnapshotModel, VenueModel


class SqlVenueRepository(VenueRepository):
    """SQLAlchemy-based implementation of the VenueRepository interface."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with a database session.

        Args:
            session: An async SQLAlchemy session.
        """
        self._session = session

    async def get_by_id(self, venue_id: int) -> Optional[Venue]:
        """Retrieve a venue by its database ID."""
        stmt = select(VenueModel).where(VenueModel.id == venue_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_name(self, name: str) -> Optional[Venue]:
        """Retrieve a venue by its display name."""
        stmt = select(VenueModel).where(VenueModel.name == name)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_all_active(self) -> List[Venue]:
        """Retrieve all venues that are currently active."""
        stmt = select(VenueModel).where(VenueModel.is_active == True)  # noqa: E712
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def get_venues_for_token(self, token_id: int) -> List[Venue]:
        """Retrieve all active venues that provide prices for a token.

        Finds venues that have at least one price snapshot for the token.
        """
        # Subquery to find venue IDs that have price data for this token
        venue_ids_subq = (
            select(distinct(PriceSnapshotModel.venue_id))
            .where(PriceSnapshotModel.token_id == token_id)
            .scalar_subquery()
        )

        stmt = select(VenueModel).where(
            VenueModel.is_active == True,  # noqa: E712
            VenueModel.id.in_(venue_ids_subq),
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def save(self, venue: Venue) -> Venue:
        """Persist a venue entity.

        Creates a new record if venue.id is None, otherwise updates existing.
        """
        if venue.id is None:
            # Insert new venue
            model = self._to_model(venue)
            self._session.add(model)
            await self._session.flush()
            await self._session.refresh(model)
            return self._to_entity(model)
        else:
            # Update existing venue
            stmt = select(VenueModel).where(VenueModel.id == venue.id)
            result = await self._session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                raise ValueError(f"Venue with id {venue.id} not found")

            model.name = venue.name
            model.venue_type = venue.venue_type
            model.api_type = venue.api_type
            model.base_url = venue.base_url
            model.trade_url_template = venue.trade_url_template
            model.is_active = venue.is_active

            await self._session.flush()
            return self._to_entity(model)

    def _to_entity(self, model: VenueModel) -> Venue:
        """Convert a VenueModel to a Venue domain entity."""
        return Venue(
            id=model.id,
            name=model.name,
            venue_type=model.venue_type,
            api_type=model.api_type,
            base_url=model.base_url,
            trade_url_template=model.trade_url_template,
            is_active=model.is_active,
        )

    def _to_model(self, entity: Venue) -> VenueModel:
        """Convert a Venue domain entity to a VenueModel."""
        return VenueModel(
            id=entity.id,
            name=entity.name,
            venue_type=entity.venue_type,
            api_type=entity.api_type,
            base_url=entity.base_url,
            trade_url_template=entity.trade_url_template,
            is_active=entity.is_active,
        )
