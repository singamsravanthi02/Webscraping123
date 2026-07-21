from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import date, datetime
from .models import JobSource, JobStatus

class JobBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str
    company: str
    location: Optional[str] = None
    salary_range: Optional[str] = None
    experience_required: Optional[str] = None
    employment_type: Optional[str] = None
    posted_date: Optional[datetime] = None
    apply_link: str
    source: JobSource = JobSource.MANUAL

class JobCreate(JobBase):
    raw_description: str
    external_id: Optional[str] = None

class JobResponse(JobBase):
    id: int
    extracted_skills: List[str]
    eligibility: Optional[str]
    deadline: Optional[date]
    ai_summary: Optional[str]
    status: JobStatus
    created_at: datetime
    
    # Virtual field for the AI match score
    match_score: Optional[int] = None
    missing_skills: Optional[List[str]] = None
    recommended_topics: Optional[List[str]] = None
class BookmarkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    notes: Optional[str]
    created_at: datetime
    job: JobResponse
