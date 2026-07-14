import os
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
import google.generativeai as genai
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

qdrant_client = None
COLLECTION_NAME = "learning_materials"

try:
    qdrant_url = settings.QDRANT_URL
    
    qdrant_client = QdrantClient(
        url=qdrant_url, 
        api_key=settings.QDRANT_API_KEY
    )
    
    # Ensure collection exists
    try:
        qdrant_client.get_collection(COLLECTION_NAME)
    except Exception:
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=768, distance=Distance.COSINE),
        )
except Exception as e:
    logger.error(f"Qdrant connection failed: {e}. Vector search will be disabled.")

if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)

def get_embedding(text: str) -> List[float]:
    """Generates an embedding using Gemini text-embedding-004 model"""
    try:
        # text-embedding-004 returns 768-dimensional embeddings
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_document"
        )
        return result['embedding']
    except Exception as e:
        print(f"Embedding error: {e}")
        # Return empty/zero vector in worst case (not ideal for production, but prevents crashes)
        return [0.0] * 768 

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Simple character-based chunking with overlap."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def ingest_document(document_id: int, title: str, text_content: str, source_type: str, 
                    subject: str = None, unit: str = None, semester: str = None, 
                    topic: str = None, keywords: List[str] = None):
    """
    Chunks a document, embeds it, and stores it in Qdrant with rich metadata.
    """
    chunks = chunk_text(text_content)
    points = []
    
    for i, chunk in enumerate(chunks):
        embedding = get_embedding(chunk)
        points.append(
            PointStruct(
                id=int(f"{document_id}{i:04d}"), # Unique composite ID
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
                    "keywords": keywords or []
                }
            )
        )
        
    if points:
        if qdrant_client:
            try:
                qdrant_client.upsert(
                    collection_name=COLLECTION_NAME,
                    points=points
                )
            except Exception as e:
                logger.error(f"Failed to upsert to Qdrant: {e}")
        else:
            logger.warning("Qdrant client not initialized. Cannot upsert points.")

def search_documents(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Searches Qdrant for relevant chunks based on the query.
    """
    if not qdrant_client:
        logger.warning("Qdrant client not initialized. Returning empty search results.")
        return []
        
    query_vector = get_embedding(query)
    try:
        search_result = qdrant_client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=limit
        )
        
        results = []
        for hit in search_result:
            results.append({
                "score": hit.score,
                "title": hit.payload.get("title"),
                "text": hit.payload.get("text"),
                "source_type": hit.payload.get("source_type"),
                "document_id": hit.payload.get("document_id")
            })
            
        return results
    except Exception as e:
        logger.error(f"Failed to search Qdrant: {e}")
        return []

def get_document_text(document_id: int) -> str:
    """
    Reconstructs the full document text by fetching all its chunks from Qdrant.
    """
    if not qdrant_client:
        logger.warning("Qdrant client not initialized. Cannot retrieve document text.")
        return ""
        
    from qdrant_client.http.models import Filter, FieldCondition, MatchValue
    
    try:
        response, _ = qdrant_client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id)
                    )
                ]
            ),
            limit=1000 # Assume a doc won't have more than 1000 chunks (1M chars)
        )
        
        if not response:
            return ""
            
        # Sort chunks by their original index
        sorted_chunks = sorted(response, key=lambda p: p.payload.get("chunk_index", 0))
        
        # Reconstruct text
        full_text = "\n\n".join([p.payload.get("text", "") for p in sorted_chunks])
        return full_text
        
    except Exception as e:
        logger.error(f"Failed to retrieve chunks for document {document_id}: {e}")
        return ""
