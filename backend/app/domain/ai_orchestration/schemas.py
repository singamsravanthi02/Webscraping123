from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ResumeAnalysisSchema(BaseModel):
    technical_skills: List[str] = Field(default_factory=list)
    soft_skills: List[str] = Field(default_factory=list)
    years_of_experience: float = 0
    education_level: str = ""
    projects: List[str] = Field(default_factory=list)
    overall_score: float = 0
    improvement_suggestions: List[str] = Field(default_factory=list)


class JobQuerySchema(BaseModel):
    queries: List[str] = Field(default_factory=list)


class JobExtractionSchema(BaseModel):
    skills: List[str] = Field(default_factory=list)
    eligibility: str = "Not specified"
    ai_summary: str = "A great opportunity."


class InterviewEvaluationSchema(BaseModel):
    confidence_score: float = 0
    communication_score: float = 0
    technical_score: float = 0
    problem_solving_score: float = 0
    overall_grade: float = 0
    feedback_summary: str = ""
    suggestions: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    recommended_topics: List[str] = Field(default_factory=list)
    learning_plan: str = ""
    placement_readiness_contribution: float = 0


class RAGAnswerSchema(BaseModel):
    concise_explanation: str = ""
    confidence_level: str = "Low"
    related_topics: List[str] = Field(default_factory=list)
    suggested_quiz: str = ""
    suggested_flashcards: str = ""
    suggested_revision_notes: str = ""


class FlashcardSchema(BaseModel):
    front: str = ""
    back: str = ""


class StudyQuizQuestionSchema(BaseModel):
    question: str = ""
    options: List[str] = Field(default_factory=list)
    answer_index: int = 0
    explanation: str = ""


class StudyMaterialSchema(BaseModel):
    material_type: str = ""
    topic: str = ""
    summary_markdown: str = ""
    flashcards: List[FlashcardSchema] = Field(default_factory=list)
    questions: List[StudyQuizQuestionSchema] = Field(default_factory=list)
    key_points: List[str] = Field(default_factory=list)
    cheat_sheet: str = ""


class LearningResourceSchema(BaseModel):
    flashcards: List[FlashcardSchema] = Field(default_factory=list)
    revision_notes: str = ""
    cheat_sheet: str = ""


class QuestionItemSchema(BaseModel):
    topic: str = ""
    subject: str = ""
    type: str = "mcq"
    difficulty: int = 5
    interview_difficulty: int = 5
    company_difficulty: int = 5
    bloom_level: str = "Apply"
    content: str = ""
    options: Optional[Dict[str, str]] = None
    correct_answer: str = ""
    detailed_explanation: str = ""
    hints: List[str] = Field(default_factory=list)
    common_mistakes: List[str] = Field(default_factory=list)
    company_tags: List[str] = Field(default_factory=list)
    placement_relevance: int = 5
    estimated_time: int = 60
    marks: float = 1.0


class QuestionListSchema(BaseModel):
    questions: List[QuestionItemSchema] = Field(default_factory=list)
