from typing import Dict, Any, List
from time import perf_counter
import logging
import httpx
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.domain.interviews import models
from app.domain.interviews.models import InterviewType, MessageRole
from app.domain.ai_orchestration.placement_engine import placement_engine
from app.domain.ai_orchestration.gateway import gateway
from app.domain.ai_orchestration.agents.interviews import InterviewAgent
from app.domain.ai_orchestration.prompts import (
    interview_system_prompt,
    interview_evaluation_prompt,
    PROMPT_VERSION_INTERVIEW_EVAL,
)
from app.domain.ai_orchestration.schemas import InterviewEvaluationSchema

agent = InterviewAgent()
logger = logging.getLogger(__name__)

WANDBOX_COMPILERS = {
    "java": "openjdk-jdk-21+35",
    "cpp": "gcc-13.2.0",
}

def get_system_prompt_for_type(interview_type: InterviewType, job_description: str = None, resume_text: str = None) -> str:
    return interview_system_prompt(interview_type.value, job_description, resume_text)

def _fallback_question(system_prompt: str, chat_history: List[Dict[str, str]], new_message: str) -> str:
    prompt = (system_prompt or "").lower()
    user_turns = sum(1 for msg in chat_history if msg.get("role") == MessageRole.USER)

    if "coding" in prompt:
        return (
            "Talk me through your approach first, then code the core solution. "
            "What is the time and space complexity of your approach?"
            if user_turns == 0
            else "Now tighten the solution. Which edge cases or test cases would you add next?"
        )
    if "behavioral" in prompt:
        return (
            "Tell me about a recent challenge you handled and what you learned from it."
            if user_turns == 0
            else "What would you do differently if that same situation happened again?"
        )
    if "hr" in prompt:
        return (
            "Tell me about yourself and the kind of role you're targeting."
            if user_turns == 0
            else "What kind of team environment helps you do your best work?"
        )
    if "system design" in prompt or "architecture" in prompt:
        return (
            "Walk me through the high-level architecture first, then call out the main trade-off."
            if user_turns == 0
            else "Which part of the design will become the first bottleneck as traffic grows?"
        )
    if "mock company" in prompt:
        return (
            "Let's run this like a real panel. Start with the strongest part of your profile."
            if user_turns == 0
            else "What would you improve before a second round with this company?"
        )
    return (
        "Let's continue. What would you do next?"
        if user_turns > 0
        else "Tell me how you would approach this interview to start."
    )


def _fallback_evaluation(chat_history: List[Dict[str, str]]) -> Dict[str, Any]:
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
            "Prepare concise examples of accessibility, state management, and API integration work.",
        ],
        "strengths": [
            "Engaged with the interviewer",
            "Communicated intent clearly",
        ],
        "weaknesses": [
            "Insufficient transcript depth for a full technical assessment",
            "No verified evidence of advanced problem solving in this short session",
        ],
        "recommended_topics": [
            "React component architecture",
            "Accessibility patterns",
            "State management and API integration",
        ],
        "learning_plan": "1. Review one frontend system design topic. 2. Practice one STAR-style answer. 3. Rehearse a short code walkthrough. 4. Run another mock interview and compare progress.",
        "placement_readiness_contribution": round(1.5 + engagement_bonus / 2, 1),
    }

async def generate_ai_response(system_prompt: str, chat_history: List[Dict[str, str]], new_message: str, user_id: int) -> str:
    try:
        return agent.process_turn(user_id, system_prompt, chat_history, new_message)
    except Exception as e:
        logger.warning("Error calling Gemini: %s", e)
        return _fallback_question(system_prompt, chat_history, new_message)

async def evaluate_interview_transcript(system_prompt: str, chat_history: List[Dict[str, str]], user_id: int) -> Dict[str, Any]:
    transcript = "Interview Log:\n\n"
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
        logger.warning("Error evaluating interview: %s", e)
        return _fallback_evaluation(chat_history)


async def finalize_interview_report(interview_id: int, user_id: int) -> None:
    db: Session = SessionLocal()
    timings: Dict[str, float] = {}
    started = perf_counter()
    history_dicts: List[Dict[str, str]] = []
    interview = None
    try:
        step = perf_counter()
        interview = (
            db.query(models.InterviewSession)
            .filter(models.InterviewSession.id == interview_id, models.InterviewSession.user_id == user_id)
            .first()
        )
        timings["load_interview_ms"] = round((perf_counter() - step) * 1000, 1)
        if not interview:
            logger.warning("Interview %s not found for report generation", interview_id)
            return

        if interview.result:
            logger.info("Interview %s already has a result; skipping report generation", interview_id)
            return

        step = perf_counter()
        history = (
            db.query(models.InterviewMessage)
            .filter(
                models.InterviewMessage.interview_id == interview.id,
                models.InterviewMessage.role != models.MessageRole.SYSTEM,
            )
            .order_by(models.InterviewMessage.created_at.asc())
            .all()
        )
        history_dicts = [{"role": msg.role, "content": msg.content} for msg in history]
        sys_msg = (
            db.query(models.InterviewMessage)
            .filter(models.InterviewMessage.interview_id == interview.id, models.InterviewMessage.role == models.MessageRole.SYSTEM)
            .first()
        )
        sys_prompt = sys_msg.content if sys_msg else ""
        timings["collect_answers_ms"] = round((perf_counter() - step) * 1000, 1)

        step = perf_counter()
        eval_data = await evaluate_interview_transcript(sys_prompt, history_dicts, user_id)
        timings["ai_evaluation_ms"] = round((perf_counter() - step) * 1000, 1)

        step = perf_counter()
        result = models.InterviewResult(
            interview_id=interview.id,
            confidence_score=eval_data.get("confidence_score", 0),
            communication_score=eval_data.get("communication_score", 0),
            technical_score=eval_data.get("technical_score", 0),
            problem_solving_score=eval_data.get("problem_solving_score", 0),
            overall_grade=eval_data.get("overall_grade", 0),
            feedback_summary=eval_data.get("feedback_summary", ""),
            suggestions=eval_data.get("suggestions", []),
            strengths=eval_data.get("strengths", []),
            weaknesses=eval_data.get("weaknesses", []),
            recommended_topics=eval_data.get("recommended_topics", []),
            learning_plan=eval_data.get("learning_plan", ""),
            placement_readiness_contribution=eval_data.get("placement_readiness_contribution", 0),
        )
        db.add(result)
        db.commit()
        db.refresh(result)
        timings["save_report_ms"] = round((perf_counter() - step) * 1000, 1)

        step = perf_counter()
        try:
            memory = db.query(models.StudentAIMemory).filter(models.StudentAIMemory.user_id == user_id).first()
            if not memory:
                memory = models.StudentAIMemory(user_id=user_id)
                db.add(memory)
                db.flush()

            weaknesses = list(result.weaknesses or [])
            strengths = list(result.strengths or [])
            communication_issues = [
                item for item in weaknesses if any(token in item.lower() for token in ("communicat", "clarity", "hesitat", "confidence"))
            ]
            coding_mistakes = weaknesses if interview.type == models.InterviewType.CODING else []
            if result.overall_grade is None:
                future_difficulty = "medium"
            elif result.overall_grade >= 8:
                future_difficulty = "hard"
            elif result.overall_grade >= 6:
                future_difficulty = "medium"
            else:
                future_difficulty = "easy"

            feedback_entry = {
                "interview_id": interview.id,
                "overall_grade": result.overall_grade,
                "date": interview.end_time.isoformat() if interview.end_time else None,
                "strong_topics": strengths,
                "weak_topics": weaknesses,
                "coding_mistakes": coding_mistakes,
                "communication_issues": communication_issues,
                "recommended_roadmap": result.learning_plan,
                "future_difficulty": future_difficulty,
            }

            curr_feedback = list(memory.interview_feedback or [])
            curr_feedback.append(feedback_entry)
            memory.interview_feedback = curr_feedback
            memory.strong_topics = list(set((memory.strong_topics or []) + strengths))
            memory.weak_topics = list(set((memory.weak_topics or []) + weaknesses))
            db.commit()
        except Exception as exc:
            db.rollback()
            logger.warning("Interview memory update failed for %s: %s", interview_id, exc)
        timings["memory_update_ms"] = round((perf_counter() - step) * 1000, 1)

        step = perf_counter()
        try:
            placement_engine.calculate_score(user_id)
        except Exception as exc:
            logger.warning("Placement score recalculation failed for interview %s: %s", interview_id, exc)
        timings["placement_score_ms"] = round((perf_counter() - step) * 1000, 1)
        timings["total_ms"] = round((perf_counter() - started) * 1000, 1)
        logger.info("Interview report finalized interview_id=%s timings=%s", interview_id, timings)
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to finalize interview report for %s: %s", interview_id, exc)
        try:
            if interview and not interview.result:
                fallback = _fallback_evaluation(history_dicts)
                result = models.InterviewResult(
                    interview_id=interview.id,
                    confidence_score=fallback.get("confidence_score", 0),
                    communication_score=fallback.get("communication_score", 0),
                    technical_score=fallback.get("technical_score", 0),
                    problem_solving_score=fallback.get("problem_solving_score", 0),
                    overall_grade=fallback.get("overall_grade", 0),
                    feedback_summary=fallback.get("feedback_summary", ""),
                    suggestions=fallback.get("suggestions", []),
                    strengths=fallback.get("strengths", []),
                    weaknesses=fallback.get("weaknesses", []),
                    recommended_topics=fallback.get("recommended_topics", []),
                    learning_plan=fallback.get("learning_plan", ""),
                    placement_readiness_contribution=fallback.get("placement_readiness_contribution", 0),
                )
                db.add(result)
                db.commit()
        except Exception as fallback_exc:
            db.rollback()
            logger.exception("Fallback interview report generation also failed for %s: %s", interview_id, fallback_exc)
    finally:
        db.close()


def run_code_snippet(language: str, code: str, stdin: str = "") -> Dict[str, Any]:
    normalized = (language or "").strip().lower()
    compiler = WANDBOX_COMPILERS.get(normalized)
    if not compiler:
        return {
            "language": normalized or "unknown",
            "compiler": None,
            "success": False,
            "status": "",
            "stdout": "",
            "stderr": f"Unsupported language: {language}",
            "compiler_output": "",
            "compiler_error": "",
            "program_output": "",
            "program_error": "",
            "message": f"Unsupported language: {language}",
        }

    payload = {
        "compiler": compiler,
        "code": code,
        "stdin": stdin or "",
    }

    try:
        response = httpx.post("https://wandbox.org/api/compile.json", json=payload, timeout=30.0)
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        logger.warning("Wandbox code execution failed for %s: %s", normalized, exc)
        return {
            "language": normalized,
            "compiler": compiler,
            "success": False,
            "status": "",
            "stdout": "",
            "stderr": "",
            "compiler_output": "",
            "compiler_error": "",
            "program_output": "",
            "program_error": "",
            "message": f"Code runner unavailable: {exc}",
        }

    program_output = data.get("program_output") or ""
    program_error = data.get("program_error") or ""
    compiler_output = data.get("compiler_output") or ""
    compiler_error = data.get("compiler_error") or ""
    program_message = data.get("program_message") or ""
    compiler_message = data.get("compiler_message") or ""
    status = str(data.get("status") or "")
    return {
        "language": normalized,
        "compiler": compiler,
        "success": status == "0",
        "status": status,
        "stdout": program_output or compiler_output,
        "stderr": program_error or compiler_error,
        "compiler_output": compiler_output,
        "compiler_error": compiler_error,
        "program_output": program_output,
        "program_error": program_error,
        "message": program_message or compiler_message or (program_error or compiler_error or program_output),
    }
