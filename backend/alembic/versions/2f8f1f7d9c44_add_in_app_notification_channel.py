"""add in-app notification channel

Revision ID: 2f8f1f7d9c44
Revises: 7b1d9f8c2a11
Create Date: 2026-07-21 17:45:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "2f8f1f7d9c44"
down_revision = "7b1d9f8c2a11"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE notificationchannel ADD VALUE IF NOT EXISTS 'IN_APP'")


def downgrade() -> None:
    return None
