from app.domain.ai_orchestration.agents.base import BaseAgent
from app.domain.ai_orchestration.prompts import resume_analysis_prompt
from app.domain.ai_orchestration.schemas import ResumeAnalysisSchema

class ResumeAgent(BaseAgent):
    @property
    def agent_name(self) -> str:
        return "ResumeAnalysisAgent"

    def analyze_resume(self, user_id: int, resume_text: str) -> dict:
        response = self.run_structured_inference(
            resume_analysis_prompt(resume_text),
            ResumeAnalysisSchema,
            user_id,
            use_pro=True,
        )

        self.log_recommendation(
            user_id=user_id,
            action="resume_analysis",
            confidence=0.9,
            reasoning="Extracted entities using structured Gemini output.",
            next_actions=response.improvement_suggestions,
        )
        return response.model_dump()
