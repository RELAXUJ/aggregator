"""HTMX-powered web dashboard routes.

Implements the main dashboard and HTMX partial endpoints for real-time
price updates without full page reloads.
"""

import os
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.rwa_aggregator.application.dto.price_dto import AggregatedPricesDTO
from app.rwa_aggregator.application.exceptions import NoPriceDataError, TokenNotFoundError
from app.rwa_aggregator.application.use_cases.get_aggregated_prices import GetAggregatedPricesUseCase
from app.rwa_aggregator.domain.entities.token import MarketType, Token
from app.rwa_aggregator.domain.services.price_calculator import PriceCalculator
from app.rwa_aggregator.infrastructure.db.session import get_db_session
from app.rwa_aggregator.infrastructure.repositories.sql_price_repository import SqlPriceRepository
from app.rwa_aggregator.infrastructure.repositories.sql_token_repository import SqlTokenRepository
from app.rwa_aggregator.infrastructure.repositories.sql_venue_repository import SqlVenueRepository

router = APIRouter()

# Templates directory - relative to the presentation package
_TEMPLATES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),  # presentation/
    "templates",
)
templates = Jinja2Templates(directory=_TEMPLATES_DIR)


def _create_use_case(session: AsyncSession) -> GetAggregatedPricesUseCase:
    """Factory function to create GetAggregatedPricesUseCase with dependencies."""
    return GetAggregatedPricesUseCase(
        token_repository=SqlTokenRepository(session),
        price_repository=SqlPriceRepository(session),
        venue_repository=SqlVenueRepository(session),
        price_calculator=PriceCalculator(),
    )


@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    token: Annotated[Optional[str], Query(description="Selected token symbol")] = None,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    """Render the main dashboard page.

    The dashboard displays:
    - Token selector dropdown
    - KPI cards (best bid, best ask, spread)
    - Price comparison table across venues

    Price data is loaded via HTMX partial for auto-refresh capability.

    Args:
        request: FastAPI request object.
        token: Initially selected token symbol (defaults to first active token).
        session: Database session (injected).

    Returns:
        Rendered dashboard HTML page.
    """
    token_repo = SqlTokenRepository(session)
    tokens = await token_repo.get_all_active()

    # Get tradable tokens separately for alert modal (only show tokens that support alerts)
    tradable_tokens = await token_repo.get_all_active_tradable()

    # Get NAV-only tokens for the informational section
    nav_only_tokens = await token_repo.get_all_active_nav_only()

    # Default to first token if none specified
    current_token_symbol = token.upper() if token else (tokens[0].symbol if tokens else None)

    # Get the current token entity for market_type info
    current_token_entity: Optional[Token] = None
    if current_token_symbol:
        current_token_entity = await token_repo.get_by_symbol(current_token_symbol)

    # Determine if current token is NAV-only
    is_nav_only = (
        current_token_entity is not None
        and current_token_entity.market_type == MarketType.NAV_ONLY
    )

    # Get initial price data for server-side rendering (fallback for no-JS)
    prices: Optional[AggregatedPricesDTO] = None
    error_message: Optional[str] = None

    # Only fetch prices for tradable tokens
    if current_token_entity and current_token_entity.market_type == MarketType.TRADABLE:
        use_case = _create_use_case(session)
        try:
            prices = await use_case.execute(
                base_symbol=current_token_symbol,
                include_stale=True,
            )
        except (TokenNotFoundError, NoPriceDataError) as e:
            error_message = e.message

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "tokens": tokens,
            "tradable_tokens": tradable_tokens,
            "nav_only_tokens": nav_only_tokens,
            "current_token": current_token_symbol,
            "current_token_entity": current_token_entity,
            "is_nav_only": is_nav_only,
            "prices": prices,
            "error_message": error_message,
        },
    )


@router.get("/partials/price-table/{token_symbol}", response_class=HTMLResponse)
async def price_table_partial(
    request: Request,
    token_symbol: str,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    """HTMX partial endpoint for the price comparison table.

    This endpoint is called by HTMX to update the price table without
    a full page reload. It's triggered:
    - On initial page load
    - Every 10 seconds (auto-refresh)
    - When user changes the token selector

    Args:
        request: FastAPI request object.
        token_symbol: Token symbol to fetch prices for.
        session: Database session (injected).

    Returns:
        Rendered price table HTML partial.
    """
    token_repo = SqlTokenRepository(session)
    token_entity = await token_repo.get_by_symbol(token_symbol.upper())

    # If token is NAV-only, return informational card instead of price table
    if token_entity and token_entity.market_type == MarketType.NAV_ONLY:
        return templates.TemplateResponse(
            request,
            "partials/price_table.html",
            {
                "prices": None,
                "error_message": None,
                "token_entity": token_entity,
                "is_nav_only": True,
            },
        )

    use_case = _create_use_case(session)
    prices: Optional[AggregatedPricesDTO] = None
    error_message: Optional[str] = None

    try:
        prices = await use_case.execute(
            base_symbol=token_symbol.upper(),
            include_stale=True,
        )
    except TokenNotFoundError as e:
        error_message = e.message
    except NoPriceDataError as e:
        error_message = e.message

    return templates.TemplateResponse(
        request,
        "partials/price_table.html",
        {
            "prices": prices,
            "error_message": error_message,
            "token_entity": token_entity,
            "is_nav_only": False,
        },
    )


@router.get("/partials/kpi-cards/{token_symbol}", response_class=HTMLResponse)
async def kpi_cards_partial(
    request: Request,
    token_symbol: str,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    """HTMX partial endpoint for KPI cards.

    Updates the best bid, best ask, and spread summary cards.

    Args:
        request: FastAPI request object.
        token_symbol: Token symbol to fetch prices for.
        session: Database session (injected).

    Returns:
        Rendered KPI cards HTML partial.
    """
    use_case = _create_use_case(session)
    prices: Optional[AggregatedPricesDTO] = None
    error_message: Optional[str] = None

    try:
        prices = await use_case.execute(
            base_symbol=token_symbol.upper(),
            include_stale=True,
        )
    except TokenNotFoundError as e:
        error_message = e.message
    except NoPriceDataError as e:
        error_message = e.message

    return templates.TemplateResponse(
        request,
        "partials/kpi_cards.html",
        {
            "prices": prices,
            "error_message": error_message,
        },
    )
