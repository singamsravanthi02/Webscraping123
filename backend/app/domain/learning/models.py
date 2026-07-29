from sqlalchemy import Column, Integer, String, Boolean, Enum, ForeignKey, DateTime, Float, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
import enum
from app.db.base import Base, AuditMixin

class MessageRole(str, enum.Enum):
    SYSTEM = "system"
    USER = "user"
    AI = "ai"

class ResourceType(str, enum.Enum):
    PDF = "pdf"
    PPT = "ppt"
    TEXT = "text"
    WEBSITE = "website"


class ModuleStatus(str, enum.Enum):
    AVAILABLE = "available"
    COMPLETED = "completed"


class LearningRoadmap(Base, AuditMixin):
    __tablename__ = "learning_roadmaps"
    __table_args__ = (
        UniqueConstraint("user_id", "title_key", name="uq_learning_roadmap_user_title"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String, index=True, nullable=False)
    title_key = Column(String, index=True, nullable=False)
    subject = Column(String, index=True, nullable=True)
    difficulty = Column(String, nullable=True)
    estimated_hours = Column(Float, default=0)
    description = Column(Text, nullable=True)
    created_by_ai = Column(Boolean, default=True, nullable=False)
    source_chips = Column(JSONB, default=lambda: [])
    retrieved_context = Column(JSONB, default=lambda: [])

    modules = relationship(
        "LearningModule",
        back_populates="roadmap",
        cascade="all, delete-orphan",
        order_by="LearningModule.order",
    )


class LearningModule(Base, AuditMixin):
    __tablename__ = "learning_modules"

    id = Column(Integer, primary_key=True, index=True)
    roadmap_id = Column(Integer, ForeignKey("learning_roadmaps.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String, index=True, nullable=False)
    order = Column(Integer, nullable=False)
    summary = Column(Text, nullable=True)
    estimated_minutes = Column(Integer, default=0)
    status = Column(
        Enum(ModuleStatus, values_callable=lambda enum_cls: [item.value for item in enum_cls]),
        default=ModuleStatus.AVAILABLE.value,
        nullable=False,
    )
    theory = Column(Text, nullable=True)
    institutional_notes = Column(Text, nullable=True)
    important_questions = Column(JSONB, default=lambda: [])
    previous_year_questions = Column(JSONB, default=lambda: [])
    examples = Column(JSONB, default=lambda: [])
    diagrams = Column(JSONB, default=lambda: [])
    practice_quiz = Column(JSONB, default=lambda: [])
    flashcards = Column(JSONB, default=lambda: [])
    revision_notes = Column(Text, nullable=True)
    resources = Column(JSONB, default=lambda: [])
    source_chips = Column(JSONB, default=lambda: [])
    retrieved_chunks = Column(JSONB, default=lambda: [])

    roadmap = relationship("LearningRoadmap", back_populates="modules")
    progress_records = relationship("LearningProgress", back_populates="module", cascade="all, delete-orphan")


class LearningProgress(Base, AuditMixin):
    __tablename__ = "learning_progress"
    __table_args__ = (
        UniqueConstraint("student_id", "module_id", name="uq_learning_progress_student_module"),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    module_id = Column(Integer, ForeignKey("learning_modules.id", ondelete="CASCADE"), nullable=False, index=True)
    completed = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    time_spent = Column(Integer, default=0, nullable=False)
    progress_percent = Column(Float, default=0.0, nullable=False)

    module = relationship("LearningModule", back_populates="progress_records")

class LearningSession(Base, AuditMixin):
    __tablename__ = "learning_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    title = Column(String, index=True, nullable=False)
    subject = Column(String, index=True, nullable=True) # e.g. "Data Structures"
    
    is_active = Column(Boolean, default=True)

    # Relationships
    messages = relationship("LearningMessage", back_populates="session", cascade="all, delete-orphan", order_by="LearningMessage.created_at")

class LearningMessage(Base):
    __tablename__ = "learning_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("learning_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    
    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    
    # Store citations for AI messages (e.g. [{"source": "JNTUH_Syllabus.pdf", "page": 4}])
    citations = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    session = relationship("LearningSession", back_populates="messages")

class LearningResource(Base, AuditMixin):
    __tablename__ = "learning_resources"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    type = Column(Enum(ResourceType), nullable=False)
    
    # Who uploaded it. If null, it's a global resource.
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # S3 path or local path if we store actual files, otherwise just metadata
    file_path = Column(String, nullable=True) 
    
    # Qdrant collection name if specific, or indicates it's in the main collection
    is_processed = Column(Boolean, default=False)
