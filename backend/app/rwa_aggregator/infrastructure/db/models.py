"""SQLAlchemy ORM models mapping to domain entities.

These models represent the database schema and handle persistence concerns.
They should be converted to/from domain entities via repository mappers.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import DeclarativeBase, relationship


# Import domain enums for SQLAlchemy Enum columns
from app.rwa_aggregator.domain.entities.alert import AlertStatus, AlertType
from app.rwa_aggregator.domain.entities.token import MarketType, TokenCategory
from app.rwa_aggregator.domain.entities.venue import ApiType, VenueType


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class TokenModel(Base):
    """ORM model for tokens table."""

    __tablename__ = "tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    category = Column(SQLEnum(TokenCategory), nullable=False)
    issuer = Column(String(100), nullable=False)
    chain = Column(String(50), nullable=True)
    contract_address = Column(String(66), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    market_type = Column(
        SQLEnum(MarketType), nullable=False, default=MarketType.TRADABLE
    )

    # Relationships
    price_snapshots = relationship(
        "PriceSnapshotModel", back_populates="token", cascade="all, delete-orphan"
    )
    alerts = relationship(
        "AlertModel", back_populates="token", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<TokenModel(id={self.id}, symbol='{self.symbol}')>"


class VenueModel(Base):
    """ORM model for venues table."""

    __tablename__ = "venues"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    venue_type = Column(SQLEnum(VenueType), nullable=False)
    api_type = Column(SQLEnum(ApiType), nullable=False)
    base_url = Column(String(255), nullable=False)
    trade_url_template = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    price_snapshots = relationship(
        "PriceSnapshotModel", back_populates="venue", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<VenueModel(id={self.id}, name='{self.name}')>"


class PriceSnapshotModel(Base):
    """ORM model for price_snapshots table."""

    __tablename__ = "price_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    token_id = Column(Integer, ForeignKey("tokens.id"), nullable=False, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    bid = Column(Numeric(20, 8), nullable=False)
    ask = Column(Numeric(20, 8), nullable=False)
    mid = Column(Numeric(20, 8), nullable=False)
    spread_pct = Column(Numeric(10, 4), nullable=False)
    volume_24h = Column(Numeric(20, 2), nullable=True)
    fetched_at = Column(DateTime(timezone=True), nullable=False, index=True)

    # Relationships
    token = relationship("TokenModel", back_populates="price_snapshots")
    venue = relationship("VenueModel", back_populates="price_snapshots")

    # Composite index for efficient queries
    __table_args__ = (
        Index(
            "ix_price_snapshots_token_venue_time",
            "token_id",
            "venue_id",
            "fetched_at",
        ),
    )

    def __repr__(self) -> str:
        return f"<PriceSnapshotModel(id={self.id}, token_id={self.token_id}, venue_id={self.venue_id})>"


class AlertModel(Base):
    """ORM model for alerts table."""

    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, index=True)
    token_id = Column(Integer, ForeignKey("tokens.id"), nullable=False, index=True)
    threshold_pct = Column(Numeric(5, 2), nullable=False, default=2.00)
    alert_type = Column(
        SQLEnum(AlertType), nullable=False, default=AlertType.SPREAD_BELOW
    )
    status = Column(SQLEnum(AlertStatus), nullable=False, default=AlertStatus.ACTIVE)
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    cooldown_hours = Column(Integer, nullable=False, default=1)

    # Relationships
    token = relationship("TokenModel", back_populates="alerts")

    # Index for efficient alert checking
    __table_args__ = (Index("ix_alerts_token_status", "token_id", "status"),)

    def __repr__(self) -> str:
        return f"<AlertModel(id={self.id}, email='{self.email}', token_id={self.token_id})>"
