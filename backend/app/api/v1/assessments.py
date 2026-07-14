from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.domain.assessments.schemas import AssessmentBase, AssessmentStartResponse, AssessmentSubmitRequest, AssessmentResultResponse
from app.domain.assessments.models import Assessment, QuestionBank, QuestionType, AssessmentType
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
    
    return {
        "attempt_id": attempt.id,
        "assessment": attempt.assessment,
        "questions": questions,
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
    company_pattern: Optional[str] = None
    limit: int = 10

@router.post("/generate_quiz")
def generate_dynamic_quiz(
    req: QuizGenerateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Dynamically constructs a quiz based on knowledge base questions.
    """
    query = db.query(QuestionBank)
    if req.subject:
        query = query.filter(QuestionBank.subject.ilike(f"%{req.subject}%"))
    if req.topic:
        query = query.filter(QuestionBank.topic.ilike(f"%{req.topic}%"))
    if req.difficulty:
        query = query.filter(QuestionBank.difficulty == req.difficulty)
    if req.company_pattern:
        query = query.filter(QuestionBank.company_tags.contains([req.company_pattern]))
        
    questions = query.limit(req.limit).all()
    
    if not questions:
        raise HTTPException(status_code=404, detail="No questions found matching criteria")
        
    # Create an ephemeral assessment wrapper
    assessment = Assessment(
        title=f"Dynamic Quiz: {req.subject or req.topic or 'Mixed'}",
        type=AssessmentType.APTITUDE,
        duration_minutes=len(questions) * 2,
        total_marks=float(sum([q.points for q in questions]))
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    
    # Map questions
    from app.domain.assessments.models import AssessmentQuestionMap
    for q in questions:
        db.add(AssessmentQuestionMap(assessment_id=assessment.id, question_id=q.id))
    db.commit()
    
    return {
        "assessment_id": assessment.id,
        "questions_count": len(questions),
        "total_marks": assessment.total_marks,
        "message": "Quiz generated successfully. Use /start endpoint."
    }
