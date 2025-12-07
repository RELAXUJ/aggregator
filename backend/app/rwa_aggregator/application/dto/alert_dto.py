"""Data Transfer Objects for alert-related API requests and responses.

These DTOs represent the external contract for alert operations exposed
through the API layer. They are decoupled from domain entities and
optimized for JSON serialization.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.rwa_aggregator.domain.entities.alert import AlertStatus, AlertType


class CreateAlertRequest(BaseModel):
    """Request payload for creating a new price alert.

    Used by the API endpoint to validate incoming alert creation requests.
    """

    model_config = ConfigDict(
        json_encoders={Decimal: lambda v: float(v)},
    )

    email: EmailStr = Field(description="Email address to receive alert notifications")
    base_token_symbol: str = Field(description="Base token symbol to monitor (e.g., 'USDY')")
    quote_token_symbol: str = Field(default="USD", description="Quote token symbol (e.g., 'USD')")
    threshold_pct: Decimal = Field(
        gt=0,
        le=100,
        description="Spread percentage threshold that triggers the alert (e.g., 0.05 for 0.05%)"
    )
    alert_type: AlertType = Field(
        default=AlertType.SPREAD_BELOW,
        description="Type of alert: 'spread_below' triggers when spread drops below threshold"
    )
    cooldown_hours: int = Field(
        default=1,
        ge=0,
        le=168,
        description="Minimum hours between alert triggers to prevent spam (0-168)"
    )


class UpdateAlertRequest(BaseModel):
    """Request payload for updating an existing alert.

    All fields are optional - only provided fields will be updated.
    """

    model_config = ConfigDict(
        json_encoders={Decimal: lambda v: float(v)},
    )

    threshold_pct: Optional[Decimal] = Field(
        default=None,
        gt=0,
        le=100,
        description="New spread percentage threshold"
    )
    status: Optional[AlertStatus] = Field(
        default=None,
        description="New alert status (active, paused, deleted)"
    )
    cooldown_hours: Optional[int] = Field(
        default=None,
        ge=0,
        le=168,
        description="New cooldown period in hours"
    )


class AlertDTO(BaseModel):
    """Alert data for API responses.

    Represents a user's alert subscription as returned by the API,
    including all relevant metadata for display.
    """

    model_config = ConfigDict(
        json_encoders={Decimal: lambda v: float(v)},
        from_attributes=True,
    )

    id: int = Field(description="Unique alert identifier")
    email: EmailStr = Field(description="Email address receiving notifications")
    base_token_symbol: str = Field(description="Base token symbol being monitored")
    base_token_name: str = Field(description="Human-readable base token name")
    quote_token_symbol: str = Field(default="USD", description="Quote token symbol")
    threshold_pct: Decimal = Field(description="Spread percentage threshold")
    alert_type: AlertType = Field(description="Type of alert")
    status: AlertStatus = Field(description="Current alert status")
    cooldown_hours: int = Field(description="Hours between triggers")
    last_triggered_at: Optional[datetime] = Field(
        default=None,
        description="When the alert was last triggered (UTC)"
    )
    created_at: datetime = Field(description="When the alert was created (UTC)")
    can_trigger: bool = Field(
        default=True,
        description="Whether the alert is eligible to trigger (active and past cooldown)"
    )


class AlertListDTO(BaseModel):
    """Paginated list of alerts for API responses."""

    alerts: list[AlertDTO] = Field(default_factory=list, description="List of alerts")
    total: int = Field(description="Total number of alerts matching the query")
    page: int = Field(default=1, ge=1, description="Current page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Number of alerts per page")
