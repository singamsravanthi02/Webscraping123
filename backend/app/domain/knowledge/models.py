from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
import enum
from app.db.base import Base, AuditMixin

class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"

class DocumentType(str, enum.Enum):
    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    TXT = "txt"
    MD = "md"
    WEBPAGE = "webpage"

class LearningResourceType(str, enum.Enum):
    FLASHCARD = "flashcard"
    REVISION_NOTE = "revision_note"
    CONCEPT_SUMMARY = "concept_summary"
    CHEAT_SHEET = "cheat_sheet"
    MIND_MAP = "mind_map"

class Document(Base, AuditMixin):
    __tablename__ = "knowledge_documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    url = Column(String, nullable=True) # Source URL if scraped
    source = Column(String, index=True, nullable=False) # e.g., 'SREYAS', 'JNTUH', 'ADMIN_UPLOAD'
    
    # Academic Metadata
    department = Column(String, nullable=True)
    semester = Column(String, nullable=True)
    subject = Column(String, nullable=True)
    unit = Column(String, nullable=True)
    module = Column(String, nullable=True)
    academic_year = Column(String, nullable=True)
    
    keywords = Column(JSONB, default=lambda: [])
    language = Column(String, default="en")
    version = Column(Integer, default=1)
    doc_type = Column(Enum(DocumentType), nullable=False)
    
    # Processing Metadata
    file_hash = Column(String, unique=True, index=True, nullable=False) # For deduplication
    status = Column(Enum(DocumentStatus), default=DocumentStatus.PENDING, nullable=False)
    error_message = Column(Text, nullable=True)
    
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete")
    resources = relationship("GeneratedResource", back_populates="document", cascade="all, delete")

class DocumentChunk(Base):
    __tablename__ = "knowledge_chunks"

    id = Column(String, primary_key=True) # Using UUID string for direct Qdrant mapping
    document_id = Column(Integer, ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    
    heading = Column(String, nullable=True)
    page_number = Column(Integer, nullable=True)
    section = Column(String, nullable=True)
    chunk_index = Column(Integer, nullable=False)
    
    prev_chunk_id = Column(String, nullable=True)
    next_chunk_id = Column(String, nullable=True)
    
    char_count = Column(Integer, default=0)
    token_count = Column(Integer, default=0)
    
    document = relationship("Document", back_populates="chunks")

class GeneratedResource(Base, AuditMixin):
    __tablename__ = "knowledge_generated_resources"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    
    resource_type = Column(Enum(LearningResourceType), nullable=False)
    content = Column(JSONB, nullable=False) # e.g., list of flashcards, or markdown text
    
    topic = Column(String, nullable=True)
    tags = Column(JSONB, default=lambda: [])
    
    document = relationship("Document", back_populates="resources")
