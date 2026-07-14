from sqlalchemy import Column, Integer, String, Boolean, Enum, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.base import Base, AuditMixin
from sqlalchemy.dialects.postgresql import JSONB

class UserRole(str, enum.Enum):
    STUDENT = "student"
    FACULTY = "faculty"
    PLACEMENT_OFFICER = "placement_officer"
    ADMIN = "admin"

class User(Base, AuditMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, unique=True, index=True, nullable=True)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.STUDENT, nullable=False)
    
    # Academic & Professional Details
    college = Column(String, nullable=True)
    department = Column(String, nullable=True)
    branch = Column(String, nullable=True)
    semester = Column(Integer, nullable=True)
    cgpa = Column(Float, nullable=True)
    skills = Column(JSONB, default=lambda: [])
    career_goal = Column(String, nullable=True)
    
    # Uploads & Links
    resume_url = Column(String, nullable=True)
    profile_picture = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    github_url = Column(String, nullable=True)
    portfolio_url = Column(String, nullable=True)
    
    # Status
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    is_locked = Column(Boolean, default=False)
    profile_completed = Column(Boolean, default=False)
    
    # Login Tracking
    failed_login_attempts = Column(Integer, default=0)
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Legacy Registration details (kept for backward compatibility if needed, but the prompt overrides some)
    roll_number = Column(String, unique=True, index=True, nullable=True)
    employee_id = Column(String, unique=True, index=True, nullable=True)
    terms_accepted = Column(Boolean, default=False, nullable=False)

    # Profile Data (JSONB for future flexibility)
    profile_data = Column(JSONB, default=lambda: {})

    sessions = relationship("UserSession", back_populates="user", cascade="all, delete")
    tokens = relationship("VerificationToken", back_populates="user", cascade="all, delete")
    otps = relationship("EmailOTP", back_populates="user", cascade="all, delete")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete")


class UserSession(Base, AuditMixin):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    refresh_token = Column(String, unique=True, index=True, nullable=False)
    device_info = Column(String, nullable=True)
    browser = Column(String, nullable=True)
    os = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, default=False)

    user = relationship("User", back_populates="sessions")


class TokenType(str, enum.Enum):
    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"
    EMAIL_CHANGE = "email_change"
    ACCOUNT_RECOVERY = "account_recovery"


class VerificationToken(Base, AuditMixin):
    __tablename__ = "verification_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    token_type = Column(Enum(TokenType), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_used = Column(Boolean, default=False)

    user = relationship("User", back_populates="tokens")


class EmailOTP(Base, AuditMixin):
    __tablename__ = "email_otps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    otp_hash = Column(String, nullable=False)
    purpose = Column(Enum(TokenType), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    attempts = Column(Integer, default=0)
    is_used = Column(Boolean, default=False)

    user = relationship("User", back_populates="otps")


class AuditLog(Base, AuditMixin):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String, nullable=False)
    status = Column(String, nullable=False)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    details = Column(String, nullable=True)

    user = relationship("User", back_populates="audit_logs")
