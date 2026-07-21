from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.domain.assessments.schemas import AssessmentBase, AssessmentStartResponse, AssessmentSubmitRequest, AssessmentResultResponse
from pydantic import BaseModel
from typing import Optional
from app.services.assessment_service import AssessmentService
from app.api.dependencies.auth import get_current_active_user
from app.domain.users.models import User

router = APIRouter()

@router.get("", response_model=List[AssessmentBase])
def get_assessments(db: Session = Depends(get_db)):
    service = AssessmentService(db)
    return service.get_assessments()

@router.post("/{id}/start", response_model=AssessmentStartResponse)
def start_assessment(id: int, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    service = AssessmentService(db)
    attempt = service.start_assessment(user_id=current_user.id, assessment_id=id)
    questions = service.get_assessment_questions(assessment_id=id)
    question_payloads = [service._question_response(question) for question in questions]
    
    return {
        "attempt_id": attempt.id,
        "assessment": attempt.assessment,
        "questions": question_payloads,
        "start_time": attempt.start_time
    }

@router.post("/submit", response_model=AssessmentResultResponse)
def submit_assessment(request: AssessmentSubmitRequest, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    service = AssessmentService(db)
    return service.submit_assessment(user_id=current_user.id, request=request)

class QuizGenerateRequest(BaseModel):
    subject: Optional[str] = None
    topic: Optional[str] = None
    difficulty: Optional[int] = None
    bloom_level: Optional[str] = None
    company_pattern: Optional[str] = None
    limit: int = 10

@router.post("/generate_quiz")
def generate_dynamic_quiz(
    req: QuizGenerateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    service = AssessmentService(db)
    return service.generate_dynamic_quiz(
        user_id=current_user.id,
        subject=req.subject,
        topic=req.topic,
        difficulty=req.difficulty,
        bloom_level=req.bloom_level,
        company_pattern=req.company_pattern,
        limit=req.limit,
    )
