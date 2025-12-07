"""Application layer - use cases and orchestration.

This layer contains:
- DTOs: Data Transfer Objects for API input/output
- Use Cases: Application services that orchestrate domain logic
- Exceptions: Application-level error types
"""

from app.rwa_aggregator.application.dto import (
    AggregatedPricesDTO,
    AlertDTO,
    AlertListDTO,
    BestPriceDTO,
    CreateAlertRequest,
    UpdateAlertRequest,
    VenuePriceDTO,
)
from app.rwa_aggregator.application.exceptions import (
    AlertAlreadyExistsError,
    AlertNotFoundError,
    ApplicationError,
    InvalidEmailError,
    NoPriceDataError,
    TokenNotFoundError,
    VenueNotFoundError,
)
from app.rwa_aggregator.application.use_cases import (
    CreateAlertUseCase,
    DeleteAlertUseCase,
    GetAggregatedPricesUseCase,
    GetAlertsByEmailUseCase,
)

__all__ = [
    # DTOs
    "VenuePriceDTO",
    "BestPriceDTO",
    "AggregatedPricesDTO",
    "CreateAlertRequest",
    "UpdateAlertRequest",
    "AlertDTO",
    "AlertListDTO",
    # Use Cases
    "GetAggregatedPricesUseCase",
    "CreateAlertUseCase",
    "GetAlertsByEmailUseCase",
    "DeleteAlertUseCase",
    # Exceptions
    "ApplicationError",
    "TokenNotFoundError",
    "VenueNotFoundError",
    "AlertNotFoundError",
    "AlertAlreadyExistsError",
    "InvalidEmailError",
    "NoPriceDataError",
]
