from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
import os
import uuid
import shutil
import logging

from app.db.session import get_db
from app.domain.users.schemas import UserResponse, ProfileUpdate, SuccessResponse
from app.domain.users.models import User
from app.api.dependencies.auth import get_current_active_user
from app.worker.tasks import parse_resume_task
from app.domain.job_discovery.services import AIJobDiscoveryService

router = APIRouter()
logger = logging.getLogger(__name__)

UPLOAD_DIR = "uploads"
os.makedirs(f"{UPLOAD_DIR}/resume", exist_ok=True)
os.makedirs(f"{UPLOAD_DIR}/profile", exist_ok=True)


def _refresh_job_discovery_for_user(db: Session, user: User) -> None:
    try:
        AIJobDiscoveryService(db).refresh_user(user)
    except Exception as exc:
        logger.warning("Failed to refresh job discovery for user %s: %s", user.id, exc)

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_active_user)):
    return current_user

@router.put("/me", response_model=UserResponse)
def update_current_user_profile(
    profile_update: ProfileUpdate, 
    current_user: User = Depends(get_current_active_user), 
    db: Session = Depends(get_db)
):
    update_data = profile_update.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(current_user, field, value)

    # Check if essential profile fields are now filled to mark profile_completed = True
    essential_fields = [
        current_user.full_name, current_user.college, current_user.department, 
        current_user.branch, current_user.semester, current_user.cgpa,
        current_user.skills, current_user.career_goal, current_user.resume_url
    ]
    
    if all(essential_fields):
        current_user.profile_completed = True

    db.commit()
    db.refresh(current_user)
    _refresh_job_discovery_for_user(db, current_user)
    return current_user

@router.post("/upload/resume", response_model=SuccessResponse)
def upload_resume(
    file: UploadFile = File(...), 
    current_user: User = Depends(get_current_active_user), 
    db: Session = Depends(get_db)
):
    allowed_types = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are allowed for resumes")
        
    ext = file.filename.split('.')[-1]
    filename = f"{current_user.id}_{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, "resume", filename)
    
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    current_user.resume_url = f"/uploads/resume/{filename}"
    db.commit()
    
    # Trigger Resume Parsing Pipeline
    try:
        parse_resume_task.delay(str(current_user.id), current_user.resume_url)
    except Exception as exc:
        logger.warning(
            "Resume parsing pipeline unavailable for user %s: %s",
            current_user.id,
            exc,
        )
    _refresh_job_discovery_for_user(db, current_user)

    return {"message": "Resume uploaded successfully and pipeline triggered"}

@router.post("/upload/profile", response_model=SuccessResponse)
def upload_profile_picture(
    file: UploadFile = File(...), 
    current_user: User = Depends(get_current_active_user), 
    db: Session = Depends(get_db)
):
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, and WEBP files are allowed")
        
    ext = file.filename.split('.')[-1]
    filename = f"{current_user.id}_{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, "profile", filename)
    
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    current_user.profile_picture = f"/uploads/profile/{filename}"
    db.commit()
    _refresh_job_discovery_for_user(db, current_user)
    
    return {"message": "Profile picture uploaded successfully"}
