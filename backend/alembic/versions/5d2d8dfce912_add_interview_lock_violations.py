"""add interview lock violations

Revision ID: 5d2d8dfce912
Revises: 2f8f1f7d9c44
Create Date: 2026-07-21 18:05:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "5d2d8dfce912"
down_revision = "2f8f1f7d9c44"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "interviews",
        sa.Column(
            "lock_violations",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("interviews", "lock_violations")
