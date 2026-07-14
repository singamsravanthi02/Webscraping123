"""ai job discovery tables

Revision ID: 4a9f7c7f3d7b
Revises: e6be74216d46
Create Date: 2026-07-13 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "4a9f7c7f3d7b"
down_revision = "e6be74216d46"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "student_search_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("preferred_roles", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("preferred_locations", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("resume_keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("interview_scores", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("learning_progress", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("search_context", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("cgpa", sa.Float(), nullable=True),
        sa.Column("career_goal", sa.String(), nullable=True),
        sa.Column("last_resume_url", sa.String(), nullable=True),
        sa.Column("profile_hash", sa.String(), nullable=True),
        sa.Column("last_generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_student_search_profiles_user_id", "student_search_profiles", ["user_id"], unique=True)
    op.create_index("ix_student_search_profiles_profile_hash", "student_search_profiles", ["profile_hash"])

    op.create_table(
        "ai_job_queries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("profile_id", sa.Integer(), sa.ForeignKey("student_search_profiles.id", ondelete="CASCADE"), nullable=True),
        sa.Column("query_text", sa.String(), nullable=False),
        sa.Column("query_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("results_count", sa.Integer(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cache_key", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_ai_job_queries_user_id", "ai_job_queries", ["user_id"])
    op.create_index("ix_ai_job_queries_profile_id", "ai_job_queries", ["profile_id"])
    op.create_index("ix_ai_job_queries_query_text", "ai_job_queries", ["query_text"])
    op.create_index("ix_ai_job_queries_cache_key", "ai_job_queries", ["cache_key"])

    op.create_table(
        "job_rankings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("query_id", sa.Integer(), sa.ForeignKey("ai_job_queries.id", ondelete="SET NULL"), nullable=True),
        sa.Column("rank_score", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("missing_skills", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("suggested_improvements", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("learning_recommendations", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("expected_difficulty", sa.String(), nullable=True),
        sa.Column("ai_recommendation", sa.String(), nullable=True),
        sa.Column("rank_index", sa.Integer(), nullable=True),
        sa.Column("refreshed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_job_rankings_user_id", "job_rankings", ["user_id"])
    op.create_index("ix_job_rankings_job_id", "job_rankings", ["job_id"])
    op.create_index("ix_job_rankings_query_id", "job_rankings", ["query_id"])
    op.create_index("ix_job_rankings_rank_score", "job_rankings", ["rank_score"])

    op.create_table(
        "recommended_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ranking_id", sa.Integer(), sa.ForeignKey("job_rankings.id", ondelete="SET NULL"), nullable=True),
        sa.Column("rank_score", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("ai_recommendation", sa.String(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("source_query", sa.String(), nullable=True),
        sa.Column("refreshed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_recommended_jobs_user_id", "recommended_jobs", ["user_id"])
    op.create_index("ix_recommended_jobs_job_id", "recommended_jobs", ["job_id"])
    op.create_index("ix_recommended_jobs_is_current", "recommended_jobs", ["is_current"])
    op.create_index("ix_recommended_jobs_rank_score", "recommended_jobs", ["rank_score"])

    op.create_table(
        "job_recommendations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ranking_id", sa.Integer(), sa.ForeignKey("job_rankings.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_job_recommendations_user_id", "job_recommendations", ["user_id"])
    op.create_index("ix_job_recommendations_job_id", "job_recommendations", ["job_id"])
    op.create_index("ix_job_recommendations_action", "job_recommendations", ["action"])

    op.create_table(
        "job_search_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("query_text", sa.String(), nullable=False),
        sa.Column("filters", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("results_count", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("used_queries", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_job_search_history_user_id", "job_search_history", ["user_id"])
    op.create_index("ix_job_search_history_query_text", "job_search_history", ["query_text"])


def downgrade() -> None:
    op.drop_index("ix_job_search_history_query_text", table_name="job_search_history")
    op.drop_index("ix_job_search_history_user_id", table_name="job_search_history")
    op.drop_table("job_search_history")

    op.drop_index("ix_job_recommendations_action", table_name="job_recommendations")
    op.drop_index("ix_job_recommendations_job_id", table_name="job_recommendations")
    op.drop_index("ix_job_recommendations_user_id", table_name="job_recommendations")
    op.drop_table("job_recommendations")

    op.drop_index("ix_recommended_jobs_rank_score", table_name="recommended_jobs")
    op.drop_index("ix_recommended_jobs_is_current", table_name="recommended_jobs")
    op.drop_index("ix_recommended_jobs_job_id", table_name="recommended_jobs")
    op.drop_index("ix_recommended_jobs_user_id", table_name="recommended_jobs")
    op.drop_table("recommended_jobs")

    op.drop_index("ix_job_rankings_rank_score", table_name="job_rankings")
    op.drop_index("ix_job_rankings_query_id", table_name="job_rankings")
    op.drop_index("ix_job_rankings_job_id", table_name="job_rankings")
    op.drop_index("ix_job_rankings_user_id", table_name="job_rankings")
    op.drop_table("job_rankings")

    op.drop_index("ix_ai_job_queries_cache_key", table_name="ai_job_queries")
    op.drop_index("ix_ai_job_queries_query_text", table_name="ai_job_queries")
    op.drop_index("ix_ai_job_queries_profile_id", table_name="ai_job_queries")
    op.drop_index("ix_ai_job_queries_user_id", table_name="ai_job_queries")
    op.drop_table("ai_job_queries")

    op.drop_index("ix_student_search_profiles_profile_hash", table_name="student_search_profiles")
    op.drop_index("ix_student_search_profiles_user_id", table_name="student_search_profiles")
    op.drop_table("student_search_profiles")
