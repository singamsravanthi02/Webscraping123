from app.domain.ai_orchestration.agents.base import BaseAgent
from app.domain.ai_orchestration.gateway import gateway
from app.domain.ai_orchestration.prompts import rag_prompt, PROMPT_VERSION_RAG
from app.domain.ai_orchestration.schemas import RAGAnswerSchema

class RAGAgent(BaseAgent):
    @property
    def agent_name(self) -> str:
        return "RAGRetrievalAgent"

    def process_rag_chat(self, user_id: int | None, query: str, context_str: str, citations: list, history_text: str = "") -> dict:
        response = gateway.generate_structured_response(
            rag_prompt(query, context_str, history_text),
            RAGAnswerSchema,
            use_pro=False,
            user_id=user_id,
            feature="rag_chat",
            prompt_version=PROMPT_VERSION_RAG,
        )

        # Explainable AI log
        if user_id is not None:
            self.log_recommendation(
                user_id=user_id,
                action="rag_answer",
                confidence=0.9,
                reasoning="Synthesized answer based on retrieved vector embeddings.",
                sources=[c["title"] for c in citations]
            )
        return response.model_dump()
