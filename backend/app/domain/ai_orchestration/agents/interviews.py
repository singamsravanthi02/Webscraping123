from app.domain.ai_orchestration.agents.base import BaseAgent
from app.domain.ai_orchestration.gateway import gateway

class InterviewAgent(BaseAgent):
    @property
    def agent_name(self) -> str:
        return "InterviewAgent"

    def process_turn(self, user_id: int, chat_session, user_message: str) -> str:
        # We delegate the actual chat.send_message to the chat_session created by Gateway
        # but we use our Gateway wrapper if we just want a single prompt
        
        response = chat_session.send_message(user_message)
        
        # Log Tokens via Gateway
        gateway._log_tokens(response.usage_metadata, user_id, "interview_chat", "gemini-1.5-flash")
        
        self.log_recommendation(
            user_id=user_id,
            action="interview_reply",
            confidence=0.95,
            reasoning="Generated interview follow-up based on user response."
        )
        return response.text
