from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base

class StudentAIMemory(Base):
    """
    Persists long-term AI context for a student across all agents.
    """
    __tablename__ = "student_ai_memory"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    
    # JSON blobs for flexible schema
    learning_history = Column(JSON, default=list)
    test_performance = Column(JSON, default=dict)
    interview_feedback = Column(JSON, default=list)
    resume_analysis = Column(JSON, default=dict)
    preferred_roles = Column(JSON, default=list)
    career_goals = Column(String, nullable=True)
    weak_topics = Column(JSON, default=list)
    strong_topics = Column(JSON, default=list)
    
    # Composite Placement Readiness Score (0-100)
    placement_readiness_score = Column(Float, nullable=True)

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class AIRecommendationLog(Base):
    """
    Provides Explainable AI logging for all agent recommendations.
    """
    __tablename__ = "ai_recommendation_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    agent_name = Column(String, nullable=False)
    
    action = Column(String, nullable=False)
    confidence_score = Column(Float, nullable=False) # 0.0 to 1.0
    supporting_evidence = Column(JSON, default=list)
    source_documents = Column(JSON, default=list)
    reasoning_summary = Column(String, nullable=False)
    suggested_next_actions = Column(JSON, default=list)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
