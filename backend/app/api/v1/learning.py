from fastapi import APIRouter, Body, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
import os
import logging

from app.db.session import get_db
from app.api.dependencies.auth import get_current_active_user
from app.domain.users.models import User
from app.domain.learning import schemas, models
from app.domain.learning.services.rag_service import chat_with_context, generate_study_material
from app.domain.learning.services.qdrant_service import ingest_document
from app.domain.learning.services.roadmap_service import (
    build_learning_context,
    complete_module,
    get_module,
    get_module_section,
    get_or_create_roadmap,
    get_roadmap,
    list_roadmaps,
)
from app.services.document_text_extractor import extract_document_text
from app.domain.ai_orchestration.models import StudentAIMemory
from app.domain.ai_orchestration.placement_engine import placement_engine
import json
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)
ALLOWED_RESOURCE_SUFFIXES = {
    ".pdf": models.ResourceType.PDF,
    ".pptx": models.ResourceType.PPT,
    ".docx": models.ResourceType.TEXT,
    ".txt": models.ResourceType.TEXT,
    ".md": models.ResourceType.TEXT,
}

router = APIRouter()


@router.post("/roadmap", response_model=schemas.LearningRoadmapResponse)
def create_roadmap(
    request: schemas.LearningRoadmapCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return get_or_create_roadmap(
        db,
        user_id=current_user.id,
        title=request.title,
        subject=request.subject,
        difficulty=request.difficulty,
        estimated_hours=request.estimated_hours,
    )


@router.get("/roadmaps", response_model=List[schemas.LearningRoadmapResponse])
def get_roadmaps(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    return list_roadmaps(db, current_user.id)


@router.get("/roadmap/{id}", response_model=schemas.LearningRoadmapDetailResponse)
def read_roadmap(id: int, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    return get_roadmap(db, id, current_user.id)


@router.get("/module/{id}", response_model=schemas.LearningModuleDetailResponse)
def read_module(id: int, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    return get_module(db, id, current_user.id)


@router.post("/module/{id}/complete", response_model=dict)
def complete_learning_module(
    id: int,
    request: schemas.LearningModuleCompleteRequest = Body(default_factory=schemas.LearningModuleCompleteRequest),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return complete_module(db, id, current_user.id, int(request.time_spent or 0))


@router.get("/module/{id}/flashcards", response_model=dict)
def module_flashcards(id: int, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    return get_module_section(db, id, current_user.id, "flashcards")


@router.get("/module/{id}/quiz", response_model=dict)
def module_quiz(id: int, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    return get_module_section(db, id, current_user.id, "quiz")


@router.get("/module/{id}/summary", response_model=dict)
def module_summary(id: int, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    return get_module_section(db, id, current_user.id, "summary")


@router.post("/module/{id}/chat", response_model=dict)
async def module_chat(
    id: int,
    request: schemas.LearningModuleChatRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    module = (
        db.query(models.LearningModule)
        .join(models.LearningRoadmap, models.LearningRoadmap.id == models.LearningModule.roadmap_id)
        .filter(models.LearningModule.id == id, models.LearningRoadmap.user_id == current_user.id)
        .first()
    )
    if not module:
        raise HTTPException(status_code=404, detail="Learning module not found")
    roadmap = module.roadmap
    _, citations = build_learning_context(module.title, roadmap.subject if roadmap else None, db=db)
    response = await chat_with_context(
        f"{module.title}: {request.content}",
        [{"role": "user", "content": request.content}],
        subject=roadmap.subject if roadmap and roadmap.subject else (roadmap.title if roadmap else module.title),
        user_id=current_user.id,
        db=db,
    )
    return {
        "module_id": id,
        "content": response["content"],
        "citations": response["citations"] or citations,
        "retrieved_chunks": response["citations"] or citations,
    }

@router.post("/sessions", response_model=schemas.LearningSessionResponse)
def create_session(request: schemas.LearningSessionCreate, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    session = models.LearningSession(
        user_id=current_user.id,
        title=request.title,
        subject=request.subject,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

@router.get("/sessions", response_model=List[schemas.LearningSessionResponse])
def get_sessions(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    return db.query(models.LearningSession).filter(models.LearningSession.user_id == current_user.id).order_by(models.LearningSession.created_at.desc()).all()

@router.get("/sessions/{id}", response_model=schemas.LearningSessionDetailResponse)
def get_session(id: int, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    session = db.query(models.LearningSession).filter(models.LearningSession.id == id, models.LearningSession.user_id == current_user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.post("/sessions/{id}/chat", response_model=schemas.LearningMessageResponse)
async def chat(id: int, request: schemas.ChatMessageRequest, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    session = db.query(models.LearningSession).filter(models.LearningSession.id == id, models.LearningSession.user_id == current_user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    # Add user message
    user_msg = models.LearningMessage(session_id=session.id, role=models.MessageRole.USER, content=request.content)
    db.add(user_msg)
    db.flush()
    
    # Get history
    history = db.query(models.LearningMessage).filter(
        models.LearningMessage.session_id == session.id
    ).order_by(models.LearningMessage.created_at.asc()).all()
    
    history_dicts = [{"role": msg.role.value, "content": msg.content} for msg in history]
    
    # Call RAG
    ai_response = await chat_with_context(request.content, history_dicts, subject=session.subject, user_id=current_user.id, db=db)
    
    # Save AI message
    ai_msg = models.LearningMessage(
        session_id=session.id, 
        role=models.MessageRole.AI, 
        content=ai_response["content"],
        citations=ai_response["citations"]
    )
    db.add(ai_msg)
    db.commit()
    db.refresh(ai_msg)
    
    # Parse structured JSON to update memory with related topics
    try:
        parsed_ai = json.loads(ai_response["content"])
        if parsed_ai.get("related_topics"):
            memory = db.query(StudentAIMemory).filter(StudentAIMemory.user_id == current_user.id).first()
            if not memory:
                memory = StudentAIMemory(user_id=current_user.id)
                db.add(memory)
                db.flush()
                
            curr_learning = list(memory.learning_history or [])
            for t in parsed_ai["related_topics"]:
                if t not in curr_learning:
                    curr_learning.append(t)
            memory.learning_history = curr_learning
            db.commit()
    except Exception as e:
        logger.debug("Ignoring learning memory parse error: %s", e)
        
    return ai_msg

@router.post("/generate")
async def generate_material(request: schemas.GenerateRequest, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """
    Generate study materials (quiz, summary, flashcards) based on a topic.
    Returns plain text (or JSON string) based on generation.
    """
    if not request.topic:
        raise HTTPException(status_code=400, detail="Topic is required")
        
    result = await generate_study_material(request.type, request.topic, user_id=current_user.id, db=db)
    
    # Update AI Memory for quizzes
    if request.type == "quiz":
        memory = db.query(StudentAIMemory).filter(StudentAIMemory.user_id == current_user.id).first()
        if not memory:
            memory = StudentAIMemory(user_id=current_user.id)
            db.add(memory)
            db.flush()
            
        history = list(memory.learning_history or [])
        event = f"generated_{request.type}_{request.topic}"
        if event not in history:
            history.append(event)
        memory.learning_history = history
        db.commit()
        placement_engine.calculate_score(current_user.id)
        
    return result

@router.post("/resources/upload")
async def upload_resource(
    title: str = Form(...),
    type: str = Form(...),
    subject: str = Form(None),
    unit: str = Form(None),
    semester: str = Form(None),
    topic: str = Form(None),
    keywords: str = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Upload a document to be embedded and added to the learning knowledge base.
    """
    content = await file.read()
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_RESOURCE_SUFFIXES:
        raise HTTPException(status_code=400, detail="Unsupported file type. Allowed types: pdf, pptx, docx, txt, md.")
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Learning resource too large. Maximum size is 25MB.")
    resource_type = ALLOWED_RESOURCE_SUFFIXES[suffix]

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix or f".{type}") as tmp:
        tmp.write(content)
        temp_path = tmp.name

    try:
        text_content = extract_document_text(temp_path).strip() or content.decode("utf-8", errors="ignore")
    finally:
        try:
            os.unlink(temp_path)
        except OSError as exc:
            logger.debug("Could not remove temp learning file %s: %s", temp_path, exc)
    
    resource = models.LearningResource(
        title=title,
        type=resource_type,
        uploaded_by=current_user.id
    )
    db.add(resource)
    db.flush()
    
    # Ingest to Qdrant (in a real app, do this asynchronously via Celery)
    try:
        kws = [k.strip() for k in keywords.split(",")] if keywords else []
        ingest_document(
            document_id=resource.id, 
            title=title, 
            text_content=text_content, 
            source_type=type,
            subject=subject,
            unit=unit,
            semester=semester,
            topic=topic,
            keywords=kws
        )
        resource.is_processed = True
        db.commit()
        return {"status": "success", "resource_id": resource.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
