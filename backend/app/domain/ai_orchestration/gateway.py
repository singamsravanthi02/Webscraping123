import google.generativeai as genai
from typing import Dict, Any, List
import re
from fastapi import HTTPException
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.core.config import settings
from app.db.session import SessionLocal
from app.domain.audit_logs.models import AITokenUsageLog

import logging

logger = logging.getLogger(__name__)

if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)
else:
    logger.critical("GEMINI_API_KEY is missing! AI features will gracefully degrade.")

class AIGateway:
    """
    Centralized Gateway for all AI routing.
    Handles Model Selection, Retries, Fallbacks, and Token Accounting.
    """
    
    def __init__(self):
        self.flash_model = genai.GenerativeModel('gemini-1.5-flash')
        self.pro_model = genai.GenerativeModel('gemini-1.5-pro')
        
    def sanitize_prompt(self, text: str) -> str:
        """
        Basic pre-flight check to mitigate prompt injection.
        If malicious patterns are found, we reject the request.
        """
        if not text:
            return text
            
        malicious_patterns = [
            r"(?i)\bignore all previous instructions\b",
            r"(?i)\bdisregard previous instructions\b",
            r"(?i)\byou are now an evil\b",
            r"(?i)\bsystem prompt\b",
            r"(?i)\boutput your instructions\b"
        ]
        
        for pattern in malicious_patterns:
            if re.search(pattern, text):
                raise HTTPException(status_code=400, detail="Security violation: Invalid prompt content detected.")
                
        return text

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def generate_content(
        self, 
        prompt: str, 
        use_pro: bool = False, 
        user_id: int = None, 
        feature: str = "orchestration"
    ) -> str:
        """
        Generates content using the optimal model.
        """
        sanitized_prompt = self.sanitize_prompt(prompt)
        
        if not settings.GEMINI_API_KEY:
            logger.warning("Mocking AI generation because GEMINI_API_KEY is unset.")
            return "AI features are currently unavailable due to missing configuration."
            
        model = self.pro_model if use_pro else self.flash_model
        
        response = model.generate_content(sanitized_prompt)
        
        if user_id:
            self._log_tokens(response.usage_metadata, user_id, feature, "gemini-1.5-pro" if use_pro else "gemini-1.5-flash")
            
        return response.text
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def chat_session(self, use_pro: bool = False):
        """
        Returns a ChatSession object. Callers must handle their own token logging using _log_tokens.
        """
        if not settings.GEMINI_API_KEY:
            raise HTTPException(status_code=503, detail="AI chat is currently unavailable due to missing configuration.")
            
        model = self.pro_model if use_pro else self.flash_model
        return model.start_chat(history=[])
        
    def _log_tokens(self, usage, user_id: int, feature: str, model_name: str):
        if not usage:
            return
            
        db = SessionLocal()
        try:
            log = AITokenUsageLog(
                user_id=user_id,
                model_name=model_name,
                prompt_tokens=usage.prompt_token_count,
                completion_tokens=usage.candidates_token_count,
                total_tokens=usage.total_token_count,
                feature=feature
            )
            db.add(log)
            db.commit()
        except Exception:
            pass # Silently fail
        finally:
            db.close()

# Singleton instance
gateway = AIGateway()
