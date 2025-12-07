"""Add market_type column to tokens table.

Revision ID: 002_add_market_type
Revises: 001_initial
Create Date: 2024-12-07

Adds market_type enum to distinguish between tradable tokens (with real
spot pairs) and NAV-only tokens (informational only, no active trading).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "002_add_market_type"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add market_type column to tokens table."""
    # Create the markettype enum
    markettype_enum = sa.Enum("TRADABLE", "NAV_ONLY", name="markettype")
    markettype_enum.create(op.get_bind(), checkfirst=True)

    # Add the column with a default value
    op.add_column(
        "tokens",
        sa.Column(
            "market_type",
            sa.Enum("TRADABLE", "NAV_ONLY", name="markettype"),
            nullable=False,
            server_default="TRADABLE",
        ),
    )


def downgrade() -> None:
    """Remove market_type column from tokens table."""
    op.drop_column("tokens", "market_type")
    op.execute("DROP TYPE IF EXISTS markettype")
