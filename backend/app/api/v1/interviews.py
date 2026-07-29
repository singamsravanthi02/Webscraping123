from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Any, Dict
from datetime import datetime
from time import perf_counter

from app.db.session import get_db
from app.api.dependencies.auth import get_current_active_user
from app.domain.users.models import User
from app.domain.interviews import schemas, models
from app.domain.interviews.services import get_system_prompt_for_type, generate_ai_response, run_code_snippet, finalize_interview_report
from app.domain.ai_orchestration.models import StudentAIMemory

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


@router.post("/code-run", response_model=schemas.CodeRunResponse)
def run_code(
    request: schemas.CodeRunRequest,
    current_user: User = Depends(get_current_active_user),
):
    return run_code_snippet(request.language, request.code, request.stdin or "")


@router.post("/{id}/lock-violations", response_model=dict)
def log_lock_violation(
    id: int,
    request: schemas.InterviewLockViolationCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    interview = db.query(models.InterviewSession).filter(
        models.InterviewSession.id == id,
        models.InterviewSession.user_id == current_user.id,
    ).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    violations = list(interview.lock_violations or [])
    violations.append(
        {
            "type": request.violation_type,
            "details": request.details,
            "recorded_at": datetime.utcnow().isoformat() + "Z",
        }
    )
    interview.lock_violations = violations
    db.commit()
    return {"message": "Violation recorded", "count": len(violations)}

@router.post("/{id}/end", response_model=Dict[str, Any])
async def end_interview(
    id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    started = perf_counter()
    interview = db.query(models.InterviewSession).filter(models.InterviewSession.id == id, models.InterviewSession.user_id == current_user.id).first()
    if not interview or interview.status != models.InterviewStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Invalid interview session")
        
    db_start = perf_counter()
    interview.status = models.InterviewStatus.COMPLETED
    import datetime as dt
    interview.end_time = dt.datetime.now(dt.timezone.utc)
    db.commit()
    timings = {
        "load_and_complete_ms": round((perf_counter() - db_start) * 1000, 1),
    }
    background_tasks.add_task(finalize_interview_report, interview.id, current_user.id)
    timings["queue_report_ms"] = round((perf_counter() - db_start) * 1000, 1)
    timings["total_ms"] = round((perf_counter() - started) * 1000, 1)
    return {
        "message": "Interview ended. Generating your AI Report...",
        "status": "processing",
        "result_ready": False,
        "interview_id": interview.id,
        "timings": timings,
    }
