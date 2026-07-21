from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from .models import AssessmentType, QuestionType, AttemptStatus

class QuestionBase(BaseModel):
    id: int
    topic: str
    subject: str
    difficulty: int
    type: QuestionType
    content: str
    options: Optional[Any] = None

    class Config:
        from_attributes = True

class AssessmentBase(BaseModel):
    id: int
    title: str
    type: AssessmentType
    duration_minutes: int
    is_adaptive: bool
    is_proctored: bool
    total_marks: float
    
    class Config:
        from_attributes = True

class AssessmentStartResponse(BaseModel):
    attempt_id: int
    assessment: AssessmentBase
    questions: List[QuestionBase]
    start_time: datetime

class AnswerSubmission(BaseModel):
    question_id: int
    user_answer: str
    time_taken_seconds: int

class AssessmentSubmitRequest(BaseModel):
    attempt_id: int
    answers: List[AnswerSubmission]
    tab_switch_count: int
    fullscreen_violations: int

class AssessmentResultResponse(BaseModel):
    attempt_id: int
    score: float
    total_marks: float
    status: AttemptStatus
    tab_switch_count: int
    ai_recommendations: List[str]
