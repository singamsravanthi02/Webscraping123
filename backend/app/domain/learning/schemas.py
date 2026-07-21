from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Any
from datetime import datetime
from .models import MessageRole, ResourceType

class LearningMessageBase(BaseModel):
    role: MessageRole
    content: str
    citations: Optional[List[dict]] = None

class LearningMessageCreate(LearningMessageBase):
    ...

class LearningMessageResponse(LearningMessageBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime

class LearningSessionCreate(BaseModel):
    title: str
    subject: Optional[str] = None

class LearningSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    subject: Optional[str] = None
    is_active: bool
    created_at: datetime

class LearningSessionDetailResponse(LearningSessionResponse):
    messages: List[LearningMessageResponse] = Field(default_factory=list)

class ChatMessageRequest(BaseModel):
    content: str

class GenerateRequest(BaseModel):
    type: str # "quiz", "summary", "flashcards"
    topic: Optional[str] = None # Optional specific topic, otherwise uses recent chat context
