from app.domain.ai_orchestration.agents.base import BaseAgent
from app.domain.ai_orchestration.gateway import gateway
from app.domain.ai_orchestration.prompts import interview_turn_prompt, PROMPT_VERSION_INTERVIEW_TURN

class InterviewAgent(BaseAgent):
    @property
    def agent_name(self) -> str:
        return "InterviewAgent"

    def process_turn(self, user_id: int, system_prompt: str, chat_history: list, user_message: str) -> str:
        prompt = interview_turn_prompt(system_prompt, chat_history, user_message)
        response = gateway.generate_content(
            prompt,
            user_id=user_id,
            feature="interview_chat",
            prompt_version=PROMPT_VERSION_INTERVIEW_TURN,
        )
        self.log_recommendation(
            user_id=user_id,
            action="interview_reply",
            confidence=0.95,
            reasoning="Generated interview follow-up based on user response."
        )
        return response
