from sqlalchemy import Column, Integer, String, Boolean, Enum, ForeignKey, DateTime, Float, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
import enum
from app.db.base import Base, AuditMixin

class AssessmentType(str, enum.Enum):
    APTITUDE = "aptitude"
    TECHNICAL = "technical"
    CODING = "coding"
    COMPANY_PATTERN = "company_pattern"
    JNTUH_PATTERN = "jntuh_pattern"

class QuestionType(str, enum.Enum):
    MCQ = "mcq"
    CODING = "coding"
    SUBJECTIVE = "subjective"

class AttemptStatus(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    AUTO_SUBMITTED = "auto_submitted"
    ABANDONED = "abandoned"

class QuestionBank(Base, AuditMixin):
    __tablename__ = "question_bank"

    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String, index=True, nullable=False)
    subject = Column(String, index=True, nullable=False)
    difficulty = Column(Integer, default=5) # 1-10
    type = Column(Enum(QuestionType), default=QuestionType.MCQ, nullable=False)
    
    content = Column(Text, nullable=False)
    options = Column(JSONB, nullable=True) # Used for MCQ
    correct_answer = Column(String, nullable=True) # Key in options JSON or strict text
    
    # Coding specific
    starter_code = Column(Text, nullable=True)
    test_cases = Column(JSONB, nullable=True)
    
    points = Column(Float, default=1.0)
    
    # AI Engine Extensions
    interview_difficulty = Column(Integer, nullable=True) # 1-10 rating for interviews
    company_difficulty = Column(Integer, nullable=True) # 1-10 rating for specific companies
    bloom_level = Column(String, nullable=True) # e.g. 'Apply', 'Analyze'
    estimated_time = Column(Integer, nullable=True) # in seconds
    marks = Column(Float, nullable=True)
    placement_relevance = Column(Integer, nullable=True) # 1-10
    
    company_tags = Column(JSONB, default=lambda: [])
    hints = Column(JSONB, default=lambda: [])
    common_mistakes = Column(JSONB, default=lambda: [])
    source_citations = Column(JSONB, default=lambda: []) # Links back to Document IDs/Chunks
    detailed_explanation = Column(Text, nullable=True)


class Assessment(Base, AuditMixin):
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    type = Column(Enum(AssessmentType), nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    
    is_adaptive = Column(Boolean, default=False)
    is_proctored = Column(Boolean, default=True)
    
    negative_mark_weight = Column(Float, default=0.0) # e.g. 0.25 for 1/4th negative marking
    total_marks = Column(Float, nullable=False)

    # Relationships
    attempts = relationship("AssessmentAttempt", back_populates="assessment")

class AssessmentQuestionMap(Base):
    __tablename__ = "assessment_question_map"
    
    assessment_id = Column(Integer, ForeignKey("assessments.id", ondelete="CASCADE"), primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("question_bank.id", ondelete="CASCADE"), primary_key=True, index=True)


class AssessmentAttempt(Base, AuditMixin):
    __tablename__ = "assessment_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    
    status = Column(Enum(AttemptStatus), default=AttemptStatus.IN_PROGRESS, nullable=False)
    start_time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    
    score = Column(Float, nullable=True)
    
    # Proctoring Data
    tab_switch_count = Column(Integer, default=0)
    fullscreen_violations = Column(Integer, default=0)

    assessment = relationship("Assessment", back_populates="attempts")
    details = relationship("AttemptDetail", back_populates="attempt", cascade="all, delete")

class AttemptDetail(Base):
    __tablename__ = "attempt_details"
    
    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("assessment_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("question_bank.id", ondelete="CASCADE"), nullable=False, index=True)
    
    user_answer = Column(String, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    time_taken_seconds = Column(Integer, default=0)

    attempt = relationship("AssessmentAttempt", back_populates="details")
