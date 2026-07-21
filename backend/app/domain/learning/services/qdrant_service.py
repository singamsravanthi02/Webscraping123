from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, FieldCondition, Filter, MatchValue, PointStruct, VectorParams

from app.core.config import settings
from app.domain.ai_orchestration.gateway import gateway

logger = logging.getLogger(__name__)

COLLECTION_NAME = "learning_materials"
EMBEDDING_DIMENSION = 3072

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
):
    _ensure_collection()
    chunks = chunk_text(text_content)
    points = []

    for i, chunk in enumerate(chunks):
        embedding = get_embedding(chunk)
        points.append(
            PointStruct(
                id=int(f"{document_id}{i:04d}"),
                vector=embedding,
                payload={
                    "document_id": document_id,
                    "title": title,
                    "source_type": source_type,
                    "chunk_index": i,
                    "text": chunk,
                    "subject": subject,
                    "unit": unit,
                    "semester": semester,
                    "topic": topic,
                    "keywords": keywords or [],
                },
            )
        )

    if points:
        qdrant_client.upsert(collection_name=COLLECTION_NAME, points=points)


def search_documents(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    _ensure_collection()
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
            results.append(
                {
                    "score": hit.score,
                    "title": payload.get("title"),
                    "text": payload.get("text"),
                    "source_type": payload.get("source_type"),
                    "document_id": payload.get("document_id"),
                }
            )
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
