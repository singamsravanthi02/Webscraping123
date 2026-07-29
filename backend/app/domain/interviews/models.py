from sqlalchemy import Column, Integer, String, Boolean, Enum, ForeignKey, DateTime, Float, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
import enum
from app.db.base import Base, AuditMixin

class InterviewType(str, enum.Enum):
    HR = "hr"
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    CODING = "coding"
    RESUME = "resume"
    SYSTEM_DESIGN = "system_design"
    MOCK_COMPANY = "mock_company"

class InterviewStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"

class MessageRole(str, enum.Enum):
    SYSTEM = "system"
    USER = "user"
    AI = "ai"

class InterviewSession(Base, AuditMixin):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    title = Column(String, index=True, nullable=False)
    type = Column(Enum(InterviewType), nullable=False)
    status = Column(Enum(InterviewStatus), default=InterviewStatus.PENDING, nullable=False)
    
    resume_text = Column(Text, nullable=True) # Optional context for resume based interview
    job_description = Column(Text, nullable=True)
    lock_violations = Column(JSONB, default=lambda: [], nullable=False)
    
    start_time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    messages = relationship("InterviewMessage", back_populates="interview", cascade="all, delete-orphan", order_by="InterviewMessage.created_at")
    result = relationship("InterviewResult", back_populates="interview", uselist=False, cascade="all, delete-orphan")


class InterviewMessage(Base):
    __tablename__ = "interview_messages"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False, index=True)
    
    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    interview = relationship("InterviewSession", back_populates="messages")


class InterviewResult(Base):
    __tablename__ = "interview_results"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    confidence_score = Column(Float, nullable=True)
    communication_score = Column(Float, nullable=True)
    technical_score = Column(Float, nullable=True)
    problem_solving_score = Column(Float, nullable=True)
    overall_grade = Column(Float, nullable=True)
    
    feedback_summary = Column(Text, nullable=True)
    suggestions = Column(JSONB, nullable=True) # Array of suggestions
    strengths = Column(JSONB, nullable=True) # Array of strengths
    weaknesses = Column(JSONB, nullable=True) # Array of weaknesses
    recommended_topics = Column(JSONB, nullable=True) # Array of topics
    learning_plan = Column(Text, nullable=True)
    placement_readiness_contribution = Column(Float, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    interview = relationship("InterviewSession", back_populates="result")
