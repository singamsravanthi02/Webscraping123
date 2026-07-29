from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session, selectinload

from app.domain.ai_orchestration.gateway import gateway
from app.domain.ai_orchestration.prompts import (
    PROMPT_VERSION_LEARNING_MODULE,
    PROMPT_VERSION_LEARNING_ROADMAP,
    learning_module_prompt,
    learning_roadmap_prompt,
)
from app.domain.ai_orchestration.schemas import LearningModuleContentSchema, LearningRoadmapSchema
from app.domain.learning.models import LearningModule, LearningProgress, LearningRoadmap, ModuleStatus
from app.domain.learning.services.rag_service import chat_with_context
from app.domain.learning.services.qdrant_service import search_documents

logger = logging.getLogger(__name__)
LEARNING_CONTEXT_CHARS = 900


def normalize_title_key(title: str, subject: str | None = None) -> str:
    raw = f"{title or ''} {subject or ''}".strip().lower()
    raw = re.sub(r"[^a-z0-9]+", "-", raw)
    return raw.strip("-")[:180] or "learning-roadmap"


def _serialize_docs(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "id": index + 1,
            "title": doc.get("title") or "Unknown",
            "type": doc.get("source_type") or "unknown",
            "score": round(float(doc.get("score") or 0), 4),
            "embedding_distance": round(float(doc.get("embedding_distance") or 0), 4),
            "document_id": doc.get("document_id"),
            "chunk_index": doc.get("chunk_index"),
            "chunk_number": doc.get("chunk_number"),
            "page_number": doc.get("page_number"),
            "metadata": doc.get("metadata") or {},
        }
        for index, doc in enumerate(docs)
    ]


def build_learning_context(
    title: str,
    subject: str | None = None,
    limit: int = 4,
    db: Session | None = None,
) -> tuple[str, List[Dict[str, Any]]]:
    query = " ".join(part for part in [title, subject] if part)
    try:
        docs = search_documents(query or title, limit=limit, db=db)
    except Exception as exc:
        logger.warning("Learning context retrieval failed for %s: %s", title, exc)
        docs = []

    context_lines = []
    for index, doc in enumerate(docs, start=1):
        page_number = doc.get("page_number")
        chunk_number = doc.get("chunk_number") or (int(doc.get("chunk_index") or 0) + 1)
        snippet = (doc.get("text") or "")[:LEARNING_CONTEXT_CHARS]
        context_lines.append(
            f"[{index}] {doc.get('title') or 'Unknown'} ({doc.get('source_type') or 'unknown'})"
            f" | page {page_number if page_number is not None else 'unknown'} | chunk {chunk_number}\n"
            f"{snippet}\n"
        )
    return "\n".join(context_lines).strip(), _serialize_docs(docs)


def _attach_progress(
    db: Session,
    module: LearningModule,
    student_id: int,
) -> Dict[str, Any]:
    progress = (
        db.query(LearningProgress)
        .filter(LearningProgress.student_id == student_id, LearningProgress.module_id == module.id)
        .first()
    )
    return {
        "completed": bool(progress.completed) if progress else False,
        "completed_at": progress.completed_at if progress else None,
        "time_spent": int(progress.time_spent or 0) if progress else 0,
        "progress_percent": float(progress.progress_percent or 0.0) if progress else 0.0,
    }


def _module_response_payload(db: Session, module: LearningModule, student_id: int) -> Dict[str, Any]:
    progress = _attach_progress(db, module, student_id)
    return {
        "id": module.id,
        "roadmap_id": module.roadmap_id,
        "roadmap_title": module.roadmap.title if module.roadmap else "",
        "roadmap_subject": module.roadmap.subject if module.roadmap else None,
        "roadmap_difficulty": module.roadmap.difficulty if module.roadmap else None,
        "title": module.title,
        "order": module.order,
        "summary": module.summary,
        "estimated_minutes": module.estimated_minutes,
        "status": module.status,
        "theory": module.theory,
        "institutional_notes": module.institutional_notes,
        "important_questions": list(module.important_questions or []),
        "previous_year_questions": list(module.previous_year_questions or []),
        "examples": list(module.examples or []),
        "diagrams": list(module.diagrams or []),
        "practice_quiz": list(module.practice_quiz or []),
        "flashcards": list(module.flashcards or []),
        "revision_notes": module.revision_notes,
        "resources": list(module.resources or []),
        "source_chips": list(module.source_chips or []),
        "retrieved_chunks": list(module.retrieved_chunks or []),
        **progress,
    }


def _roadmap_response_payload(db: Session, roadmap: LearningRoadmap, student_id: int) -> Dict[str, Any]:
    module_rows = []
    completed_modules = 0
    total_minutes = 0
    for module in roadmap.modules:
        progress = _attach_progress(db, module, student_id)
        if progress["completed"]:
            completed_modules += 1
        total_minutes += int(module.estimated_minutes or 0)
        module_rows.append(
            {
                "id": module.id,
                "roadmap_id": module.roadmap_id,
                "title": module.title,
                "order": module.order,
                "summary": module.summary,
                "estimated_minutes": module.estimated_minutes,
                "status": module.status,
                **progress,
                "source_chips": list(module.source_chips or []),
            }
        )

    total_modules = len(module_rows)
    completion_percent = round((completed_modules / total_modules) * 100, 1) if total_modules else 0.0
    return {
        "id": roadmap.id,
        "user_id": roadmap.user_id,
        "title": roadmap.title,
        "title_key": roadmap.title_key,
        "subject": roadmap.subject,
        "difficulty": roadmap.difficulty,
        "estimated_hours": float(roadmap.estimated_hours or 0),
        "description": roadmap.description,
        "created_by_ai": bool(roadmap.created_by_ai),
        "source_chips": list(roadmap.source_chips or []),
        "retrieved_context": list(roadmap.retrieved_context or []),
        "created_at": roadmap.created_at,
        "modules": module_rows,
        "completed_modules": completed_modules,
        "total_modules": total_modules,
        "completion_percent": completion_percent,
        "estimated_minutes_remaining": max(total_minutes - (completed_modules * 15), 0),
    }


def _safe_json_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    return []


def _store_roadmap(
    db: Session,
    *,
    user_id: int,
    request_title: str,
    subject: str | None,
    ai_data: LearningRoadmapSchema,
    retrieved_context: List[Dict[str, Any]],
) -> LearningRoadmap:
    roadmap = LearningRoadmap(
        user_id=user_id,
        title=ai_data.title or request_title,
        title_key=normalize_title_key(ai_data.title or request_title, subject or ai_data.subject),
        subject=subject or ai_data.subject or request_title,
        difficulty=ai_data.difficulty or "Intermediate",
        estimated_hours=float(ai_data.estimated_hours or 0),
        description=ai_data.description or "",
        created_by_ai=True,
        source_chips=ai_data.source_chips or ["AI Generated"],
        retrieved_context=retrieved_context,
    )
    db.add(roadmap)
    db.flush()

    for index, module_data in enumerate(ai_data.modules, start=1):
        db.add(
            LearningModule(
                roadmap_id=roadmap.id,
                title=module_data.title or f"Module {index}",
                order=index,
                summary=module_data.summary or "",
                estimated_minutes=int(module_data.estimated_minutes or 0),
                status=ModuleStatus.AVAILABLE,
                source_chips=ai_data.source_chips or ["AI Generated"],
                retrieved_chunks=retrieved_context,
            )
        )

    db.commit()
    db.refresh(roadmap)
    return roadmap


def get_or_create_roadmap(
    db: Session,
    *,
    user_id: int,
    title: str,
    subject: str | None = None,
    difficulty: str | None = None,
    estimated_hours: float | None = None,
) -> Dict[str, Any]:
    title_key = normalize_title_key(title, subject)
    roadmap = (
        db.query(LearningRoadmap)
        .options(selectinload(LearningRoadmap.modules))
        .filter(LearningRoadmap.user_id == user_id, LearningRoadmap.title_key == title_key)
        .first()
    )
    if roadmap:
        return _roadmap_response_payload(db, roadmap, user_id)

    context_str, retrieved_context = build_learning_context(title, subject, db=db)
    ai_data = gateway.generate_structured_response(
        learning_roadmap_prompt(title, subject or title, context_str, []),
        LearningRoadmapSchema,
        use_pro=False,
        user_id=user_id,
        feature="learning_roadmap",
        prompt_version=PROMPT_VERSION_LEARNING_ROADMAP,
    )

    if estimated_hours and not ai_data.estimated_hours:
        ai_data.estimated_hours = float(estimated_hours)
    if difficulty and not ai_data.difficulty:
        ai_data.difficulty = difficulty

    roadmap = _store_roadmap(
        db,
        user_id=user_id,
        request_title=title,
        subject=subject,
        ai_data=ai_data,
        retrieved_context=retrieved_context,
    )
    roadmap = (
        db.query(LearningRoadmap)
        .options(selectinload(LearningRoadmap.modules))
        .filter(LearningRoadmap.id == roadmap.id)
        .first()
    )
    return _roadmap_response_payload(db, roadmap, user_id)


def get_roadmap(db: Session, roadmap_id: int, user_id: int) -> Dict[str, Any]:
    roadmap = (
        db.query(LearningRoadmap)
        .options(selectinload(LearningRoadmap.modules))
        .filter(LearningRoadmap.id == roadmap_id, LearningRoadmap.user_id == user_id)
        .first()
    )
    if not roadmap:
        raise HTTPException(status_code=404, detail="Learning roadmap not found")
    return _roadmap_response_payload(db, roadmap, user_id)


def list_roadmaps(db: Session, user_id: int) -> List[Dict[str, Any]]:
    roadmaps = (
        db.query(LearningRoadmap)
        .options(selectinload(LearningRoadmap.modules))
        .filter(LearningRoadmap.user_id == user_id)
        .order_by(LearningRoadmap.created_at.desc())
        .all()
    )
    return [_roadmap_response_payload(db, roadmap, user_id) for roadmap in roadmaps]


def _populate_module_content(
    db: Session,
    *,
    module: LearningModule,
    user_id: int,
) -> LearningModule:
    if module.theory and module.practice_quiz and module.flashcards:
        return module

    roadmap = module.roadmap
    context_str, retrieved_context = build_learning_context(module.title, roadmap.subject if roadmap else None, db=db)
    prompt = learning_module_prompt(module.title, roadmap.title if roadmap else module.title, context_str)
    ai_data = gateway.generate_structured_response(
        prompt,
        LearningModuleContentSchema,
        use_pro=False,
        user_id=user_id,
        feature="learning_module_content",
        prompt_version=PROMPT_VERSION_LEARNING_MODULE,
    )

    module.summary = module.summary or ai_data.overview
    module.theory = ai_data.theory or module.theory or ""
    module.institutional_notes = ai_data.institutional_notes or module.institutional_notes or ""
    module.important_questions = _safe_json_list(ai_data.important_questions)
    module.previous_year_questions = _safe_json_list(ai_data.previous_year_questions)
    module.examples = _safe_json_list(ai_data.examples)
    module.diagrams = _safe_json_list(ai_data.diagrams)
    module.practice_quiz = [item.model_dump() for item in ai_data.practice_quiz]
    module.flashcards = [item.model_dump() for item in ai_data.flashcards]
    module.revision_notes = ai_data.revision_notes or module.revision_notes or ""
    module.resources = _safe_json_list(ai_data.resources)
    module.source_chips = ai_data.source_chips or module.source_chips or ["AI Generated"]
    module.retrieved_chunks = ai_data.retrieved_chunks or retrieved_context
    db.commit()
    db.refresh(module)
    return module


def get_module(db: Session, module_id: int, user_id: int) -> Dict[str, Any]:
    module = (
        db.query(LearningModule)
        .options(selectinload(LearningModule.roadmap))
        .join(LearningRoadmap, LearningRoadmap.id == LearningModule.roadmap_id)
        .filter(LearningModule.id == module_id, LearningRoadmap.user_id == user_id)
        .first()
    )
    if not module:
        raise HTTPException(status_code=404, detail="Learning module not found")
    return _module_response_payload(db, module, user_id)


def get_module_section(db: Session, module_id: int, user_id: int, section: str) -> Dict[str, Any]:
    module = (
        db.query(LearningModule)
        .options(selectinload(LearningModule.roadmap))
        .join(LearningRoadmap, LearningRoadmap.id == LearningModule.roadmap_id)
        .filter(LearningModule.id == module_id, LearningRoadmap.user_id == user_id)
        .first()
    )
    if not module:
        raise HTTPException(status_code=404, detail="Learning module not found")
    module = _populate_module_content(db, module=module, user_id=user_id)
    payload = _module_response_payload(db, module, user_id)
    if section == "summary":
        return {
            "module_id": module.id,
            "section": "summary",
            "content": module.theory or module.summary or "",
            "source_chips": payload["source_chips"],
            "retrieved_chunks": payload["retrieved_chunks"],
        }
    if section == "quiz":
        return {
            "module_id": module.id,
            "section": "quiz",
            "questions": payload["practice_quiz"],
            "source_chips": payload["source_chips"],
            "retrieved_chunks": payload["retrieved_chunks"],
        }
    if section == "flashcards":
        return {
            "module_id": module.id,
            "section": "flashcards",
            "flashcards": payload["flashcards"],
            "source_chips": payload["source_chips"],
            "retrieved_chunks": payload["retrieved_chunks"],
        }
    raise HTTPException(status_code=400, detail="Invalid module section requested")


def complete_module(db: Session, module_id: int, user_id: int, time_spent: int = 0) -> Dict[str, Any]:
    module = (
        db.query(LearningModule)
        .join(LearningRoadmap, LearningRoadmap.id == LearningModule.roadmap_id)
        .filter(LearningModule.id == module_id, LearningRoadmap.user_id == user_id)
        .first()
    )
    if not module:
        raise HTTPException(status_code=404, detail="Learning module not found")

    progress = (
        db.query(LearningProgress)
        .filter(LearningProgress.student_id == user_id, LearningProgress.module_id == module.id)
        .first()
    )
    if not progress:
        progress = LearningProgress(student_id=user_id, module_id=module.id)
        db.add(progress)
    progress.completed = True
    progress.time_spent = max(int(progress.time_spent or 0), int(time_spent or 0))
    progress.progress_percent = 100.0
    if not progress.completed_at:
        from datetime import datetime, timezone

        progress.completed_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Module marked complete", "module_id": module.id, "completed": True}


def chat_module(db: Session, module_id: int, user_id: int, message: str, history: List[Dict[str, str]] | None = None) -> Dict[str, Any]:
    module = (
        db.query(LearningModule)
        .options(selectinload(LearningModule.roadmap))
        .join(LearningRoadmap, LearningRoadmap.id == LearningModule.roadmap_id)
        .filter(LearningModule.id == module_id, LearningRoadmap.user_id == user_id)
        .first()
    )
    if not module:
        raise HTTPException(status_code=404, detail="Learning module not found")

    roadmap = module.roadmap
    query = f"{roadmap.title if roadmap else ''} {module.title} {message}".strip()
    subject = roadmap.title if roadmap else module.title
    chat_history = history or []
    return asyncio_run(chat_with_context(query, chat_history, subject=subject, user_id=user_id))


def asyncio_run(coro):
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    if loop.is_running():
        new_loop = asyncio.new_event_loop()
        try:
            return new_loop.run_until_complete(coro)
        finally:
            new_loop.close()
    return loop.run_until_complete(coro)
