from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, FieldCondition, Filter, MatchValue, PointStruct, VectorParams
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.cache_service import cache as ai_cache
from app.domain.knowledge.models import Document, DocumentChunk
from app.domain.ai_orchestration.gateway import gateway

logger = logging.getLogger(__name__)

COLLECTION_NAME = "learning_materials"
EMBEDDING_DIMENSION = 3072
SEARCH_CACHE_TTL_SECONDS = 300

qdrant_client = QdrantClient(
    url=settings.QDRANT_URL,
    api_key=settings.QDRANT_API_KEY if settings.QDRANT_URL.startswith("https://") else None,
)


def _ensure_collection() -> None:
    try:
        collection = qdrant_client.get_collection(COLLECTION_NAME)
        current_vectors = collection.config.params.vectors
        current_size = getattr(current_vectors, "size", None)
        if current_size != EMBEDDING_DIMENSION:
            qdrant_client.delete_collection(COLLECTION_NAME)
            raise ValueError("Recreating Qdrant collection with updated embedding dimension.")
    except Exception:
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=EMBEDDING_DIMENSION, distance=Distance.COSINE),
        )


def get_embedding(text: str) -> List[float]:
    return gateway.embed_text(text, feature="qdrant_embedding")


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def ingest_document(
    document_id: int,
    title: str,
    text_content: str,
    source_type: str,
    subject: str | None = None,
    unit: str | None = None,
    semester: str | None = None,
    topic: str | None = None,
    keywords: List[str] | None = None,
    extra_metadata: Dict[str, Any] | None = None,
    chunk_size: int = 1000,
    overlap: int = 200,
):
    _ensure_collection()
    chunks = chunk_text(text_content, chunk_size=chunk_size, overlap=overlap)
    points = []
    ingestion_timestamp = (extra_metadata or {}).get("ingestion_timestamp") or datetime.now(timezone.utc).isoformat()

    for i, chunk in enumerate(chunks):
        embedding = get_embedding(chunk)
        embedding_id = str(int(f"{document_id}{i:04d}"))
        points.append(
            PointStruct(
                id=int(embedding_id),
                vector=embedding,
                payload={
                    "document_id": document_id,
                    "title": title,
                    "source_type": source_type,
                    "chunk_index": i,
                    "embedding_id": embedding_id,
                    "text": chunk,
                    "subject": subject,
                    "unit": unit,
                    "semester": semester,
                    "topic": topic,
                    "keywords": keywords or [],
                    **(extra_metadata or {}),
                    "ingestion_timestamp": ingestion_timestamp,
                },
            )
        )

    if points:
        qdrant_client.upsert(collection_name=COLLECTION_NAME, points=points)


def _lookup_chunk_metadata(db: Session | None, document_id: Any, chunk_index: Any) -> Dict[str, Any]:
    if db is None or document_id is None:
        return {}

    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        chunk = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document_id, DocumentChunk.chunk_index == chunk_index)
            .first()
        )
    except Exception:
        return {}

    page_number = getattr(chunk, "page_number", None)
    chunk_number = int(chunk_index or 0) + 1 if chunk_index is not None else None
    return {
        "document": {
            "id": getattr(doc, "id", document_id),
            "title": getattr(doc, "title", None),
            "source": getattr(doc, "source", None),
            "url": getattr(doc, "url", None),
            "subject": getattr(doc, "subject", None),
            "department": getattr(doc, "department", None),
            "semester": getattr(doc, "semester", None),
            "unit": getattr(doc, "unit", None),
            "module": getattr(doc, "module", None),
            "keywords": list(getattr(doc, "keywords", []) or []),
        },
        "page_number": page_number,
        "chunk_number": chunk_number,
    }


def search_documents(query: str, limit: int = 5, db: Session | None = None) -> List[Dict[str, Any]]:
    _ensure_collection()
    normalized_query = " ".join((query or "").split()).lower()
    cache_key = f"qdrant-search:v1:{limit}:{normalized_query}"
    cached = ai_cache.get(cache_key)
    if isinstance(cached, list):
        return cached

    query_vector = get_embedding(query)
    try:
        search_result = qdrant_client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=limit,
        ).points

        results = []
        for hit in search_result:
            payload = hit.payload or {}
            score = float(hit.score or 0.0)
            document_id = payload.get("document_id")
            chunk_index = payload.get("chunk_index")
            metadata = _lookup_chunk_metadata(db, document_id, chunk_index)
            results.append(
                {
                    "score": score,
                    "embedding_distance": round(max(1.0 - score, 0.0), 4),
                    "title": payload.get("title") or metadata.get("document", {}).get("title"),
                    "text": payload.get("text"),
                    "source_type": payload.get("source_type") or metadata.get("document", {}).get("source"),
                    "document_id": document_id,
                    "chunk_index": chunk_index,
                    "embedding_id": payload.get("embedding_id"),
                    "chunk_number": metadata.get("chunk_number"),
                    "page_number": metadata.get("page_number"),
                    "metadata": metadata.get("document", {}),
                    "source_page_url": payload.get("source_page_url"),
                    "resource_url": payload.get("resource_url"),
                    "google_drive_file_id": payload.get("google_drive_file_id"),
                    "document_title": payload.get("document_title"),
                    "resource_label": payload.get("resource_label"),
                    "ingestion_timestamp": payload.get("ingestion_timestamp"),
                }
            )
        ai_cache.set(cache_key, results, SEARCH_CACHE_TTL_SECONDS)
        return results
    except Exception as exc:
        logger.error("Failed to search Qdrant: %s", exc)
        raise RuntimeError(f"Qdrant search failed: {exc}") from exc


def get_document_text(document_id: int) -> str:
    _ensure_collection()
    try:
        response, _ = qdrant_client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id),
                    )
                ]
            ),
            limit=1000,
        )

        if not response:
            return ""

        sorted_chunks = sorted(response, key=lambda p: p.payload.get("chunk_index", 0))
        return "\n\n".join(p.payload.get("text", "") for p in sorted_chunks)
    except Exception as exc:
        logger.error("Failed to retrieve chunks for document %s: %s", document_id, exc)
        raise RuntimeError(f"Qdrant retrieval failed: {exc}") from exc
