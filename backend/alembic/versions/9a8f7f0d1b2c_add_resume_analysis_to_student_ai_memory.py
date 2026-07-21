"""add resume analysis to student ai memory

Revision ID: 9a8f7f0d1b2c
Revises: 4a9f7c7f3d7b
Create Date: 2026-07-20 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "9a8f7f0d1b2c"
down_revision = "4a9f7c7f3d7b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("student_ai_memory", sa.Column("resume_analysis", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("student_ai_memory", "resume_analysis")
