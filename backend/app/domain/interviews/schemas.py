from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from .models import InterviewType, InterviewStatus, MessageRole

class InterviewMessageBase(BaseModel):
    role: MessageRole
    content: str

class InterviewMessageCreate(InterviewMessageBase):
    model_config = ConfigDict(extra="forbid")

class InterviewMessageResponse(InterviewMessageBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime

class InterviewResultBase(BaseModel):
    confidence_score: Optional[float] = None
    communication_score: Optional[float] = None
    technical_score: Optional[float] = None
    overall_grade: Optional[float] = None
    feedback_summary: Optional[str] = None
    suggestions: Optional[List[str]] = None

class InterviewResultResponse(InterviewResultBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime

class InterviewCreate(BaseModel):
    title: str
    type: InterviewType
    resume_text: Optional[str] = None
    job_description: Optional[str] = None

class InterviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    type: InterviewType
    status: InterviewStatus
    resume_text: Optional[str] = None
    job_description: Optional[str] = None
    lock_violations: List[Dict[str, Any]] = Field(default_factory=list)
    start_time: datetime
    end_time: Optional[datetime] = None
class InterviewDetailResponse(InterviewResponse):
    messages: List[InterviewMessageResponse] = Field(default_factory=list)
    result: Optional[InterviewResultResponse] = None


class InterviewLockViolationCreate(BaseModel):
    violation_type: str
    details: Optional[str] = None

class ChatMessageRequest(BaseModel):
    content: str


class CodeRunRequest(BaseModel):
    language: str
    code: str = Field(min_length=1)
    stdin: Optional[str] = ""


class CodeRunResponse(BaseModel):
    language: str
    compiler: Optional[str] = None
    success: bool = False
    status: str = ""
    stdout: str = ""
    stderr: str = ""
    compiler_output: str = ""
    compiler_error: str = ""
    program_output: str = ""
    program_error: str = ""
    message: Optional[str] = None
