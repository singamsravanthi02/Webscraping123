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
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("student_ai_memory"):
        op.create_table(
            "student_ai_memory",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("learning_history", sa.JSON(), nullable=True),
            sa.Column("test_performance", sa.JSON(), nullable=True),
            sa.Column("interview_feedback", sa.JSON(), nullable=True),
            sa.Column("resume_analysis", sa.JSON(), nullable=True),
            sa.Column("preferred_roles", sa.JSON(), nullable=True),
            sa.Column("career_goals", sa.String(), nullable=True),
            sa.Column("weak_topics", sa.JSON(), nullable=True),
            sa.Column("strong_topics", sa.JSON(), nullable=True),
            sa.Column("placement_readiness_score", sa.Float(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_student_ai_memory_id"), "student_ai_memory", ["id"], unique=False)
        op.create_index(op.f("ix_student_ai_memory_user_id"), "student_ai_memory", ["user_id"], unique=True)
        return

    existing_columns = {column["name"] for column in inspector.get_columns("student_ai_memory")}
    if "resume_analysis" not in existing_columns:
        op.add_column("student_ai_memory", sa.Column("resume_analysis", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("student_ai_memory", "resume_analysis")
