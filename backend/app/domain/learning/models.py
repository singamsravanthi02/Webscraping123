from sqlalchemy import Column, Integer, String, Boolean, Enum, ForeignKey, DateTime, Float, Text
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
