import json
import logging
import time
from datetime import datetime, timezone
from typing import List, Dict, Any

from sqlalchemy.orm import Session

from app.domain.audit_logs.models import AITokenUsageLog
from .qdrant_service import search_documents
from app.domain.ai_orchestration.gateway import gateway
from app.domain.ai_orchestration.prompts import (
    PROMPT_VERSION_LEARNING_HYBRID,
    PROMPT_VERSION_STUDY_MATERIAL,
    hybrid_learning_prompt,
    study_material_prompt,
)
from app.domain.ai_orchestration.schemas import LearningTutorAnswerSchema, StudyMaterialSchema
logger = logging.getLogger(__name__)
LEARNING_RAG_CONFIDENCE_THRESHOLD = 0.65
LEARNING_HISTORY_LIMIT = 4
LEARNING_CONTEXT_CHARS = 900


def _retrieval_confidence(docs: List[Dict[str, Any]]) -> float:
    scores = [max(0.0, min(1.0, float(doc.get("score") or 0.0))) for doc in docs if doc.get("score") is not None]
    if not scores:
        return 0.0
    top_scores = sorted(scores, reverse=True)[:3]
    blended = (top_scores[0] * 0.7) + ((sum(top_scores) / len(top_scores)) * 0.3)
    return round(max(0.0, min(1.0, blended)), 4)


def _build_context_block(docs: List[Dict[str, Any]]) -> tuple[str, List[Dict[str, Any]]]:
    context_lines: List[str] = []
    citations_meta: List[Dict[str, Any]] = []
    for index, doc in enumerate(docs, start=1):
        title = doc.get("title") or "Unknown"
        chunk_number = doc.get("chunk_number") or (int(doc.get("chunk_index") or 0) + 1)
        snippet = (doc.get("text") or "")[:LEARNING_CONTEXT_CHARS]
        context_lines.append(
            f"[{index}] Source: {title}\n"
            f"Content: {snippet}\n"
        )
        citations_meta.append(
            {
                "id": index,
                "title": title,
                "type": doc.get("source_type") or "unknown",
                "document": doc.get("metadata", {}).get("title") or title,
                "source": doc.get("metadata", {}).get("source") or doc.get("source_type") or "unknown",
                "page": doc.get("page_number"),
                "chunk_number": chunk_number,
                "chunk_index": doc.get("chunk_index"),
                "similarity_score": round(float(doc.get("score") or 0.0), 4),
                "embedding_distance": round(float(doc.get("embedding_distance") or 0.0), 4),
                "metadata": doc.get("metadata") or {},
            }
    )
    return "\n".join(context_lines).strip(), citations_meta


def _history_excerpt(chat_history: List[Dict[str, str]], limit: int = LEARNING_HISTORY_LIMIT) -> str:
    if not chat_history:
        return ""

    recent_messages = chat_history[-limit:]
    lines: List[str] = []
    for message in recent_messages:
        role = message.get("role", "user")
        content = " ".join((message.get("content") or "").split())
        if len(content) > 500:
            content = f"{content[:500].rstrip()}…"
        lines.append(f"{role}: {content}")
    return "\n".join(lines)

def _build_citations(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    citations: List[Dict[str, Any]] = []
    for index, doc in enumerate(docs, start=1):
        metadata = doc.get("metadata") or {}
        citations.append(
            {
                "id": index,
                "title": doc.get("title") or metadata.get("title") or "Unknown",
                "document": metadata.get("title") or doc.get("title") or "Unknown",
                "source": metadata.get("source") or doc.get("source_type") or "unknown",
                "page": doc.get("page_number"),
                "chunk_number": doc.get("chunk_number") or (int(doc.get("chunk_index") or 0) + 1),
                "chunk_index": doc.get("chunk_index"),
                "embedding_id": doc.get("embedding_id"),
                "similarity_score": round(float(doc.get("score") or 0.0), 4),
                "embedding_distance": round(float(doc.get("embedding_distance") or 0.0), 4),
                "metadata": {
                    "document_id": doc.get("document_id"),
                    "subject": metadata.get("subject"),
                    "department": metadata.get("department"),
                    "semester": metadata.get("semester"),
                    "unit": metadata.get("unit"),
                    "module": metadata.get("module"),
                    "url": metadata.get("url"),
                    "keywords": list(metadata.get("keywords") or []),
                    "source_page_url": doc.get("source_page_url"),
                    "resource_url": doc.get("resource_url"),
                    "google_drive_file_id": doc.get("google_drive_file_id"),
                    "document_title": doc.get("document_title"),
                    "resource_label": doc.get("resource_label"),
                    "ingestion_timestamp": doc.get("ingestion_timestamp"),
                },
            }
        )
    return citations


def _token_usage_since(db: Session | None, user_id: int | None, started_at: datetime, feature: str) -> Dict[str, int]:
    if db is None or user_id is None:
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    logs = (
        db.query(AITokenUsageLog)
        .filter(
            AITokenUsageLog.user_id == user_id,
            AITokenUsageLog.created_at >= started_at,
            AITokenUsageLog.feature.in_([feature, "offline_chat"]),
        )
        .order_by(AITokenUsageLog.created_at.asc())
        .all()
    )
    if not logs:
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    return {
        "prompt_tokens": sum(int(log.prompt_tokens or 0) for log in logs),
        "completion_tokens": sum(int(log.completion_tokens or 0) for log in logs),
        "total_tokens": sum(int(log.total_tokens or 0) for log in logs),
    }


def _learning_tutor_response(
    query: str,
    chat_history: List[Dict[str, str]],
    subject: str | None,
    user_id: int | None,
    db: Session | None,
    limit: int = 4,
) -> Dict[str, Any]:
    started_at = datetime.now(timezone.utc)
    search_start = time.perf_counter()
    search_query = query
    try:
        retrieved_docs = search_documents(search_query, limit=max(1, min(limit, 10)), db=db)
    except Exception as exc:
        logger.warning("Error retrieving learning context: %s", exc)
        retrieved_docs = []
    retrieval_latency_ms = round((time.perf_counter() - search_start) * 1000, 1)

    retrieval_confidence = _retrieval_confidence(retrieved_docs)
    use_rag = bool(retrieved_docs) and retrieval_confidence >= LEARNING_RAG_CONFIDENCE_THRESHOLD
    context_str = ""
    citations_meta: List[Dict[str, Any]] = []
    if use_rag:
        context_str, citations_meta = _build_context_block(retrieved_docs)

    history_text = _history_excerpt(chat_history)
    prompt = hybrid_learning_prompt(
        query=query,
        context_str=context_str,
        history_text=history_text,
        subject=subject,
        use_rag=use_rag,
        retrieval_confidence=retrieval_confidence,
    )

    generation_start = time.perf_counter()
    try:
        response = gateway.generate_structured_response(
            prompt,
            LearningTutorAnswerSchema,
            use_pro=False,
            user_id=user_id,
            feature="learning_chat",
            prompt_version=PROMPT_VERSION_LEARNING_HYBRID,
        )
        response_payload = response.model_dump()
    except Exception as exc:
        logger.warning("Error generating learning response: %s", exc)
        response_payload = LearningTutorAnswerSchema(
            concise_explanation="I'm sorry, I can't generate a grounded answer right now. Please try again.",
            confidence_level="Low",
            answer_mode="general",
            used_rag=False,
            used_gemini=True,
            hybrid=False,
            retrieval_confidence=retrieval_confidence,
            institutional_information="No institutional sources were used. Answered using Gemini.",
            general_explanation="I couldn't finish the response, but you can retry the question.",
        ).model_dump()
    generation_latency_ms = round((time.perf_counter() - generation_start) * 1000, 1)
    token_usage = _token_usage_since(db, user_id, started_at, "learning_chat")
    latency_ms = round((time.perf_counter() - search_start) * 1000, 1)
    decision = "rag+gemini" if use_rag else "gemini-only"

    return {
        "content": json.dumps(response_payload, ensure_ascii=False),
        "answer": response_payload,
        "query": query,
        "citations": citations_meta if use_rag else [],
        "results": [
            {
                **doc,
                "snippet": (doc.get("text") or "")[:280],
                "retrieved_at": started_at.isoformat(),
            }
            for doc in retrieved_docs
        ],
        "retrieval_confidence": retrieval_confidence,
        "used_rag": use_rag,
        "used_gemini": True,
        "hybrid": use_rag,
        "decision": decision,
        "prompt_sent": prompt,
        "final_context": context_str if use_rag else "",
        "retrieval_latency_ms": retrieval_latency_ms,
        "generation_latency_ms": generation_latency_ms,
        "latency_ms": latency_ms,
        "prompt_tokens": token_usage["prompt_tokens"],
        "completion_tokens": token_usage["completion_tokens"],
        "total_tokens": token_usage["total_tokens"],
        "retrieved_at": started_at.isoformat(),
    }


async def chat_with_context(
    query: str,
    chat_history: List[Dict[str, str]],
    subject: str = None,
    user_id: int = None,
    db: Session | None = None,
) -> Dict[str, Any]:
    """
    RAG-enabled chat. Fetches context, prompts Gemini, and parses out the response + citations.
    """
    response = _learning_tutor_response(query, chat_history, subject, user_id, db)
    return {
        "content": response["content"],
        "citations": response["citations"],
    }

async def generate_study_material(
    material_type: str,
    topic: str,
    chat_history: List[Dict[str, str]] = None,
    user_id: int = None,
    db: Session | None = None,
) -> Dict[str, Any]:
    """
    Generates specific study materials (quiz, summary, flashcards) based on a topic or recent chat context.
    """
    try:
        context_docs = search_documents(topic, limit=5, db=db)
    except Exception as exc:
        logger.warning("Error retrieving study context: %s", exc)
        context_docs = []
    context_str = "\n".join([f"- {(doc.get('text') or '')[:LEARNING_CONTEXT_CHARS]}" for doc in context_docs[:3]])
    prompt = study_material_prompt(material_type, topic, context_str)
    if prompt == "Invalid material type requested.":
        return {
            "result": {
                "material_type": material_type,
                "topic": topic,
                "summary_markdown": "",
                "flashcards": [],
                "questions": [],
                "key_points": [],
                "cheat_sheet": "",
            },
            "citations": _build_citations(context_docs),
        }

    try:
        response = gateway.generate_structured_response(
            prompt,
            StudyMaterialSchema,
            use_pro=False,
            user_id=user_id,
            feature=f"generate_{material_type}",
            prompt_version=PROMPT_VERSION_STUDY_MATERIAL,
        )
        result = response.model_dump()
        if not context_docs:
            key_points = list(result.get("key_points") or [])
            if "No institutional sources were used. Answered using Gemini." not in key_points:
                key_points.insert(0, "No institutional sources were used. Answered using Gemini.")
            result["key_points"] = key_points
        return {
            "result": result,
            "citations": _build_citations(context_docs),
        }
    except Exception as e:
        logger.warning("Error generating material: %s", e)
        return {
            "result": {
                "material_type": material_type,
                "topic": topic,
                "summary_markdown": "",
                "flashcards": [],
                "questions": [],
                "key_points": [],
                "cheat_sheet": "",
            },
            "citations": _build_citations(context_docs),
        }
