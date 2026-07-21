from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.domain.jobs.schemas import JobResponse


class SearchRequest(BaseModel):
    query: str
    location: Optional[str] = None
    role: Optional[str] = None
    limit: int = 20
    refresh: bool = False


class AIChatRequest(BaseModel):
    message: str = Field(min_length=1)
    location: Optional[str] = None
    limit: int = 12


class RefreshResponse(BaseModel):
    message: str
    profile_id: Optional[int] = None
    queries_generated: int = 0
    jobs_ranked: int = 0
    recommendations: List[JobResponse] = []


class JobSearchHistoryResponse(BaseModel):
    id: int
    query_text: str
    filters: Dict[str, Any]
    results_count: int
    source: str
    used_queries: List[str]
    created_at: datetime

    class Config:
        from_attributes = True


class StudentSearchProfileResponse(BaseModel):
    id: int
    user_id: int
    preferred_roles: List[str]
    preferred_locations: List[str]
    keywords: List[str]
    resume_keywords: List[str]
    interview_scores: Dict[str, Any]
    learning_progress: Dict[str, Any]
    search_context: Dict[str, Any]
    cgpa: Optional[float] = None
    career_goal: Optional[str] = None
    last_resume_url: Optional[str] = None
    profile_hash: Optional[str] = None
    last_generated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AIJobQueryResponse(BaseModel):
    id: int
    query_text: str
    query_payload: Dict[str, Any]
    source: str
    results_count: int
    cache_key: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class JobRankingResponse(BaseModel):
    id: Optional[int] = None
    job_id: Optional[int] = None
    query_id: Optional[int] = None
    rank_score: int
    reason: Optional[str] = None
    missing_skills: List[str] = []
    suggested_improvements: List[str] = []
    learning_recommendations: List[str] = []
    expected_difficulty: Optional[str] = None
    ai_recommendation: Optional[str] = None
    rank_index: Optional[int] = None
    refreshed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AIJobDiscoveryResponse(BaseModel):
    profile: Optional[StudentSearchProfileResponse] = None
    queries: List[str] = []
    rankings: List[JobRankingResponse] = []
    jobs: List[JobResponse] = []
    metadata: Dict[str, Any] = {}


class AIChatResponse(BaseModel):
    assistant_message: str
    queries: List[str] = []
    jobs: List[JobResponse] = []
    rankings: List[JobRankingResponse] = []
    profile: Optional[StudentSearchProfileResponse] = None
    metadata: Dict[str, Any] = {}


class JobApplyRequest(BaseModel):
    job_id: int
    note: Optional[str] = None
    external_url: Optional[str] = None


class JobActionResponse(BaseModel):
    message: str
    job_id: int
    status: str
    details: Dict[str, Any] = {}
