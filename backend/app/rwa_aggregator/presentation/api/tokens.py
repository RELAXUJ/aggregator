"""Token listing API endpoints.

Implements GET /api/tokens for retrieving active tokens.
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.rwa_aggregator.domain.entities.token import TokenCategory
from app.rwa_aggregator.infrastructure.db.session import get_db_session
from app.rwa_aggregator.infrastructure.repositories.sql_token_repository import SqlTokenRepository

router = APIRouter()


class TokenDTO(BaseModel):
    """Token data for API responses.

    Represents a tracked RWA token with its metadata.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Unique token identifier")
    symbol: str = Field(description="Token symbol (e.g., 'USDY')")
    name: str = Field(description="Human-readable token name")
    category: str = Field(description="Asset category (tbill, private_credit, real_estate, equity)")
    issuer: str = Field(description="Token issuer name")
    chain: Optional[str] = Field(default=None, description="Blockchain network (e.g., 'ethereum')")
    contract_address: Optional[str] = Field(default=None, description="Token contract address")


class TokenListDTO(BaseModel):
    """Paginated list of tokens for API responses."""

    tokens: list[TokenDTO] = Field(default_factory=list, description="List of tokens")
    total: int = Field(description="Total number of tokens")


@router.get("/tokens", response_model=TokenListDTO)
async def list_tokens(
    category: Annotated[
        Optional[str],
        Query(description="Filter by category (tbill, private_credit, real_estate, equity)")
    ] = None,
    session: AsyncSession = Depends(get_db_session),
) -> TokenListDTO:
    """List all active tokens.

    Returns all tokens that are currently active in the system,
    optionally filtered by asset category.

    Args:
        category: Optional category filter.
        session: Database session (injected).

    Returns:
        TokenListDTO with list of active tokens.
    """
    token_repo = SqlTokenRepository(session)

    if category:
        # Map string to TokenCategory enum
        try:
            category_enum = TokenCategory(category.lower())
            tokens = await token_repo.get_by_category(category_enum)
        except ValueError:
            # Invalid category - return empty list
            tokens = []
    else:
        tokens = await token_repo.get_all_active()

    token_dtos = [
        TokenDTO(
            id=t.id,  # type: ignore[arg-type]
            symbol=t.symbol,
            name=t.name,
            category=t.category.value,
            issuer=t.issuer,
            chain=t.chain,
            contract_address=t.contract_address,
        )
        for t in tokens
    ]

    return TokenListDTO(
        tokens=token_dtos,
        total=len(token_dtos),
    )


@router.get("/tokens/{token_symbol}", response_model=TokenDTO)
async def get_token(
    token_symbol: str,
    session: AsyncSession = Depends(get_db_session),
) -> TokenDTO:
    """Get a single token by symbol.

    Args:
        token_symbol: The token symbol (case-insensitive).
        session: Database session (injected).

    Returns:
        TokenDTO for the requested token.

    Raises:
        HTTPException: 404 if token not found.
    """
    from fastapi import HTTPException, status

    token_repo = SqlTokenRepository(session)
    token = await token_repo.get_by_symbol(token_symbol.upper())

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Token '{token_symbol.upper()}' not found",
        )

    return TokenDTO(
        id=token.id,  # type: ignore[arg-type]
        symbol=token.symbol,
        name=token.name,
        category=token.category.value,
        issuer=token.issuer,
        chain=token.chain,
        contract_address=token.contract_address,
    )
