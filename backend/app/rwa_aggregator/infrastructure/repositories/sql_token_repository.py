"""SQLAlchemy implementation of TokenRepository.

Provides async database operations for Token entities using
SQLAlchemy 2.0 async patterns with asyncpg driver.
"""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.rwa_aggregator.domain.entities.token import MarketType, Token, TokenCategory
from app.rwa_aggregator.domain.repositories.token_repository import TokenRepository
from app.rwa_aggregator.infrastructure.db.models import TokenModel


class SqlTokenRepository(TokenRepository):
    """SQLAlchemy-based implementation of the TokenRepository interface."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with a database session.

        Args:
            session: An async SQLAlchemy session.
        """
        self._session = session

    async def get_by_id(self, token_id: int) -> Optional[Token]:
        """Retrieve a token by its database ID."""
        stmt = select(TokenModel).where(TokenModel.id == token_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_symbol(self, symbol: str) -> Optional[Token]:
        """Retrieve a token by its ticker symbol."""
        stmt = select(TokenModel).where(TokenModel.symbol == symbol.upper())
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_all_active(self) -> List[Token]:
        """Retrieve all tokens that are currently active."""
        stmt = select(TokenModel).where(TokenModel.is_active == True)  # noqa: E712
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def get_by_category(self, category: TokenCategory) -> List[Token]:
        """Retrieve all active tokens in a specific category."""
        stmt = select(TokenModel).where(
            TokenModel.is_active == True,  # noqa: E712
            TokenModel.category == category,
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def get_all_active_tradable(self) -> List[Token]:
        """Retrieve all active tokens that have tradable pairs.

        Returns only tokens where market_type == TRADABLE (i.e., tokens
        that have real spot trading pairs on exchanges).
        """
        stmt = select(TokenModel).where(
            TokenModel.is_active == True,  # noqa: E712
            TokenModel.market_type == MarketType.TRADABLE,
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def get_all_active_nav_only(self) -> List[Token]:
        """Retrieve all active tokens that are NAV-only (informational).

        Returns only tokens where market_type == NAV_ONLY (i.e., tokens
        that don't have active trading pairs, only NAV/AUM info).
        """
        stmt = select(TokenModel).where(
            TokenModel.is_active == True,  # noqa: E712
            TokenModel.market_type == MarketType.NAV_ONLY,
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def save(self, token: Token) -> Token:
        """Persist a token entity.

        Creates a new record if token.id is None, otherwise updates existing.
        """
        if token.id is None:
            # Insert new token
            model = self._to_model(token)
            self._session.add(model)
            await self._session.flush()
            await self._session.refresh(model)
            return self._to_entity(model)
        else:
            # Update existing token
            stmt = select(TokenModel).where(TokenModel.id == token.id)
            result = await self._session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                raise ValueError(f"Token with id {token.id} not found")

            model.symbol = token.symbol.upper()
            model.name = token.name
            model.category = token.category
            model.issuer = token.issuer
            model.chain = token.chain
            model.contract_address = token.contract_address
            model.is_active = token.is_active
            model.market_type = token.market_type

            await self._session.flush()
            return self._to_entity(model)

    def _to_entity(self, model: TokenModel) -> Token:
        """Convert a TokenModel to a Token domain entity."""
        return Token(
            id=model.id,
            symbol=model.symbol,
            name=model.name,
            category=model.category,
            issuer=model.issuer,
            chain=model.chain,
            contract_address=model.contract_address,
            is_active=model.is_active,
            market_type=model.market_type,
        )

    def _to_model(self, entity: Token) -> TokenModel:
        """Convert a Token domain entity to a TokenModel."""
        return TokenModel(
            id=entity.id,
            symbol=entity.symbol.upper(),
            name=entity.name,
            category=entity.category,
            issuer=entity.issuer,
            chain=entity.chain,
            contract_address=entity.contract_address,
            is_active=entity.is_active,
            market_type=entity.market_type,
        )
