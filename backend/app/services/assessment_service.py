from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.domain.assessments.models import Assessment, QuestionBank, AssessmentAttempt, AttemptDetail, AttemptStatus, AssessmentQuestionMap
from app.domain.assessments.schemas import AssessmentSubmitRequest, AnswerSubmission
from typing import List
from datetime import datetime

class AssessmentService:
    def __init__(self, db: Session):
        self.db = db

    def get_assessments(self) -> List[Assessment]:
        return self.db.query(Assessment).all()

    def start_assessment(self, user_id: int, assessment_id: int) -> AssessmentAttempt:
        assessment = self.db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")
            
        attempt = AssessmentAttempt(
            user_id=user_id,
            assessment_id=assessment_id,
            status=AttemptStatus.IN_PROGRESS
        )
        self.db.add(attempt)
        self.db.commit()
        self.db.refresh(attempt)
        return attempt
        
    def get_assessment_questions(self, assessment_id: int) -> List[QuestionBank]:
        return self.db.query(QuestionBank).join(
            AssessmentQuestionMap, QuestionBank.id == AssessmentQuestionMap.question_id
        ).filter(AssessmentQuestionMap.assessment_id == assessment_id).all()

    def submit_assessment(self, user_id: int, request: AssessmentSubmitRequest):
        attempt = self.db.query(AssessmentAttempt).filter(
            AssessmentAttempt.id == request.attempt_id,
            AssessmentAttempt.user_id == user_id
        ).first()
        
        if not attempt or attempt.status != AttemptStatus.IN_PROGRESS:
            raise HTTPException(status_code=400, detail="Invalid or already submitted attempt")
            
        assessment = attempt.assessment
        
        # Load all questions to avoid N+1 query issue
        question_ids = [ans.question_id for ans in request.answers]
        questions = self.db.query(QuestionBank).filter(QuestionBank.id.in_(question_ids)).all()
        question_map = {q.id: q for q in questions}
        
        # Calculate Score
        total_score = 0.0
        for ans in request.answers:
            question = question_map.get(ans.question_id)
            is_correct = False
            if question and question.correct_answer == ans.user_answer:
                is_correct = True
                total_score += question.points
            elif question and assessment.negative_mark_weight > 0:
                total_score -= (question.points * assessment.negative_mark_weight)
                
            detail = AttemptDetail(
                attempt_id=attempt.id,
                question_id=ans.question_id,
                user_answer=ans.user_answer,
                is_correct=is_correct,
                time_taken_seconds=ans.time_taken_seconds
            )
            self.db.add(detail)

        attempt.score = total_score
        attempt.status = AttemptStatus.SUBMITTED
        attempt.end_time = datetime.utcnow()
        attempt.tab_switch_count = request.tab_switch_count
        attempt.fullscreen_violations = request.fullscreen_violations
        
        self.db.commit()
        
        
        return {
            "attempt_id": attempt.id,
            "score": total_score,
            "total_marks": assessment.total_marks,
            "status": attempt.status,
            "tab_switch_count": attempt.tab_switch_count,
            "ai_recommendations": [
                f"Your score: {total_score}/{assessment.total_marks}",
                "Review the topics you got wrong to improve next time."
            ]
        }
