from sqlalchemy import Column, Integer, String, Boolean, Enum, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
import enum
from app.db.base import Base, AuditMixin
from app.domain.users.models import User

class NotificationChannel(str, enum.Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"

class NotificationStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SENT = "sent"
    FAILED = "failed"

class NotificationTemplate(Base, AuditMixin):
    __tablename__ = "notification_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False) # e.g. "job_alert", "interview_reminder"
    channel = Column(Enum(NotificationChannel), nullable=False)
    
    subject_template = Column(String, nullable=True) # Used for Email/Push
    body_template = Column(Text, nullable=False)
    
    is_active = Column(Boolean, default=True)

class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    template_name = Column(String, nullable=False)
    channel = Column(Enum(NotificationChannel), nullable=False)
    
    # Store the actual sent content or the context data
    context_data = Column(JSONB, nullable=True)
    
    status = Column(Enum(NotificationStatus), default=NotificationStatus.PENDING, nullable=False)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship(User)
