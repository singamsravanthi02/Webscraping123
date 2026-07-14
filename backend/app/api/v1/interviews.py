from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.db.session import get_db
from app.api.dependencies.auth import get_current_active_user
from app.domain.users.models import User
from app.domain.interviews import schemas, models
from app.domain.interviews.services import get_system_prompt_for_type, generate_ai_response, evaluate_interview_transcript
from app.domain.ai_orchestration.models import StudentAIMemory
from app.domain.ai_orchestration.placement_engine import placement_engine

router = APIRouter()

@router.post("", response_model=schemas.InterviewResponse)
def create_interview(request: schemas.InterviewCreate, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    interview = models.InterviewSession(
        user_id=current_user.id,
        title=request.title,
        type=request.type,
        resume_text=request.resume_text,
        job_description=request.job_description,
        status=models.InterviewStatus.PENDING
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)
    return interview

@router.get("", response_model=List[schemas.InterviewResponse])
def get_user_interviews(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    return db.query(models.InterviewSession).filter(models.InterviewSession.user_id == current_user.id).order_by(models.InterviewSession.start_time.desc()).all()

@router.get("/{id}", response_model=schemas.InterviewDetailResponse)
def get_interview(id: int, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    interview = db.query(models.InterviewSession).filter(models.InterviewSession.id == id, models.InterviewSession.user_id == current_user.id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    return interview

@router.post("/{id}/start", response_model=schemas.InterviewMessageResponse)
async def start_interview(id: int, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    interview = db.query(models.InterviewSession).filter(models.InterviewSession.id == id, models.InterviewSession.user_id == current_user.id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
        
    if interview.status != models.InterviewStatus.PENDING:
        raise HTTPException(status_code=400, detail="Interview already started")
        
    interview.status = models.InterviewStatus.IN_PROGRESS
    
    # Generate system prompt
    system_prompt = get_system_prompt_for_type(interview.type, interview.job_description, interview.resume_text)
    
    # Save system prompt to db for context
    sys_msg = models.InterviewMessage(interview_id=interview.id, role=models.MessageRole.SYSTEM, content=system_prompt)
    db.add(sys_msg)
    
    # Ask AI to generate first question
    first_question = await generate_ai_response(system_prompt, [], "Start the interview.", current_user.id)
    
    ai_msg = models.InterviewMessage(interview_id=interview.id, role=models.MessageRole.AI, content=first_question)
    db.add(ai_msg)
    
    db.commit()
    db.refresh(ai_msg)
    
    return ai_msg

@router.post("/{id}/message", response_model=schemas.InterviewMessageResponse)
async def send_message(id: int, request: schemas.ChatMessageRequest, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    interview = db.query(models.InterviewSession).filter(models.InterviewSession.id == id, models.InterviewSession.user_id == current_user.id).first()
    if not interview or interview.status != models.InterviewStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Invalid interview session")
        
    # Save user message
    user_msg = models.InterviewMessage(interview_id=interview.id, role=models.MessageRole.USER, content=request.content)
    db.add(user_msg)
    db.flush()
    
    # Get chat history
    history = db.query(models.InterviewMessage).filter(models.InterviewMessage.interview_id == interview.id).order_by(models.InterviewMessage.created_at.asc()).all()
    history_dicts = [{"role": msg.role, "content": msg.content} for msg in history]
    
    sys_msg = next((m for m in history_dicts if m["role"] == models.MessageRole.SYSTEM), None)
    sys_prompt = sys_msg["content"] if sys_msg else ""
    
    # Generate AI response
    ai_response_text = await generate_ai_response(sys_prompt, history_dicts, request.content, current_user.id)
    
    ai_msg = models.InterviewMessage(interview_id=interview.id, role=models.MessageRole.AI, content=ai_response_text)
    db.add(ai_msg)
    
    db.commit()
    db.refresh(ai_msg)
    
    return ai_msg

@router.post("/{id}/end", response_model=schemas.InterviewResultResponse)
async def end_interview(id: int, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    interview = db.query(models.InterviewSession).filter(models.InterviewSession.id == id, models.InterviewSession.user_id == current_user.id).first()
    if not interview or interview.status != models.InterviewStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Invalid interview session")
        
    interview.status = models.InterviewStatus.COMPLETED
    import datetime as dt
    interview.end_time = dt.datetime.now(dt.timezone.utc)
    
    # Get history to evaluate
    history = db.query(models.InterviewMessage).filter(
        models.InterviewMessage.interview_id == interview.id,
        models.InterviewMessage.role != models.MessageRole.SYSTEM
    ).order_by(models.InterviewMessage.created_at.asc()).all()
    
    history_dicts = [{"role": msg.role, "content": msg.content} for msg in history]
    
    sys_msg = db.query(models.InterviewMessage).filter(models.InterviewMessage.interview_id == interview.id, models.InterviewMessage.role == models.MessageRole.SYSTEM).first()
    sys_prompt = sys_msg.content if sys_msg else ""
    
    # Evaluate
    eval_data = await evaluate_interview_transcript(sys_prompt, history_dicts, current_user.id)
    
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
        placement_readiness_contribution=eval_data.get("placement_readiness_contribution", 0)
    )
    
    db.add(result)
    db.commit()
    db.refresh(result)
    
    # --- Update Student AI Memory ---
    memory = db.query(StudentAIMemory).filter(StudentAIMemory.user_id == current_user.id).first()
    if not memory:
        memory = StudentAIMemory(user_id=current_user.id)
        db.add(memory)
        db.flush()
        
    # Append to interview feedback
    feedback_entry = {
        "interview_id": interview.id,
        "overall_grade": result.overall_grade,
        "date": interview.end_time.isoformat() if interview.end_time else None
    }
    
    # We must create a new list for SQLAlchemy JSON mutation detection
    curr_feedback = list(memory.interview_feedback or [])
    curr_feedback.append(feedback_entry)
    memory.interview_feedback = curr_feedback
    
    # Add new strengths and weaknesses
    curr_strong = list(set((memory.strong_topics or []) + result.strengths))
    curr_weak = list(set((memory.weak_topics or []) + result.weaknesses))
    
    memory.strong_topics = curr_strong
    memory.weak_topics = curr_weak
    
    db.commit()
    
    # --- Recalculate Placement Readiness ---
    placement_engine.calculate_score(current_user.id)
    
    return result
