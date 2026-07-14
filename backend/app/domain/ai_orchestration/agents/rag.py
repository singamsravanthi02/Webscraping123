from app.domain.ai_orchestration.agents.base import BaseAgent
from app.domain.ai_orchestration.gateway import gateway

class RAGAgent(BaseAgent):
    @property
    def agent_name(self) -> str:
        return "RAGRetrievalAgent"

    def process_rag_chat(self, user_id: int, chat_session, query: str, citations: list) -> str:
        response = chat_session.send_message(query)
        
        # Log Tokens via Gateway
        gateway._log_tokens(response.usage_metadata, user_id, "rag_chat", "gemini-1.5-flash")
        
        # Explainable AI log
        self.log_recommendation(
            user_id=user_id,
            action="rag_answer",
            confidence=0.9,
            reasoning="Synthesized answer based on retrieved vector embeddings.",
            sources=[c["title"] for c in citations]
        )
        return response.text
