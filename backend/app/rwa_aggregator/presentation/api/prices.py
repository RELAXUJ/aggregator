"""Price aggregation API endpoints.

Implements GET /api/prices and GET /api/prices/{token_symbol} using
the application-layer GetAggregatedPricesUseCase.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.rwa_aggregator.application.dto.price_dto import AggregatedPricesDTO
from app.rwa_aggregator.application.exceptions import NoPriceDataError, TokenNotFoundError
from app.rwa_aggregator.application.use_cases.get_aggregated_prices import GetAggregatedPricesUseCase
from app.rwa_aggregator.domain.services.price_calculator import PriceCalculator
from app.rwa_aggregator.infrastructure.db.session import get_db_session
from app.rwa_aggregator.infrastructure.repositories.sql_price_repository import SqlPriceRepository
from app.rwa_aggregator.infrastructure.repositories.sql_token_repository import SqlTokenRepository
from app.rwa_aggregator.infrastructure.repositories.sql_venue_repository import SqlVenueRepository

router = APIRouter()


def _create_use_case(session: AsyncSession) -> GetAggregatedPricesUseCase:
    """Factory function to create GetAggregatedPricesUseCase with dependencies.

    Args:
        session: Async database session.

    Returns:
        Configured GetAggregatedPricesUseCase instance.
    """
    return GetAggregatedPricesUseCase(
        token_repository=SqlTokenRepository(session),
        price_repository=SqlPriceRepository(session),
        venue_repository=SqlVenueRepository(session),
        price_calculator=PriceCalculator(),
    )


@router.get("/prices/{token_symbol}", response_model=AggregatedPricesDTO)
async def get_aggregated_prices(
    token_symbol: Annotated[str, Path(description="Token symbol (e.g., USDY, OUSG)")],
    include_stale: Annotated[bool, Query(description="Include stale prices (>60s old)")] = True,
    session: AsyncSession = Depends(get_db_session),
) -> AggregatedPricesDTO:
    """Get aggregated prices for a token across all venues.

    Retrieves the latest price data from all configured venues for the
    specified token, calculates best bid/ask, and returns a comprehensive
    price comparison view.

    Args:
        token_symbol: The token symbol to query (case-insensitive).
        include_stale: Whether to include prices older than staleness threshold.
        session: Database session (injected).

    Returns:
        AggregatedPricesDTO with best prices and per-venue breakdown.

    Raises:
        HTTPException: 404 if token not found or no price data available.
    """
    use_case = _create_use_case(session)

    try:
        result = await use_case.execute(
            base_symbol=token_symbol.upper(),
            include_stale=include_stale,
        )
        return result
    except TokenNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=e.message,
        ) from e
    except NoPriceDataError as e:
        raise HTTPException(
            status_code=404,
            detail=e.message,
        ) from e


@router.get("/prices", response_model=list[AggregatedPricesDTO])
async def list_all_prices(
    include_stale: Annotated[bool, Query(description="Include stale prices (>60s old)")] = True,
    session: AsyncSession = Depends(get_db_session),
) -> list[AggregatedPricesDTO]:
    """Get aggregated prices for all active tokens.

    Retrieves price data for all tokens that are currently active in the
    system, providing a complete overview of the RWA market.

    Args:
        include_stale: Whether to include prices older than staleness threshold.
        session: Database session (injected).

    Returns:
        List of AggregatedPricesDTO for each active token with price data.
        Tokens without any price data are skipped.
    """
    token_repo = SqlTokenRepository(session)
    use_case = _create_use_case(session)

    # Get all active tokens
    tokens = await token_repo.get_all_active()

    # Aggregate prices for each token, skipping those without data
    results: list[AggregatedPricesDTO] = []
    for token in tokens:
        try:
            prices = await use_case.execute(
                base_symbol=token.symbol,
                include_stale=include_stale,
            )
            results.append(prices)
        except NoPriceDataError:
            # Skip tokens without price data
            continue

    return results
