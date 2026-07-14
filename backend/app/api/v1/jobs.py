from fastapi import APIRouter, Body, Depends
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from typing import Any, Dict, List, Optional

from app.db.session import get_db
from app.domain.jobs.schemas import JobResponse, BookmarkResponse
from app.services.job_service import JobService
from app.api.dependencies.auth import get_current_active_user
from app.domain.users.models import User

from app.services.cache_service import cache
from app.domain.job_discovery.schemas import (
    AIChatRequest,
    AIJobDiscoveryResponse,
    JobActionResponse,
    JobApplyRequest,
    JobSearchHistoryResponse,
    RefreshResponse,
    SearchRequest,
)
from app.domain.job_discovery.services import AIJobDiscoveryService

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
    cache.set(cache_key, jsonable_encoder(jobs), expiration=120)
    return jobs

@router.get("/recommended", response_model=List[JobResponse])
def get_recommended_jobs(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    discovery = AIJobDiscoveryService(db)
    return discovery.recommended_jobs(current_user)

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

@router.post("/chat", response_model=AIJobDiscoveryResponse)
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
