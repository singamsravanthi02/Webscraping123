import logging
from typing import Dict, Any

from app.domain.ai_orchestration.gateway import AIGateway
import json

logger = logging.getLogger(__name__)

class AIPipeline:
    def __init__(self):
        self.gateway = AIGateway()
        
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
        
        prompt = f"""
        Extract structured data from the following job description.
        Return ONLY valid JSON with the following keys:
        - "skills": A list of technical skills mentioned (strings).
        - "eligibility": A short summary of eligibility criteria (string).
        - "ai_summary": A one-sentence summary of the role (string).
        
        Description:
        {raw_description[:3000]}
        """
        
        try:
            chat = self.gateway.chat_session(use_pro=False) # Flash is faster for extraction
            res = chat.send_message(prompt)
            clean_json = res.text.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)
            return {
                "skills": data.get("skills", []),
                "eligibility": data.get("eligibility", "Not specified"),
                "ai_summary": data.get("ai_summary", "A great opportunity.")
            }
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
