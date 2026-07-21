from __future__ import annotations

import hashlib
import json
import logging
import re
import time
import uuid
from typing import Any, Dict, Type, TypeVar

from fastapi import HTTPException
from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.db.session import SessionLocal
from app.domain.ai_orchestration.prompts import PROMPT_VERSION_JSON_REPAIR, repair_json_prompt
from app.domain.audit_logs.models import AITokenUsageLog
from app.services.cache_service import cache as ai_cache

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

SAFETY_SETTINGS = [
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    ),
]

BASE_CONFIG = types.GenerateContentConfig(
    temperature=0.2,
    top_p=0.95,
    max_output_tokens=2048,
    safety_settings=SAFETY_SETTINGS,
)


def _clean_json(text: str) -> str:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()
    return cleaned


class AIGateway:
    """Single AI ingress for all Gemini calls."""

    def __init__(self) -> None:
        self._available = bool(settings.GEMINI_API_KEY)
        self.client: genai.Client | None = None
        if self._available:
            self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        else:
            logger.critical("GEMINI_API_KEY is missing. AI calls will fail closed.")

    def _ensure_client(self) -> genai.Client:
        if not self.client:
            raise HTTPException(status_code=503, detail="AI service is unavailable.")
        return self.client

    def _candidate_models(self, use_pro: bool) -> list[str]:
        candidates: list[str] = []
        if use_pro:
            candidates.append(settings.GEMINI_MODEL_PRO)
        candidates.append(settings.GEMINI_MODEL_FLASH)
        if settings.GEMINI_MODEL_FLASH_LITE and settings.GEMINI_MODEL_FLASH_LITE not in candidates:
            candidates.append(settings.GEMINI_MODEL_FLASH_LITE)
        return candidates

    def sanitize_prompt(self, text: str) -> str:
        if not text:
            return text

        malicious_patterns = [
            r"(?i)\bignore all previous instructions\b",
            r"(?i)\bdisregard previous instructions\b",
            r"(?i)\byou are now an evil\b",
            r"(?i)\bsystem prompt\b",
            r"(?i)\boutput your instructions\b",
        ]

        for pattern in malicious_patterns:
            if re.search(pattern, text):
                raise HTTPException(status_code=400, detail="Security violation: Invalid prompt content detected.")
        return text

    def _cache_key(self, feature: str, prompt_version: str, model_name: str, prompt: str) -> str:
        digest = hashlib.sha256(f"{feature}|{prompt_version}|{model_name}|{prompt}".encode("utf-8")).hexdigest()
        return f"ai:{feature}:{digest}"

    def _should_fallback_to_next_model(self, exc: Exception) -> bool:
        text = str(exc).lower()
        return any(
            marker in text
            for marker in (
                "429",
                "quota",
                "not found for api version",
                "not supported for generatecontent",
                "not supported for embedcontent",
                "503",
                "timeout",
                "deadline",
            )
        )

    def _request_config(self, *, response_schema: Any | None = None, temperature: float | None = None, max_output_tokens: int | None = None):
        config_kwargs: Dict[str, Any] = {
            "temperature": temperature if temperature is not None else BASE_CONFIG.temperature,
            "top_p": BASE_CONFIG.top_p,
            "max_output_tokens": max_output_tokens if max_output_tokens is not None else BASE_CONFIG.max_output_tokens,
            "safety_settings": SAFETY_SETTINGS,
        }
        if response_schema is not None:
            config_kwargs["response_mime_type"] = "application/json"
            config_kwargs["response_schema"] = response_schema
        return types.GenerateContentConfig(**config_kwargs)

    def _response_text(self, response: Any) -> str:
        text = getattr(response, "text", None)
        if isinstance(text, str) and text.strip():
            return text.strip()

        candidates = getattr(response, "candidates", None) or []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None) or []
            for part in parts:
                part_text = getattr(part, "text", None)
                if isinstance(part_text, str) and part_text.strip():
                    return part_text.strip()
        return ""

    def _log_request(
        self,
        *,
        request_id: str,
        module: str,
        prompt_version: str,
        model_name: str,
        duration_ms: int,
        success: bool,
        retry_count: int,
        user_id: int | None = None,
        token_usage: Dict[str, int] | None = None,
        detail: str | None = None,
    ) -> None:
        logger.info(
            json.dumps(
                {
                    "request_id": request_id,
                    "module": module,
                    "prompt_version": prompt_version,
                    "model": model_name,
                    "duration_ms": duration_ms,
                    "success": success,
                    "retry_count": retry_count,
                    "user_id": user_id,
                    "token_usage": token_usage or {},
                    "detail": detail,
                },
                default=str,
            )
        )

    def _log_tokens(self, usage: Any, user_id: int, feature: str, model_name: str) -> None:
        if not usage:
            return

        db = SessionLocal()
        try:
            log = AITokenUsageLog(
                user_id=user_id,
                model_name=model_name,
                prompt_tokens=getattr(usage, "prompt_token_count", 0) or 0,
                completion_tokens=getattr(usage, "candidates_token_count", 0) or 0,
                total_tokens=getattr(usage, "total_token_count", 0) or 0,
                feature=feature,
            )
            db.add(log)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Failed to persist AI token usage log")
        finally:
            db.close()

    def _token_usage_dict(self, usage: Any) -> Dict[str, int]:
        return {
            "prompt_tokens": int(getattr(usage, "prompt_token_count", 0) or 0),
            "completion_tokens": int(getattr(usage, "candidates_token_count", 0) or 0),
            "total_tokens": int(getattr(usage, "total_token_count", 0) or 0),
        }

    def generate_content(
        self,
        prompt: str,
        use_pro: bool = False,
        user_id: int | None = None,
        feature: str = "orchestration",
        prompt_version: str = "v1",
        cache_ttl: int | None = None,
    ) -> str:
        client = self._ensure_client()
        sanitized_prompt = self.sanitize_prompt(prompt)
        request_id = uuid.uuid4().hex[:12]
        start = time.perf_counter()
        retries = 0

        if cache_ttl is None:
            cache_ttl = settings.AI_CACHE_TTL_SECONDS

        last_error: Exception | None = None
        candidates = self._candidate_models(use_pro)

        for index, model_name in enumerate(candidates):
            cache_key = self._cache_key(feature, prompt_version, model_name, sanitized_prompt)
            cached = ai_cache.get(cache_key)
            if isinstance(cached, str) and cached:
                self._log_request(
                    request_id=request_id,
                    module=feature,
                    prompt_version=prompt_version,
                    model_name=model_name,
                    duration_ms=0,
                    success=True,
                    retry_count=0,
                    user_id=user_id,
                    detail="cache_hit",
                )
                return cached

            for attempt in range(1, settings.AI_RETRY_ATTEMPTS + 1):
                retries = attempt - 1
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=sanitized_prompt,
                        config=self._request_config(),
                    )
                    text = self._response_text(response)
                    if not text:
                        raise ValueError("Empty AI response")

                    usage = getattr(response, "usage_metadata", None)
                    if user_id and usage:
                        self._log_tokens(usage, user_id, feature, model_name)

                    if cache_ttl and text:
                        ai_cache.set(cache_key, text, cache_ttl)

                    self._log_request(
                        request_id=request_id,
                        module=feature,
                        prompt_version=prompt_version,
                        model_name=model_name,
                        duration_ms=int((time.perf_counter() - start) * 1000),
                        success=True,
                        retry_count=retries,
                        user_id=user_id,
                        token_usage=self._token_usage_dict(usage) if usage else {},
                    )
                    return text
                except HTTPException:
                    raise
                except Exception as exc:
                    last_error = exc
                    logger.warning("AI request attempt failed for %s on %s: %s", feature, model_name, exc)
                    if attempt < settings.AI_RETRY_ATTEMPTS and not self._should_fallback_to_next_model(exc):
                        time.sleep(min(2 ** (attempt - 1), 8))
                        continue
                    break

            if index < len(candidates) - 1:
                logger.warning("Falling back to next Gemini model for %s after %s failure", feature, model_name)

        self._log_request(
            request_id=request_id,
            module=feature,
            prompt_version=prompt_version,
            model_name=candidates[-1],
            duration_ms=int((time.perf_counter() - start) * 1000),
            success=False,
            retry_count=retries,
            user_id=user_id,
            detail=str(last_error) if last_error else "unknown_error",
        )
        raise HTTPException(status_code=503, detail=f"AI request failed: {last_error}")

    def generate_structured_response(
        self,
        prompt: str,
        schema_model: Type[T],
        use_pro: bool = False,
        user_id: int | None = None,
        feature: str = "orchestration",
        prompt_version: str = "v1",
    ) -> T:
        def _parse(candidate: str) -> T:
            cleaned = _clean_json(candidate)
            return schema_model.model_validate_json(cleaned)

        raw_text = self.generate_content(
            prompt=prompt,
            use_pro=use_pro,
            user_id=user_id,
            feature=feature,
            prompt_version=prompt_version,
        )

        try:
            return _parse(raw_text)
        except Exception:
            repaired = self.generate_content(
                prompt=repair_json_prompt(schema_model.__name__, raw_text, schema_model.model_json_schema()),
                use_pro=use_pro,
                user_id=user_id,
                feature=f"{feature}_repair",
                prompt_version=PROMPT_VERSION_JSON_REPAIR,
                cache_ttl=0,
            )
            try:
                return _parse(repaired)
            except ValidationError as exc:
                raise HTTPException(status_code=502, detail=f"Invalid structured AI response for {feature}") from exc
            except Exception as exc:
                raise HTTPException(status_code=502, detail=f"Invalid structured AI response for {feature}") from exc

    def embed_text(
        self,
        text: str,
        *,
        user_id: int | None = None,
        feature: str = "embedding",
        prompt_version: str = "v1",
        cache_ttl: int | None = None,
    ) -> list[float]:
        client = self._ensure_client()
        payload = (text or "").strip()
        if not payload:
            return [0.0] * 768

        if cache_ttl is None:
            cache_ttl = settings.AI_CACHE_TTL_SECONDS

        model_name = "gemini-embedding-001"
        cache_key = self._cache_key(feature, prompt_version, model_name, payload)
        cached = ai_cache.get(cache_key)
        if isinstance(cached, list) and cached:
            return cached

        request_id = uuid.uuid4().hex[:12]
        start = time.perf_counter()
        retries = 0
        last_error: Exception | None = None

        for attempt in range(1, settings.AI_RETRY_ATTEMPTS + 1):
            retries = attempt - 1
            try:
                response = client.models.embed_content(
                    model=model_name,
                    contents=[payload],
                    config={"output_dimensionality": 3072},
                )

                embedding = None
                if hasattr(response, "embeddings") and response.embeddings:
                    embedding = getattr(response.embeddings[0], "values", None)
                if embedding is None and hasattr(response, "embedding"):
                    embedding = getattr(response, "embedding", None)
                if embedding is None and isinstance(response, dict):
                    embedding = response.get("embedding")

                if not embedding:
                    raise ValueError("Empty embedding response")

                if cache_ttl:
                    ai_cache.set(cache_key, embedding, cache_ttl)

                self._log_request(
                    request_id=request_id,
                    module=feature,
                    prompt_version=prompt_version,
                    model_name=model_name,
                    duration_ms=int((time.perf_counter() - start) * 1000),
                    success=True,
                    retry_count=retries,
                    user_id=user_id,
                    detail="embedding",
                )
                return list(embedding)
            except HTTPException:
                raise
            except Exception as exc:
                last_error = exc
                logger.warning("Embedding attempt failed for %s: %s", feature, exc)
                if attempt < settings.AI_RETRY_ATTEMPTS:
                    time.sleep(min(2 ** (attempt - 1), 8))
                continue

        self._log_request(
            request_id=request_id,
            module=feature,
            prompt_version=prompt_version,
            model_name=model_name,
            duration_ms=int((time.perf_counter() - start) * 1000),
            success=False,
            retry_count=retries,
            user_id=user_id,
            detail=str(last_error) if last_error else "unknown_error",
        )
        raise HTTPException(status_code=503, detail=f"Embedding generation failed: {last_error}")

    def chat_session(self, use_pro: bool = False):
        client = self._ensure_client()
        model_name = settings.GEMINI_MODEL_PRO if use_pro else settings.GEMINI_MODEL_FLASH
        return client.chats.create(model=model_name, history=[])


gateway = AIGateway()
