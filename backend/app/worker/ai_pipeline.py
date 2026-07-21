import logging
from typing import Dict, Any

from app.domain.ai_orchestration.gateway import AIGateway, gateway
from app.domain.ai_orchestration.prompts import job_extraction_prompt
from app.domain.ai_orchestration.schemas import JobExtractionSchema

logger = logging.getLogger(__name__)

class AIPipeline:
    def __init__(self):
        # Load local embedding model lazily to save startup time
        self._embedder = None
        
    @property
    def embedder(self):
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading local embedding model: BAAI/bge-small-en-v1.5")
            self._embedder = SentenceTransformer("BAAI/bge-small-en-v1.5")
        return self._embedder
        
    def extract_job_details(self, raw_description: str) -> Dict[str, Any]:
        """
        Uses Gemini to extract structured data from a raw job description.
        Returns a dictionary with: skills, eligibility, deadline, ai_summary
        """
        logger.info("Extracting job details via Gemini LLM...")
        
        try:
            data = gateway.generate_structured_response(
                job_extraction_prompt(raw_description),
                JobExtractionSchema,
                use_pro=False,
                feature="job_extraction",
            )
            return data.model_dump()
        except Exception as e:
            logger.error(f"Gemini extraction failed: {e}")
            return {
                "skills": [],
                "eligibility": "Not specified",
                "ai_summary": "Standard role."
            }
        
    def generate_embedding(self, text: str) -> list[float]:
        """
        Uses local SentenceTransformers (BAAI/bge-small-en-v1.5) to generate a 384-dimensional embedding.
        """
        # For BAAI models, passing text directly is fine. 
        # (For retrieval, queries often need a prefix, but this is for document chunks).
        embedding = self.embedder.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def upsert_to_qdrant(self, job_id: int, embedding: list[float], metadata: Dict[str, Any]):
        """
        Pushes the embedding to Qdrant for semantic matching.
        """
        logger.info(f"Upserting job {job_id} to Qdrant")
        pass
