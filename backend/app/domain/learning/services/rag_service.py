import json
import logging
from typing import List, Dict, Any
from .qdrant_service import search_documents
from app.domain.ai_orchestration.gateway import gateway
from app.domain.ai_orchestration.agents.rag import RAGAgent
from app.domain.ai_orchestration.prompts import study_material_prompt, PROMPT_VERSION_STUDY_MATERIAL
from app.domain.ai_orchestration.schemas import StudyMaterialSchema

agent = RAGAgent()
logger = logging.getLogger(__name__)

async def chat_with_context(query: str, chat_history: List[Dict[str, str]], subject: str = None, user_id: int = None) -> Dict[str, Any]:
    """
    RAG-enabled chat. Fetches context, prompts Gemini, and parses out the response + citations.
    """
    # 1. Retrieve Context
    search_query = query
    if subject:
        search_query = f"{subject}: {query}"
        
    try:
        retrieved_docs = search_documents(search_query, limit=4)
    except Exception as exc:
        logger.warning("Error retrieving context: %s", exc)
        retrieved_docs = []
    
    context_str = ""
    citations_meta = []
    
    for i, doc in enumerate(retrieved_docs):
        citation_id = f"[{i+1}]"
        context_str += f"{citation_id} Source: {doc['title']}\nContent: {doc['text']}\n\n"
        citations_meta.append({
            "id": i+1,
            "title": doc['title'],
            "type": doc['source_type']
        })

    history_text = "\n".join(f"{msg['role']}: {msg['content']}" for msg in chat_history)
        
    try:
        if user_id:
            response = agent.process_rag_chat(user_id, query, context_str, citations_meta, history_text)
            response_text = json.dumps(response)
        else:
            response_text = json.dumps(agent.process_rag_chat(None, query, context_str, citations_meta, history_text))

        return {
            "content": response_text,
            "citations": citations_meta if retrieved_docs else []
        }
    except Exception as e:
        logger.warning("Error generating AI response: %s", e)
        error_resp = {
            "concise_explanation": "I'm sorry, I'm having trouble processing that right now. Please try again.",
            "confidence_level": "Low",
            "related_topics": []
        }
        return {
            "content": json.dumps(error_resp),
            "citations": []
        }

async def generate_study_material(material_type: str, topic: str, chat_history: List[Dict[str, str]] = None, user_id: int = None) -> Dict[str, Any]:
    """
    Generates specific study materials (quiz, summary, flashcards) based on a topic or recent chat context.
    """
    try:
        context_docs = search_documents(topic, limit=5)
    except Exception as exc:
        logger.warning("Error retrieving study context: %s", exc)
        context_docs = []
    context_str = "\n".join([f"- {doc['text']}" for doc in context_docs])
    prompt = study_material_prompt(material_type, topic, context_str)
    if prompt == "Invalid material type requested.":
        return {"material_type": material_type, "topic": topic, "summary_markdown": "", "flashcards": [], "questions": [], "key_points": [], "cheat_sheet": ""}

    try:
        response = gateway.generate_structured_response(
            prompt,
            StudyMaterialSchema,
            use_pro=False,
            user_id=user_id,
            feature=f"generate_{material_type}",
            prompt_version=PROMPT_VERSION_STUDY_MATERIAL,
        )
        return response.model_dump()
    except Exception as e:
        logger.warning("Error generating material: %s", e)
        return {"material_type": material_type, "topic": topic, "summary_markdown": "", "flashcards": [], "questions": [], "key_points": [], "cheat_sheet": ""}
