from app.domain.ai_orchestration.agents.base import BaseAgent
from app.domain.ai_orchestration.prompts import content_generation_prompt, question_generation_prompt
from app.domain.ai_orchestration.schemas import LearningResourceSchema, QuestionListSchema
import logging

logger = logging.getLogger(__name__)

class QuestionGenerationAgent(BaseAgent):
    @property
    def agent_name(self) -> str:
        return "QuestionGenerationAgent"

    def generate_questions(self, user_id: int, context_text: str, document_metadata: dict) -> list:
        prompt = question_generation_prompt(context_text, document_metadata)
        try:
            response = self.run_structured_inference(prompt, QuestionListSchema, user_id, use_pro=False)
            return [item.model_dump() for item in response.questions]
        except Exception as e:
            logger.error(f"Failed to parse generated questions: {e}")
            return []


class ContentGenerationAgent(BaseAgent):
    @property
    def agent_name(self) -> str:
        return "ContentGenerationAgent"

    def generate_learning_resources(self, user_id: int, context_text: str, document_metadata: dict) -> dict:
        prompt = content_generation_prompt(context_text)

        try:
            response = self.run_structured_inference(prompt, LearningResourceSchema, user_id, use_pro=False)
            return response.model_dump()
        except Exception as e:
            logger.error(f"Failed to parse generated resources: {e}")
            return {}
