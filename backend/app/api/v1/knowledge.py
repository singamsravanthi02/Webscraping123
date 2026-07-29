from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional
from sqlalchemy import func
import hashlib
import os
from pathlib import Path

from app.db.session import get_db
from app.db.session import SessionLocal
from app.api.dependencies.auth import get_current_active_user
from app.domain.users.models import User, UserRole
from app.domain.knowledge.models import Document, DocumentType, DocumentStatus
from app.domain.learning.services.rag_service import _learning_tutor_response
from app.domain.learning.services.institutional_content import sync_sreyas_course_content
from app.worker.tasks import process_knowledge_document

router = APIRouter()

UPLOAD_DIR = "/tmp/spip_knowledge_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED_UPLOADS = {
    "pdf": {"application/pdf"},
    "docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    "pptx": {
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.ms-powerpoint",
    },
    "txt": {"text/plain"},
    "md": {"text/markdown", "text/plain"},
}


def _run_sreyas_sync() -> None:
    db = SessionLocal()
    try:
        sync_sreyas_course_content(db)
    finally:
        db.close()

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    department: Optional[str] = Form(None),
    semester: Optional[str] = Form(None),
    subject: Optional[str] = Form(None),
    unit: Optional[str] = Form(None),
    academic_year: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if current_user.role not in [UserRole.ADMIN, UserRole.FACULTY]:
        raise HTTPException(status_code=403, detail="Not authorized to upload knowledge documents")
        
    # Determine document type
    ext = Path(file.filename or "").suffix.lower().lstrip(".")
    if ext not in ALLOWED_UPLOADS:
        raise HTTPException(status_code=400, detail="Unsupported file type. Allowed types: pdf, docx, pptx, txt, md.")
    try:
        doc_type = DocumentType(ext)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}. Allowed types: pdf, docx, pptx, txt, md.")

    if file.content_type not in ALLOWED_UPLOADS[ext]:
        raise HTTPException(status_code=400, detail=f"Invalid content type for .{ext} upload")
        
    # Read file and validate size (Max 50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 50MB.")
        
    file_hash = hashlib.sha256(content).hexdigest()
    
    # Check if exists
    existing = db.query(Document).filter(Document.file_hash == file_hash).first()
    if existing:
        raise HTTPException(status_code=400, detail="Document already exists in the knowledge base")
        
    # Save to temp path
    temp_path = os.path.join(UPLOAD_DIR, f"{file_hash}.{ext}")
    with open(temp_path, "wb") as f:
        f.write(content)
        
    # Create DB entry
    db_doc = Document(
        title=title,
        source="ADMIN_UPLOAD",
        department=department,
        semester=semester,
        subject=subject,
        unit=unit,
        academic_year=academic_year,
        doc_type=doc_type,
        file_hash=file_hash,
        status=DocumentStatus.PENDING,
        uploaded_by=current_user.id
    )
    
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    
    # Trigger Celery Task
    process_knowledge_document.delay(db_doc.id, temp_path)
    
    return {"message": "Document queued for processing", "document_id": db_doc.id}

@router.get("/status")
def get_documents(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    docs = db.query(Document).offset(skip).limit(limit).all()
    return docs


@router.get("/stats")
def get_knowledge_stats(db: Session = Depends(get_db)):
    doc_counts = dict(
        db.query(Document.status, func.count(Document.id))
        .group_by(Document.status)
        .all()
    )
    chunk_count = db.query(func.count()).select_from(Document).join(Document.chunks).scalar() or 0
    document_count = db.query(func.count(Document.id)).scalar() or 0
    embedding_count = chunk_count
    return {
        "documents": document_count,
        "chunks": chunk_count,
        "embeddings": embedding_count,
        "completed": doc_counts.get(DocumentStatus.COMPLETED, 0),
        "processing": doc_counts.get(DocumentStatus.PROCESSING, 0) + doc_counts.get(DocumentStatus.PENDING, 0),
        "failed": doc_counts.get(DocumentStatus.FAILED, 0),
    }


@router.get("/retrieval-debug")
def retrieval_debug(
    query: str,
    limit: int = 5,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in [UserRole.ADMIN, UserRole.FACULTY]:
        raise HTTPException(status_code=403, detail="Not authorized to inspect retrieval debug data")

    return _learning_tutor_response(query, [], None, current_user.id, db, limit=max(1, min(limit, 10)))


@router.post("/sreyas/sync")
def sync_sreyas_content(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role not in [UserRole.ADMIN, UserRole.FACULTY]:
        raise HTTPException(status_code=403, detail="Not authorized to sync institutional learning content")

    background_tasks.add_task(_run_sreyas_sync)
    return {"message": "Sreyas course content sync started"}
