from sqlalchemy import Column, Integer, String, Boolean, Enum, ForeignKey, DateTime, Date, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
import enum
from app.db.base import Base, AuditMixin

class JobSource(str, enum.Enum):
    LINKEDIN = "linkedin"
    NAUKRI = "naukri"
    INDEED = "indeed"
    WELLFOUND = "wellfound"
    INTERNSHALA = "internshala"
    COMPANY_PAGE = "company_page"
    MANUAL = "manual"
    ARBEITNOW = "arbeitnow"
    ADZUNA = "adzuna"
    REMOTEOK = "remoteok"
    GREENHOUSE = "greenhouse"
    LEVER = "lever"

class JobStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    DRAFT = "draft"

class Job(Base, AuditMixin):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    company = Column(String, index=True, nullable=False)
    location = Column(String, nullable=True)
    salary_range = Column(String, nullable=True)
    experience_required = Column(String, nullable=True)
    employment_type = Column(String, nullable=True) # Full-time, Internship, etc.
    posted_date = Column(DateTime, nullable=True)
    
    # Original Data
    raw_description = Column(Text, nullable=False)
    apply_link = Column(String, nullable=False)
    source = Column(Enum(JobSource), default=JobSource.MANUAL, nullable=False)
    external_id = Column(String, index=True, nullable=True) # Used for deduplication
    
    # AI Extracted Data
    extracted_skills = Column(JSONB, default=lambda: [])
    eligibility = Column(Text, nullable=True)
    deadline = Column(Date, nullable=True)
    ai_summary = Column(Text, nullable=True)
    match_score = Column(Integer, nullable=True)
    missing_skills = Column(JSONB, default=lambda: [])
    recommended_topics = Column(JSONB, default=lambda: [])
    
    status = Column(Enum(JobStatus), default=JobStatus.ACTIVE, nullable=False, index=True)
    
    # Relationships
    bookmarks = relationship("JobBookmark", back_populates="job", cascade="all, delete")


class JobBookmark(Base, AuditMixin):
    __tablename__ = "job_bookmarks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    notes = Column(Text, nullable=True)

    job = relationship("Job", back_populates="bookmarks")
