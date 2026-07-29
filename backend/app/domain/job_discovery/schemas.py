from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

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
    model_config = ConfigDict(from_attributes=True)

    id: int
    query_text: str
    filters: Dict[str, Any]
    results_count: int
    source: str
    used_queries: List[str]
    created_at: datetime

class StudentSearchProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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

class AIJobQueryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    query_text: str
    query_payload: Dict[str, Any]
    source: str
    results_count: int
    cache_key: Optional[str] = None
    created_at: datetime

class JobRankingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    job_id: Optional[int] = None
    query_id: Optional[int] = None
    rank_score: int
    reason: Optional[str] = None
    missing_skills: List[str] = Field(default_factory=list)
    suggested_improvements: List[str] = Field(default_factory=list)
    learning_recommendations: List[str] = Field(default_factory=list)
    expected_difficulty: Optional[str] = None
    ai_recommendation: Optional[str] = None
    rank_index: Optional[int] = None
    refreshed_at: Optional[datetime] = None

class AIJobDiscoveryResponse(BaseModel):
    profile: Optional[StudentSearchProfileResponse] = None
    queries: List[str] = Field(default_factory=list)
    rankings: List[JobRankingResponse] = Field(default_factory=list)
    jobs: List[JobResponse] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AIChatResponse(BaseModel):
    assistant_message: str
    queries: List[str] = Field(default_factory=list)
    jobs: List[JobResponse] = Field(default_factory=list)
    rankings: List[JobRankingResponse] = Field(default_factory=list)
    profile: Optional[StudentSearchProfileResponse] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class JobApplyRequest(BaseModel):
    job_id: int
    note: Optional[str] = None
    external_url: Optional[str] = None


class JobActionResponse(BaseModel):
    message: str
    job_id: int
    status: str
    details: Dict[str, Any] = Field(default_factory=dict)


class JobMonitorSourceStat(BaseModel):
    name: str
    count: int


class JobMonitorResponse(BaseModel):
    status: str
    scheduler_status: str
    last_crawl_at: Optional[datetime] = None
    jobs_fetched: int = 0
    duplicates_removed: int = 0
    latency_ms: float = 0.0
    failures: int = 0
    cached: bool = False
    active_jobs: int = 0
    recent_queries: List[str] = Field(default_factory=list)
    sources: List[JobMonitorSourceStat] = Field(default_factory=list)
    provider_status: List[Dict[str, Any]] = Field(default_factory=list)
