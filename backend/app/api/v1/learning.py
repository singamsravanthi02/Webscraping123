from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
import os

from app.db.session import get_db
from app.api.dependencies.auth import get_current_active_user
from app.domain.users.models import User
from app.domain.learning import schemas, models
from app.domain.learning.services.rag_service import chat_with_context, generate_study_material
from app.domain.learning.services.qdrant_service import ingest_document
from app.domain.ai_orchestration.models import StudentAIMemory
from app.domain.ai_orchestration.placement_engine import placement_engine
import json

router = APIRouter()

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
    ai_response = await chat_with_context(request.content, history_dicts, subject=session.subject, user_id=current_user.id)
    
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
        pass # Ignore parse errors for memory
        
    return ai_msg

@router.post("/generate")
async def generate_material(request: schemas.GenerateRequest, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """
    Generate study materials (quiz, summary, flashcards) based on a topic.
    Returns plain text (or JSON string) based on generation.
    """
    if not request.topic:
        raise HTTPException(status_code=400, detail="Topic is required")
        
    result = await generate_study_material(request.type, request.topic, user_id=current_user.id)
    
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
        
    return {"result": result}

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
    Upload a document (PDF, Text) to be embedded and added to the learning knowledge base.
    """
    content = await file.read()
    text_content = ""
    
    if type == "pdf":
        import pypdf
        import io
        pdf_reader = pypdf.PdfReader(io.BytesIO(content))
        for page in pdf_reader.pages:
            text_content += page.extract_text() + "\n"
    else:
        # Fallback to text reading
        text_content = content.decode('utf-8', errors='ignore')
        
    resource = models.LearningResource(
        title=title,
        type=models.ResourceType(type.lower()),
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
