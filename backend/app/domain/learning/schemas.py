from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Any
from datetime import datetime
from .models import MessageRole, ResourceType, ModuleStatus

class LearningMessageBase(BaseModel):
    role: MessageRole
    content: str
    citations: Optional[List[dict]] = None

class LearningMessageCreate(LearningMessageBase):
    model_config = ConfigDict(extra="forbid")

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


class LearningRoadmapCreate(BaseModel):
    title: str
    subject: Optional[str] = None
    difficulty: Optional[str] = None
    estimated_hours: Optional[float] = None


class LearningModuleSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    roadmap_id: int
    title: str
    order: int
    summary: Optional[str] = None
    estimated_minutes: int
    status: ModuleStatus
    completed: bool = False
    completed_at: Optional[datetime] = None
    time_spent: int = 0
    progress_percent: float = 0.0
    source_chips: List[str] = Field(default_factory=list)


class LearningRoadmapResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    title_key: str
    subject: Optional[str] = None
    difficulty: Optional[str] = None
    estimated_hours: float = 0
    description: Optional[str] = None
    created_by_ai: bool = True
    source_chips: List[str] = Field(default_factory=list)
    retrieved_context: List[dict] = Field(default_factory=list)
    created_at: datetime
    modules: List[LearningModuleSummaryResponse] = Field(default_factory=list)
    completed_modules: int = 0
    total_modules: int = 0
    completion_percent: float = 0.0


class LearningRoadmapDetailResponse(LearningRoadmapResponse):
    pass


class LearningModuleDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    roadmap_id: int
    roadmap_title: str
    roadmap_subject: Optional[str] = None
    roadmap_difficulty: Optional[str] = None
    title: str
    order: int
    summary: Optional[str] = None
    estimated_minutes: int
    status: ModuleStatus
    completed: bool = False
    completed_at: Optional[datetime] = None
    time_spent: int = 0
    progress_percent: float = 0.0
    theory: Optional[str] = None
    institutional_notes: Optional[str] = None
    important_questions: List[str] = Field(default_factory=list)
    previous_year_questions: List[str] = Field(default_factory=list)
    examples: List[str] = Field(default_factory=list)
    diagrams: List[str] = Field(default_factory=list)
    practice_quiz: List[dict] = Field(default_factory=list)
    flashcards: List[dict] = Field(default_factory=list)
    revision_notes: Optional[str] = None
    resources: List[dict] = Field(default_factory=list)
    source_chips: List[str] = Field(default_factory=list)
    retrieved_chunks: List[dict] = Field(default_factory=list)


class LearningModuleChatRequest(BaseModel):
    content: str


class LearningModuleCompleteRequest(BaseModel):
    time_spent: int = 0
