from datetime import datetime, timezone

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

    @property
    def provider(self) -> str:
        return getattr(self.source, "value", self.source or JobSource.MANUAL.value)

    @property
    def provider_url(self) -> str | None:
        return self.apply_link

    @property
    def company_url(self) -> str | None:
        return self.apply_link if self.source == JobSource.COMPANY_PAGE else None

    @property
    def summary(self) -> str | None:
        return self.ai_summary

    @property
    def ai_match_score(self) -> int | None:
        return self.match_score

    @property
    def remote(self) -> bool:
        text = " ".join(part for part in [self.location or "", self.employment_type or ""] if part).lower()
        return any(token in text for token in ["remote", "work from home", "wfh"])

    @property
    def country(self) -> str | None:
        text = (self.location or "").lower()
        if any(token in text for token in ["india", "hyderabad", "bengaluru", "bangalore", "pune"]):
            return "India"
        if any(token in text for token in ["united states", "usa", "us"]):
            return "United States"
        if "uk" in text or "london" in text:
            return "United Kingdom"
        return None

    @property
    def freshness_score(self) -> int:
        if not self.posted_date:
            return 0
        posted = self.posted_date
        if posted.tzinfo is None:
            posted = posted.replace(tzinfo=timezone.utc)
        age_days = max((datetime.now(timezone.utc) - posted).days, 0)
        return max(0, 100 - min(age_days * 10, 100))

    @property
    def fingerprint(self) -> str:
        from app.domain.jobs.deduplication import job_fingerprint

        return job_fingerprint(
            {
                "title": self.title,
                "company": self.company,
                "location": self.location,
                "apply_url": self.apply_link,
                "description": self.raw_description,
            }
        )


class JobBookmark(Base, AuditMixin):
    __tablename__ = "job_bookmarks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    notes = Column(Text, nullable=True)

    job = relationship("Job", back_populates="bookmarks")
