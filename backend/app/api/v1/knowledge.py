from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional
import hashlib
import os
import shutil

from app.db.session import get_db
from app.api.dependencies.auth import get_current_active_user
from app.domain.users.models import User, UserRole
from app.domain.knowledge.models import Document, DocumentType, DocumentStatus
from app.worker.tasks import process_knowledge_document

router = APIRouter()

UPLOAD_DIR = "/tmp/spip_knowledge_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

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
    ext = file.filename.split('.')[-1].lower()
    try:
        doc_type = DocumentType(ext)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}. Allowed types: pdf, docx, pptx, txt, md.")
        
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
