from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from .models import InterviewType, InterviewStatus, MessageRole

class InterviewMessageBase(BaseModel):
    role: MessageRole
    content: str

class InterviewMessageCreate(InterviewMessageBase):
    pass

class InterviewMessageResponse(InterviewMessageBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class InterviewResultBase(BaseModel):
    confidence_score: Optional[float] = None
    communication_score: Optional[float] = None
    technical_score: Optional[float] = None
    overall_grade: Optional[float] = None
    feedback_summary: Optional[str] = None
    suggestions: Optional[List[str]] = None

class InterviewResultResponse(InterviewResultBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class InterviewCreate(BaseModel):
    title: str
    type: InterviewType
    resume_text: Optional[str] = None
    job_description: Optional[str] = None

class InterviewResponse(BaseModel):
    id: int
    user_id: int
    title: str
    type: InterviewType
    status: InterviewStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class InterviewDetailResponse(InterviewResponse):
    messages: List[InterviewMessageResponse] = []
    result: Optional[InterviewResultResponse] = None

class ChatMessageRequest(BaseModel):
    content: str
