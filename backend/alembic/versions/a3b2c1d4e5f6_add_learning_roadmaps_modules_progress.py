"""add learning roadmaps modules progress

Revision ID: a3b2c1d4e5f6
Revises: 5d2d8dfce912
Create Date: 2026-07-21 19:30:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "a3b2c1d4e5f6"
down_revision = "5d2d8dfce912"
branch_labels = None
depends_on = None


module_status = postgresql.ENUM("available", "completed", name="modulestatus", create_type=False)


def upgrade() -> None:
    module_status.create(op.get_bind(), checkfirst=True)
    bind = op.get_bind()
    existing_tables = set(sa.inspect(bind).get_table_names())

    if "learning_roadmaps" not in existing_tables:
        op.create_table(
            "learning_roadmaps",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("title_key", sa.String(), nullable=False),
            sa.Column("subject", sa.String(), nullable=True),
            sa.Column("difficulty", sa.String(), nullable=True),
            sa.Column("estimated_hours", sa.Float(), server_default=sa.text("0"), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("created_by_ai", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column("source_chips", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
            sa.Column("retrieved_context", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("user_id", "title_key", name="uq_learning_roadmap_user_title"),
        )
        op.create_index("ix_learning_roadmaps_user_id", "learning_roadmaps", ["user_id"])
        op.create_index("ix_learning_roadmaps_title_key", "learning_roadmaps", ["title_key"])
        op.create_index("ix_learning_roadmaps_title", "learning_roadmaps", ["title"])

    if "learning_modules" not in existing_tables:
        op.create_table(
            "learning_modules",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("roadmap_id", sa.Integer(), sa.ForeignKey("learning_roadmaps.id", ondelete="CASCADE"), nullable=False),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("order", sa.Integer(), nullable=False),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("estimated_minutes", sa.Integer(), server_default=sa.text("0"), nullable=False),
            sa.Column("status", module_status, server_default=sa.text("'available'"), nullable=False),
            sa.Column("theory", sa.Text(), nullable=True),
            sa.Column("institutional_notes", sa.Text(), nullable=True),
            sa.Column("important_questions", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
            sa.Column("previous_year_questions", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
            sa.Column("examples", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
            sa.Column("diagrams", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
            sa.Column("practice_quiz", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
            sa.Column("flashcards", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
            sa.Column("revision_notes", sa.Text(), nullable=True),
            sa.Column("resources", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
            sa.Column("source_chips", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
            sa.Column("retrieved_chunks", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("roadmap_id", "order", name="uq_learning_module_roadmap_order"),
        )
        op.create_index("ix_learning_modules_roadmap_id", "learning_modules", ["roadmap_id"])
        op.create_index("ix_learning_modules_title", "learning_modules", ["title"])

    if "learning_progress" not in existing_tables:
        op.create_table(
            "learning_progress",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("module_id", sa.Integer(), sa.ForeignKey("learning_modules.id", ondelete="CASCADE"), nullable=False),
            sa.Column("completed", sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("time_spent", sa.Integer(), server_default=sa.text("0"), nullable=False),
            sa.Column("progress_percent", sa.Float(), server_default=sa.text("0"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("student_id", "module_id", name="uq_learning_progress_student_module"),
        )
        op.create_index("ix_learning_progress_student_id", "learning_progress", ["student_id"])
        op.create_index("ix_learning_progress_module_id", "learning_progress", ["module_id"])


def downgrade() -> None:
    op.drop_index("ix_learning_progress_module_id", table_name="learning_progress")
    op.drop_index("ix_learning_progress_student_id", table_name="learning_progress")
    op.drop_table("learning_progress")

    op.drop_index("ix_learning_modules_title", table_name="learning_modules")
    op.drop_index("ix_learning_modules_roadmap_id", table_name="learning_modules")
    op.drop_table("learning_modules")

    op.drop_index("ix_learning_roadmaps_title", table_name="learning_roadmaps")
    op.drop_index("ix_learning_roadmaps_title_key", table_name="learning_roadmaps")
    op.drop_index("ix_learning_roadmaps_user_id", table_name="learning_roadmaps")
    op.drop_table("learning_roadmaps")

    module_status.drop(op.get_bind(), checkfirst=True)
