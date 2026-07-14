from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.domain.ai_orchestration.models import StudentAIMemory
from app.domain.users.models import User
import logging

logger = logging.getLogger(__name__)

class PlacementReadinessEngine:
    """
    Calculates a deterministic composite score based on the student's holistic performance.
    """
    
    def __init__(self):
        # Weights for the composite score
        self.weights = {
            "technical_assessments": 0.35,
            "interview_performance": 0.35,
            "resume_quality": 0.20,
            "learning_engagement": 0.10
        }

    def calculate_score(self, user_id: int) -> float:
        db: Session = SessionLocal()
        try:
            memory = db.query(StudentAIMemory).filter(StudentAIMemory.user_id == user_id).first()
            if not memory:
                return 0.0
                
            # In a full production environment, these would be aggregated from actual tables
            # Here we demonstrate the algorithmic blending from memory blobs
            
            # 1. Technical Assessments (Avg of test scores)
            tests = memory.test_performance.values() if memory.test_performance else []
            tech_score = sum(tests) / len(tests) if tests else 0.0
            
            # 2. Interviews
            interviews = memory.interview_feedback
            int_score = 0.0
            if interviews:
                # Assuming feedback dict has an 'overall_grade' out of 10, scale to 100
                grades = [i.get("overall_grade", 0) * 10 for i in interviews]
                int_score = sum(grades) / len(grades)
                
            # 3. Resume Quality (Assuming stored in a generic dict or defaulted)
            # Placeholder for resume score 0-100
            resume_score = 75.0 
            
            # 4. Learning Engagement (Proxy: number of strong topics vs weak)
            strong_count = len(memory.strong_topics)
            weak_count = len(memory.weak_topics)
            total_topics = strong_count + weak_count
            learn_score = (strong_count / total_topics * 100) if total_topics > 0 else 50.0
            
            # Calculate weighted average
            composite = (
                (tech_score * self.weights["technical_assessments"]) +
                (int_score * self.weights["interview_performance"]) +
                (resume_score * self.weights["resume_quality"]) +
                (learn_score * self.weights["learning_engagement"])
            )
            
            # Update memory
            memory.placement_readiness_score = composite
            db.commit()
            
            return composite
            
        except Exception as e:
            logger.error(f"Failed to calculate placement score for {user_id}: {e}")
            db.rollback()
            return 0.0
        finally:
            db.close()

# Singleton
placement_engine = PlacementReadinessEngine()
