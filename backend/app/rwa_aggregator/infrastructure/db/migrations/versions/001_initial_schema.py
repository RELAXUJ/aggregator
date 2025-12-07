"""Initial schema creation for RWA Liquidity Aggregator.

Revision ID: 001_initial
Revises: None
Create Date: 2024-12-07

Creates the core tables:
- tokens: RWA tokens being tracked
- venues: Trading venues/exchanges
- price_snapshots: Historical price data
- alerts: User alert subscriptions
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial database schema."""
    # Create tokens table
    op.create_table(
        "tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "category",
            sa.Enum("TBILL", "PRIVATE_CREDIT", "REAL_ESTATE", "EQUITY", name="tokencategory"),
            nullable=False,
        ),
        sa.Column("issuer", sa.String(length=100), nullable=False),
        sa.Column("chain", sa.String(length=50), nullable=True),
        sa.Column("contract_address", sa.String(length=66), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol"),
    )
    op.create_index("ix_tokens_symbol", "tokens", ["symbol"], unique=True)

    # Create venues table
    op.create_table(
        "venues",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column(
            "venue_type",
            sa.Enum("CEX", "DEX", "ISSUER", name="venuetype"),
            nullable=False,
        ),
        sa.Column(
            "api_type",
            sa.Enum("REST", "WEBSOCKET", "SUBGRAPH", name="apitype"),
            nullable=False,
        ),
        sa.Column("base_url", sa.String(length=255), nullable=False),
        sa.Column("trade_url_template", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_venues_name", "venues", ["name"], unique=True)

    # Create price_snapshots table
    op.create_table(
        "price_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("token_id", sa.Integer(), nullable=False),
        sa.Column("venue_id", sa.Integer(), nullable=False),
        sa.Column("bid", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("ask", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("mid", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("spread_pct", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("volume_24h", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["token_id"], ["tokens.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["venue_id"], ["venues.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_price_snapshots_token_id", "price_snapshots", ["token_id"])
    op.create_index("ix_price_snapshots_venue_id", "price_snapshots", ["venue_id"])
    op.create_index("ix_price_snapshots_fetched_at", "price_snapshots", ["fetched_at"])
    op.create_index(
        "ix_price_snapshots_token_venue_time",
        "price_snapshots",
        ["token_id", "venue_id", "fetched_at"],
    )

    # Create alerts table
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("token_id", sa.Integer(), nullable=False),
        sa.Column(
            "threshold_pct",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
            server_default="2.00",
        ),
        sa.Column(
            "alert_type",
            sa.Enum("SPREAD_BELOW", "DAILY_SUMMARY", name="alerttype"),
            nullable=False,
            server_default="SPREAD_BELOW",
        ),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "PAUSED", "DELETED", name="alertstatus"),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cooldown_hours", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["token_id"], ["tokens.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alerts_email", "alerts", ["email"])
    op.create_index("ix_alerts_token_id", "alerts", ["token_id"])
    op.create_index("ix_alerts_token_status", "alerts", ["token_id", "status"])


def downgrade() -> None:
    """Drop all tables and enums."""
    # Drop tables in reverse order of dependencies
    op.drop_table("alerts")
    op.drop_table("price_snapshots")
    op.drop_table("venues")
    op.drop_table("tokens")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS alertstatus")
    op.execute("DROP TYPE IF EXISTS alerttype")
    op.execute("DROP TYPE IF EXISTS apitype")
    op.execute("DROP TYPE IF EXISTS venuetype")
    op.execute("DROP TYPE IF EXISTS tokencategory")
