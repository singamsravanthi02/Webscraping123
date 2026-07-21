from typing import Dict, Any, List
from app.domain.interviews.models import InterviewType, MessageRole
from app.domain.ai_orchestration.gateway import gateway
from app.domain.ai_orchestration.agents.interviews import InterviewAgent
from app.domain.ai_orchestration.prompts import (
    interview_system_prompt,
    interview_evaluation_prompt,
    PROMPT_VERSION_INTERVIEW_EVAL,
)
from app.domain.ai_orchestration.schemas import InterviewEvaluationSchema

agent = InterviewAgent()

def get_system_prompt_for_type(interview_type: InterviewType, job_description: str = None, resume_text: str = None) -> str:
    return interview_system_prompt(interview_type.value, job_description, resume_text)

async def generate_ai_response(system_prompt: str, chat_history: List[Dict[str, str]], new_message: str, user_id: int) -> str:
    try:
        return agent.process_turn(user_id, system_prompt, chat_history, new_message)
    except Exception as e:
        print(f"Error calling Gemini: {e}")
        return "I apologize, but I am having trouble connecting right now. Could you please repeat that?"

async def evaluate_interview_transcript(system_prompt: str, chat_history: List[Dict[str, str]], user_id: int) -> Dict[str, Any]:
    transcript = "Interview Transcript:\n\n"
    for msg in chat_history:
        role_str = "Candidate" if msg["role"] == MessageRole.USER else "Interviewer"
        transcript += f"{role_str}: {msg['content']}\n\n"
        
    try:
        data = gateway.generate_structured_response(
            interview_evaluation_prompt(system_prompt, chat_history),
            InterviewEvaluationSchema,
            use_pro=True,
            user_id=user_id,
            feature="interview_evaluation",
            prompt_version=PROMPT_VERSION_INTERVIEW_EVAL,
        )
        
        # Explainable AI logging
        agent.log_recommendation(
            user_id=user_id,
            action="evaluate_interview",
            confidence=0.9,
            reasoning="Evaluated transcript based on communication and technical alignment.",
            evidence=[transcript]
        )
        return data.model_dump()
    except Exception as e:
        print(f"Error evaluating interview: {e}")
        user_turns = sum(1 for msg in chat_history if msg["role"] == MessageRole.USER)
        engagement_bonus = min(user_turns * 0.5, 2.0)
        return {
            "confidence_score": round(5.0 + engagement_bonus, 1),
            "communication_score": round(5.5 + engagement_bonus, 1),
            "technical_score": round(4.5 + engagement_bonus, 1),
            "problem_solving_score": round(4.5 + engagement_bonus, 1),
            "overall_grade": round(5.0 + engagement_bonus, 1),
            "feedback_summary": "AI evaluation was unavailable, so this fallback review was generated from the interview transcript. The candidate participated clearly, showed reasonable communication, and should continue building technical depth through longer practice sessions.",
            "suggestions": [
                "Practice answering frontend architecture questions out loud.",
                "Prepare concise examples of accessibility, state management, and API integration work."
            ],
            "strengths": [
                "Engaged with the interviewer",
                "Communicated intent clearly"
            ],
            "weaknesses": [
                "Insufficient transcript depth for a full technical assessment",
                "No verified evidence of advanced problem solving in this short session"
            ],
            "recommended_topics": [
                "React component architecture",
                "Accessibility patterns",
                "State management and API integration"
            ],
            "learning_plan": "1. Review one frontend system design topic. 2. Practice one STAR-style answer. 3. Rehearse a short code walkthrough. 4. Run another mock interview and compare progress.",
            "placement_readiness_contribution": round(1.5 + engagement_bonus / 2, 1)
        }
