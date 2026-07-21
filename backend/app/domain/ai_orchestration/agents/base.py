from abc import ABC, abstractmethod
from typing import Any, Type, TypeVar
from pydantic import BaseModel
from app.domain.ai_orchestration.gateway import gateway
from app.domain.ai_orchestration.models import AIRecommendationLog
from app.db.session import SessionLocal

T = TypeVar("T", bound=BaseModel)

class BaseAgent(ABC):
    """
    Abstract base class for all AI Agents.
    Forces implementation of explainable actions and delegates LLM calls to the Gateway.
    """
    
    @property
    @abstractmethod
    def agent_name(self) -> str:
        pass

    def run_inference(self, prompt: str, user_id: int, use_pro: bool = False) -> str:
        """
        Calls the centralized AI Gateway.
        """
        return gateway.generate_content(
            prompt=prompt,
            use_pro=use_pro,
            user_id=user_id,
            feature=self.agent_name
        )

    def run_structured_inference(self, prompt: str, schema: Type[T], user_id: int, use_pro: bool = False) -> T:
        return gateway.generate_structured_response(
            prompt=prompt,
            schema_model=schema,
            use_pro=use_pro,
            user_id=user_id,
            feature=self.agent_name,
        )

    def log_recommendation(
        self, 
        user_id: int, 
        action: str, 
        confidence: float, 
        reasoning: str,
        evidence: list = None,
        sources: list = None,
        next_actions: list = None
    ):
        """
        Explainable AI persistence. Every major decision made by an agent must be logged.
        """
        db = SessionLocal()
        try:
            log = AIRecommendationLog(
                user_id=user_id,
                agent_name=self.agent_name,
                action=action,
                confidence_score=confidence,
                reasoning_summary=reasoning,
                supporting_evidence=evidence or [],
                source_documents=sources or [],
                suggested_next_actions=next_actions or []
            )
            db.add(log)
            db.commit()
        finally:
            db.close()
