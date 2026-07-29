from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Dict, Any
import os
import uuid
import shutil
import logging
import threading
from pathlib import Path

from app.db.session import get_db, SessionLocal
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
RESUME_MAX_BYTES = 10 * 1024 * 1024
PROFILE_MAX_BYTES = 5 * 1024 * 1024


def _upload_extension(file: UploadFile, allowed_exts: set[str]) -> str:
    ext = Path(file.filename or "").suffix.lower().lstrip(".")
    if not ext or ext not in allowed_exts:
        raise HTTPException(status_code=400, detail="Invalid file type")
    return ext


def _upload_size(file: UploadFile) -> int:
    current = file.file.tell()
    file.file.seek(0, os.SEEK_END)
    size = file.file.tell()
    file.file.seek(current)
    return size


def _refresh_job_discovery_for_user(user_id: int) -> None:
    def _run() -> None:
        db = SessionLocal()
        try:
            user = db.get(User, user_id)
            if user is None:
                return
            AIJobDiscoveryService(db).refresh_user(user)
        except Exception as exc:
            logger.warning("Failed to refresh job discovery for user %s: %s", user_id, exc)
        finally:
            db.close()

    threading.Thread(target=_run, daemon=True).start()

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

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="Profile update conflicts with an existing record") from exc
    db.refresh(current_user)
    _refresh_job_discovery_for_user(current_user.id)
    return current_user

@router.post("/upload/resume", response_model=SuccessResponse)
def upload_resume(
    file: UploadFile = File(...), 
    current_user: User = Depends(get_current_active_user), 
    db: Session = Depends(get_db)
):
    allowed_types = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    ext = _upload_extension(file, set(allowed_types))
    if file.content_type != allowed_types[ext]:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are allowed for resumes")

    if _upload_size(file) > RESUME_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Resume file too large. Maximum size is 10MB.")

    filename = f"{current_user.id}_{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, "resume", filename)
    file.file.seek(0)
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
    _refresh_job_discovery_for_user(current_user.id)

    return {"message": "Resume uploaded successfully and pipeline triggered"}

@router.post("/upload/profile", response_model=SuccessResponse)
def upload_profile_picture(
    file: UploadFile = File(...), 
    current_user: User = Depends(get_current_active_user), 
    db: Session = Depends(get_db)
):
    allowed_types = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
    }
    ext = _upload_extension(file, set(allowed_types))
    if file.content_type != allowed_types[ext]:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, and WEBP files are allowed")

    if _upload_size(file) > PROFILE_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Profile picture too large. Maximum size is 5MB.")

    filename = f"{current_user.id}_{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, "profile", filename)
    file.file.seek(0)
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    current_user.profile_picture = f"/uploads/profile/{filename}"
    db.commit()
    _refresh_job_discovery_for_user(current_user.id)
    
    return {"message": "Profile picture uploaded successfully"}


@router.delete("/me", response_model=SuccessResponse)
def delete_current_user_account(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    user_id = current_user.id
    resume_url = current_user.resume_url
    profile_picture = current_user.profile_picture

    db.delete(current_user)
    db.commit()

    for path in (resume_url, profile_picture):
        if not path:
            continue
        local_path = path.lstrip("/")
        if local_path.startswith("uploads"):
            try:
                os.remove(local_path)
            except OSError as exc:
                logger.debug("Could not remove upload file %s: %s", local_path, exc)

    logger.info("Deleted user account %s", user_id)
    return {"message": "Account deleted successfully"}

from pydantic import BaseModel

class OnboardingStepData(BaseModel):
    step_id: str
    data: Dict[str, Any]

@router.patch("/onboard/step", response_model=SuccessResponse)
def update_onboarding_step(
    step_data: OnboardingStepData,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    profile_data = current_user.profile_data or {}
    profile_data[step_data.step_id] = step_data.data
    
    # In SQLAlchemy JSONB requires explicit reassignment or flag_modified to detect changes
    from sqlalchemy.orm.attributes import flag_modified
    current_user.profile_data = profile_data
    flag_modified(current_user, "profile_data")
    
    db.commit()
    return {"message": "Step saved successfully"}

@router.post("/onboard/complete", response_model=SuccessResponse)
def complete_onboarding(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    current_user.profile_completed = True
    db.commit()
    _refresh_job_discovery_for_user(current_user.id)
    return {"message": "Onboarding completed successfully"}
