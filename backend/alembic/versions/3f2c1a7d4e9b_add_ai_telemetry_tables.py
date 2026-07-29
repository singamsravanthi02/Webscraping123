"""add ai telemetry tables

Revision ID: 3f2c1a7d4e9b
Revises: 9a8f7f0d1b2c
Create Date: 2026-07-21 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3f2c1a7d4e9b"
down_revision: Union[str, Sequence[str], None] = "9a8f7f0d1b2c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    existing_tables = set(sa.inspect(bind).get_table_names())

    if "ai_token_usage_logs" not in existing_tables:
        op.create_table(
            "ai_token_usage_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("model_name", sa.String(), nullable=False),
            sa.Column("prompt_tokens", sa.Integer(), nullable=True),
            sa.Column("completion_tokens", sa.Integer(), nullable=True),
            sa.Column("total_tokens", sa.Integer(), nullable=True),
            sa.Column("feature", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_ai_token_usage_logs_id"), "ai_token_usage_logs", ["id"], unique=False)
        op.create_index(op.f("ix_ai_token_usage_logs_user_id"), "ai_token_usage_logs", ["user_id"], unique=False)
        op.create_index(op.f("ix_ai_token_usage_logs_feature"), "ai_token_usage_logs", ["feature"], unique=False)
        op.create_index(op.f("ix_ai_token_usage_logs_created_at"), "ai_token_usage_logs", ["created_at"], unique=False)

    if "ai_recommendation_logs" not in existing_tables:
        op.create_table(
            "ai_recommendation_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("agent_name", sa.String(), nullable=False),
            sa.Column("action", sa.String(), nullable=False),
            sa.Column("confidence_score", sa.Float(), nullable=False),
            sa.Column("supporting_evidence", sa.JSON(), nullable=True),
            sa.Column("source_documents", sa.JSON(), nullable=True),
            sa.Column("reasoning_summary", sa.String(), nullable=False),
            sa.Column("suggested_next_actions", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_ai_recommendation_logs_id"), "ai_recommendation_logs", ["id"], unique=False)
        op.create_index(op.f("ix_ai_recommendation_logs_user_id"), "ai_recommendation_logs", ["user_id"], unique=False)
        op.create_index(op.f("ix_ai_recommendation_logs_agent_name"), "ai_recommendation_logs", ["agent_name"], unique=False)
        op.create_index(op.f("ix_ai_recommendation_logs_created_at"), "ai_recommendation_logs", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ai_recommendation_logs_created_at"), table_name="ai_recommendation_logs")
    op.drop_index(op.f("ix_ai_recommendation_logs_agent_name"), table_name="ai_recommendation_logs")
    op.drop_index(op.f("ix_ai_recommendation_logs_user_id"), table_name="ai_recommendation_logs")
    op.drop_index(op.f("ix_ai_recommendation_logs_id"), table_name="ai_recommendation_logs")
    op.drop_table("ai_recommendation_logs")

    op.drop_index(op.f("ix_ai_token_usage_logs_created_at"), table_name="ai_token_usage_logs")
    op.drop_index(op.f("ix_ai_token_usage_logs_feature"), table_name="ai_token_usage_logs")
    op.drop_index(op.f("ix_ai_token_usage_logs_user_id"), table_name="ai_token_usage_logs")
    op.drop_index(op.f("ix_ai_token_usage_logs_id"), table_name="ai_token_usage_logs")
    op.drop_table("ai_token_usage_logs")
