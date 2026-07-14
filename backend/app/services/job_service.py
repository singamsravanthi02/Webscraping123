from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.domain.jobs.models import Job, JobBookmark, JobStatus
from app.domain.users.models import User
from typing import List
import random # For dummy match score fallback
from app.domain.ai_orchestration.agents.jobs import JobMatchingAgent

class JobService:
    def __init__(self, db: Session):
        self.db = db

    def get_jobs(self, user: User, skip: int = 0, limit: int = 20, search: str = None) -> List[Job]:
        query = self.db.query(Job).filter(Job.status == JobStatus.ACTIVE)
        if search:
            query = query.filter(Job.title.ilike(f"%{search}%") | Job.extracted_skills.contains(search))
        
        jobs = query.order_by(Job.posted_date.desc()).offset(skip).limit(limit).all()
        return jobs
        
    def get_recommended_jobs(self, user: User, limit: int = 10) -> List[Job]:
        """
        Returns jobs with match scores > 0, ordered by score.
        """
        query = self.db.query(Job).filter(Job.status == JobStatus.ACTIVE, Job.match_score > 0)
        jobs = query.order_by(Job.match_score.desc()).limit(limit).all()
        
        return jobs

    def bookmark_job(self, user_id: int, job_id: int) -> JobBookmark:
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
            
        existing = self.db.query(JobBookmark).filter(
            JobBookmark.user_id == user_id, 
            JobBookmark.job_id == job_id
        ).first()
        
        if existing:
            return existing
            
        bookmark = JobBookmark(user_id=user_id, job_id=job_id)
        self.db.add(bookmark)
        self.db.commit()
        self.db.refresh(bookmark)
        return bookmark

    def get_bookmarks(self, user_id: int) -> List[JobBookmark]:
        return self.db.query(JobBookmark).filter(JobBookmark.user_id == user_id).all()
