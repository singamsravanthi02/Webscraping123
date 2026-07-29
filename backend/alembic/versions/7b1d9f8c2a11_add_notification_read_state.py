"""add notification read state

Revision ID: 7b1d9f8c2a11
Revises: 3f2c1a7d4e9b
Create Date: 2026-07-21 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7b1d9f8c2a11"
down_revision: Union[str, Sequence[str], None] = "3f2c1a7d4e9b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "notification_logs",
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("notification_logs", "is_read")
