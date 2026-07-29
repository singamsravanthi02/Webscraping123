from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Body, Depends
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.config import settings
from app.domain.jobs.schemas import JobResponse, BookmarkResponse
from app.services.job_service import JobService
from app.api.dependencies.auth import get_current_active_user
from app.domain.users.models import User

from app.services.cache_service import cache
from app.domain.job_discovery.schemas import (
    AIChatRequest,
    AIChatResponse,
    AIJobDiscoveryResponse,
    JobActionResponse,
    JobApplyRequest,
    JobMonitorResponse,
    JobMonitorSourceStat,
    JobSearchHistoryResponse,
    RefreshResponse,
    SearchRequest,
)
from app.domain.job_discovery.models import JobRecommendationEvent, JobSearchHistory
from app.domain.job_discovery.services import AIJobDiscoveryService
from app.domain.jobs.models import Job, JobSource, JobStatus

router = APIRouter()

@router.get("", response_model=List[JobResponse])
def get_jobs(
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    location: Optional[str] = None,
    refresh: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    discovery = AIJobDiscoveryService(db)
    if search:
        result = discovery.search(current_user, query=search, location=location, limit=limit, refresh=refresh)
        return result["jobs"]
    cache_key = f"jobs:recommended:{current_user.id}:{skip}:{limit}:{refresh}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    jobs = discovery.recommended_jobs(current_user, limit=limit)
    cache.set(cache_key, jsonable_encoder(jobs), expiration=settings.JOB_CACHE_TTL_MINUTES * 60)
    return jobs

@router.get("/recommended", response_model=List[JobResponse])
def get_recommended_jobs(limit: int = 100, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    discovery = AIJobDiscoveryService(db)
    return discovery.recommended_jobs(current_user, limit=limit)

@router.post("/search", response_model=AIJobDiscoveryResponse)
def search_jobs(
    request: SearchRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    discovery = AIJobDiscoveryService(db)
    result = discovery.search(
        current_user,
        query=request.query,
        location=request.location,
        limit=request.limit,
        refresh=request.refresh,
    )
    return result

@router.post("/refresh", response_model=RefreshResponse)
def refresh_jobs(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    discovery = AIJobDiscoveryService(db)
    payload = discovery.refresh_user(current_user)
    return RefreshResponse(
        message="AI job recommendations refreshed",
        profile_id=payload["profile"].id if payload.get("profile") else None,
        queries_generated=len(payload.get("queries") or []),
        jobs_ranked=len(payload.get("jobs") or []),
        recommendations=payload.get("jobs") or [],
    )

@router.post("/chat", response_model=AIChatResponse)
def chat_jobs(
    request: AIChatRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    discovery = AIJobDiscoveryService(db)
    return discovery.chat(current_user, message=request.message, location=request.location, limit=request.limit)

@router.get("/trending")
def trending_jobs(limit: int = 10, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    discovery = AIJobDiscoveryService(db)
    return jsonable_encoder(discovery.engine.get_trending(limit=limit))


@router.get("/monitor", response_model=JobMonitorResponse)
def job_monitor(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    latest_history = db.query(JobSearchHistory).order_by(JobSearchHistory.created_at.desc()).first()
    latest_event = db.query(JobRecommendationEvent).order_by(JobRecommendationEvent.created_at.desc()).first()

    monitor = {}
    last_crawl_at = None
    if latest_history and isinstance(latest_history.filters, dict):
        monitor = latest_history.filters.get("job_monitor") or {}
        last_crawl_at = latest_history.created_at
    if (not monitor or not monitor.get("jobs_fetched")) and latest_event and isinstance(latest_event.payload, dict):
        event_monitor = latest_event.payload.get("job_monitor") or {}
        if event_monitor:
            monitor = event_monitor
            last_crawl_at = latest_event.created_at

    provider_counts = monitor.get("provider_counts") if isinstance(monitor, dict) else {}
    sources = [
        JobMonitorSourceStat(name=name, count=int(count or 0))
        for name, count in sorted((provider_counts or {}).items(), key=lambda item: item[1], reverse=True)
    ]
    active_jobs = (
        db.query(Job)
        .filter(Job.status == JobStatus.ACTIVE, Job.source != JobSource.MANUAL)
        .count()
    )
    failures = int(monitor.get("failures", 0) or 0)
    jobs_fetched = int(monitor.get("jobs_fetched", 0) or 0)
    status = "healthy" if jobs_fetched > 0 and failures == 0 and last_crawl_at else "degraded"
    if last_crawl_at and (datetime.now(timezone.utc) - last_crawl_at).total_seconds() > 86400:
        status = "stale"

    return JobMonitorResponse(
        status=status,
        scheduler_status="enabled" if settings.JOB_ENABLE_BACKGROUND_REFRESH else "disabled",
        last_crawl_at=last_crawl_at,
        jobs_fetched=jobs_fetched,
        duplicates_removed=int(monitor.get("duplicates_removed", 0) or 0),
        latency_ms=float(monitor.get("latency_ms", 0.0) or 0.0),
        failures=failures,
        cached=bool(monitor.get("cached", False)),
        active_jobs=active_jobs,
        recent_queries=list(monitor.get("queries") or []),
        sources=sources,
        provider_status=list(monitor.get("provider_status") or []),
    )

@router.get("/history", response_model=List[JobSearchHistoryResponse])
def job_history(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    discovery = AIJobDiscoveryService(db)
    return discovery.get_history(current_user)

@router.post("/{job_id}/bookmark", response_model=BookmarkResponse)
def bookmark_job(job_id: int, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    service = JobService(db)
    bookmark = service.bookmark_job(user_id=current_user.id, job_id=job_id)
    AIJobDiscoveryService(db).engine.record_action(current_user, job_id, "bookmarked", payload={"source": "path"})
    return bookmark

@router.post("/bookmark", response_model=BookmarkResponse)
def bookmark_job_body(
    job_id: int = Body(..., embed=True),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    service = JobService(db)
    bookmark = service.bookmark_job(user_id=current_user.id, job_id=job_id)
    AIJobDiscoveryService(db).engine.record_action(current_user, job_id, "bookmarked", payload={"source": "body"})
    return bookmark

@router.get("/bookmarks", response_model=List[BookmarkResponse])
def get_bookmarks(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    service = JobService(db)
    return service.get_bookmarks(user_id=current_user.id)

@router.post("/apply", response_model=JobActionResponse)
def apply_job(
    request: JobApplyRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    discovery = AIJobDiscoveryService(db)
    discovery.engine.record_action(
        current_user,
        request.job_id,
        "applied",
        note=request.note,
        payload={"external_url": request.external_url},
    )
    return JobActionResponse(
        message="Application recorded",
        job_id=request.job_id,
        status="applied",
        details={"external_url": request.external_url, "note": request.note},
    )
