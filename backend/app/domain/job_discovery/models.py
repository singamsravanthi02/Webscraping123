from __future__ import annotations

import enum

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base, AuditMixin


class JobSearchSource(str, enum.Enum):
    GEMINI = "gemini"
    SERPAPI = "serpapi"
    SERPER = "serper"
    GOOGLE_CSE = "google_cse"
    LOCAL_CACHE = "local_cache"
    MANUAL = "manual"


class RecommendationAction(str, enum.Enum):
    BOOKMARKED = "bookmarked"
    APPLIED = "applied"
    VIEWED = "viewed"
    REJECTED = "rejected"
    IGNORED = "ignored"
    REFRESHED = "refreshed"


class StudentSearchProfile(Base, AuditMixin):
    __tablename__ = "student_search_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    preferred_roles = Column(JSONB, default=lambda: [])
    preferred_locations = Column(JSONB, default=lambda: [])
    keywords = Column(JSONB, default=lambda: [])
    resume_keywords = Column(JSONB, default=lambda: [])
    interview_scores = Column(JSONB, default=lambda: {})
    learning_progress = Column(JSONB, default=lambda: {})
    search_context = Column(JSONB, default=lambda: {})
    cgpa = Column(Float, nullable=True)
    career_goal = Column(String, nullable=True)
    last_resume_url = Column(String, nullable=True)
    profile_hash = Column(String, nullable=True, index=True)
    last_generated_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User")
    queries = relationship("AIJobQuery", back_populates="profile", cascade="all, delete-orphan")


class AIJobQuery(Base, AuditMixin):
    __tablename__ = "ai_job_queries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    profile_id = Column(Integer, ForeignKey("student_search_profiles.id", ondelete="CASCADE"), nullable=True, index=True)
    query_text = Column(String, nullable=False, index=True)
    query_payload = Column(JSONB, default=lambda: {})
    source = Column(String, nullable=False, default=JobSearchSource.GEMINI.value)
    results_count = Column(Integer, default=0)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    cache_key = Column(String, nullable=True, index=True)

    profile = relationship("StudentSearchProfile", back_populates="queries")
    rankings = relationship("JobRanking", back_populates="query", cascade="all, delete-orphan")


class JobRanking(Base, AuditMixin):
    __tablename__ = "job_rankings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    query_id = Column(Integer, ForeignKey("ai_job_queries.id", ondelete="SET NULL"), nullable=True, index=True)
    rank_score = Column(Integer, nullable=False, index=True)
    reason = Column(Text, nullable=True)
    missing_skills = Column(JSONB, default=lambda: [])
    suggested_improvements = Column(JSONB, default=lambda: [])
    learning_recommendations = Column(JSONB, default=lambda: [])
    expected_difficulty = Column(String, nullable=True)
    ai_recommendation = Column(String, nullable=True)
    rank_index = Column(Integer, nullable=True)
    refreshed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    query = relationship("AIJobQuery", back_populates="rankings")
    job = relationship("Job")


class RecommendedJob(Base, AuditMixin):
    __tablename__ = "recommended_jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    ranking_id = Column(Integer, ForeignKey("job_rankings.id", ondelete="SET NULL"), nullable=True, index=True)
    rank_score = Column(Integer, nullable=False, index=True)
    reason = Column(Text, nullable=True)
    ai_recommendation = Column(String, nullable=True)
    is_current = Column(Boolean, default=True, index=True)
    source_query = Column(String, nullable=True)
    refreshed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class JobRecommendationEvent(Base, AuditMixin):
    __tablename__ = "job_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    ranking_id = Column(Integer, ForeignKey("job_rankings.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String, nullable=False)
    payload = Column(JSONB, default=lambda: {})
    note = Column(Text, nullable=True)


class JobSearchHistory(Base, AuditMixin):
    __tablename__ = "job_search_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    query_text = Column(String, nullable=False)
    filters = Column(JSONB, default=lambda: {})
    results_count = Column(Integer, default=0)
    source = Column(String, nullable=False, default=JobSearchSource.MANUAL.value)
    used_queries = Column(JSONB, default=lambda: [])
