from __future__ import annotations

import hashlib
import json
import logging
import re
import threading
import time
import uuid
from typing import Any, Dict, Type, TypeVar

from fastapi import HTTPException
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.db.session import SessionLocal
from app.domain.ai_orchestration.prompts import PROMPT_VERSION_JSON_REPAIR, repair_json_prompt
from app.domain.ai_orchestration.providers import (
    AIProvider,
    GeminiProvider,
    NvidiaProvider,
    OllamaProvider,
    ProviderError,
    ProviderQuotaError,
    ProviderRateLimitError,
    ProviderResult,
    ProviderTimeoutError,
    ProviderUnavailableError,
    provider_health,
)
from app.domain.audit_logs.models import AITokenUsageLog
from app.services.cache_service import cache as ai_cache

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


def _clean_json(text: str) -> str:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()
    return cleaned


class AIGateway:
    """Single AI ingress backed by multiple provider adapters."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.providers: dict[str, AIProvider] = {
            "gemini": GeminiProvider(),
            "nvidia": NvidiaProvider(),
            "ollama": OllamaProvider(),
        }
        self.client = getattr(self.providers["gemini"], "client", None)
        self._last_feature: str | None = None
        self._last_routing_decision: Dict[str, Any] = {}
        if not self.client:
            logger.warning("Gemini is unavailable at startup; other providers will carry fallback traffic.")

    def _ensure_gemini_client(self):
        client = getattr(self.providers["gemini"], "client", None)
        if not client:
            raise HTTPException(status_code=503, detail="AI service is unavailable.")
        return client

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

    def _cache_key(self, feature: str, prompt_version: str, provider_name: str, model_name: str, prompt: str) -> str:
        digest = hashlib.sha256(
            f"{feature}|{prompt_version}|{provider_name}|{model_name}|{prompt}".encode("utf-8")
        ).hexdigest()
        return f"ai:{feature}:{digest}"

    def _should_fallback_to_next_provider(self, exc: Exception) -> bool:
        if isinstance(
            exc,
            (
                ProviderUnavailableError,
                ProviderTimeoutError,
                ProviderQuotaError,
                ProviderRateLimitError,
                ProviderError,
            ),
        ):
            return True

        text = str(exc).lower()
        return any(
            marker in text
            for marker in (
                "429",
                "quota",
                "rate limit",
                "not found for api version",
                "not supported for generatecontent",
                "not supported for embedcontent",
                "503",
                "timeout",
                "deadline",
                "connection refused",
                "service unavailable",
            )
        )

    def _provider_order(self, feature: str) -> list[str]:
        feature_name = (feature or "").lower()
        if "embed" in feature_name:
            return ["ollama", "gemini"]
        if any(token in feature_name for token in ("resume", "career", "interview_evaluation", "interview_eval")):
            route = ["gemini", "nvidia", "ollama"]
        elif any(token in feature_name for token in ("learning_chat", "offline_chat")):
            route = ["ollama", "gemini", "nvidia"]
        elif any(token in feature_name for token in ("quiz", "assessment", "question", "study", "summary", "learning")):
            route = ["nvidia", "gemini", "ollama"]
        elif any(token in feature_name for token in ("job", "recommend", "search", "match")):
            route = ["gemini", "nvidia", "ollama"]
        else:
            route = ["gemini", "nvidia", "ollama"]

        configured = settings.AI_PROVIDER.upper()
        if configured in {"GEMINI", "NVIDIA", "OLLAMA"}:
            return [configured.lower(), *[name for name in route if name != configured.lower()]]
        return route

    def _candidate_models(self, provider_name: str, use_pro: bool, feature: str) -> list[str]:
        feature_name = (feature or "").lower()
        if provider_name == "gemini":
            force_pro = use_pro or any(token in feature_name for token in ("resume", "career", "interview"))
            models = [settings.GEMINI_MODEL_FLASH, settings.GEMINI_MODEL_FLASH_LITE]
            if force_pro:
                models.insert(0, settings.GEMINI_MODEL_PRO)
            return [model for index, model in enumerate(models) if model and model not in models[:index]]

        provider = self.providers.get(provider_name)
        if not provider:
            return []

        models = provider.model_list()
        if provider_name == "nvidia":
            preferred = settings.NVIDIA_MODEL
            feature_priorities = [
                preferred,
                "nvidia/nemotron-mini-4b-instruct",
                "mistralai/ministral-14b-instruct-2512",
                "meta/llama-3.1-8b-instruct",
                "z-ai/glm-5.2",
            ]
            if any(token in feature_name for token in ("question", "quiz", "study", "summary", "learning", "job", "recommend", "search", "match")):
                feature_priorities = [
                    preferred,
                    "nvidia/nemotron-mini-4b-instruct",
                    "mistralai/ministral-14b-instruct-2512",
                    "meta/llama-3.1-8b-instruct",
                    "z-ai/glm-5.2",
                ]
            ordered = []
            for candidate in feature_priorities + models:
                if candidate and candidate not in ordered:
                    ordered.append(candidate)
            return ordered
        return models

    def _request_config(self) -> Dict[str, Any]:
        return {
            "temperature": 0.2,
            "top_p": 0.95,
            "max_output_tokens": 2048,
        }

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

    def _record_routing_decision(self, feature: str, providers: list[str]) -> None:
        with self._lock:
            self._last_feature = feature
            self._last_routing_decision = {
                "feature": feature,
                "providers": providers,
                "primary_provider": providers[0] if providers else None,
                "prompt_route": " -> ".join(providers),
            }

    def _usage_dict(self, usage: Any) -> Dict[str, int]:
        if not usage:
            return {}

        if isinstance(usage, dict):
            return {
                "prompt_tokens": int(usage.get("prompt_tokens", 0) or 0),
                "completion_tokens": int(usage.get("completion_tokens", 0) or 0),
                "total_tokens": int(usage.get("total_tokens", 0) or 0),
            }

        return {
            "prompt_tokens": int(getattr(usage, "prompt_token_count", 0) or 0),
            "completion_tokens": int(getattr(usage, "candidates_token_count", 0) or 0),
            "total_tokens": int(getattr(usage, "total_token_count", 0) or 0),
        }

    def _log_tokens(self, usage: Any, user_id: int, feature: str, model_name: str) -> None:
        token_usage = self._usage_dict(usage)
        if not token_usage:
            return

        db = SessionLocal()
        try:
            log = AITokenUsageLog(
                user_id=user_id,
                model_name=model_name,
                prompt_tokens=token_usage["prompt_tokens"],
                completion_tokens=token_usage["completion_tokens"],
                total_tokens=token_usage["total_tokens"],
                feature=feature,
            )
            db.add(log)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Failed to persist AI token usage log")
        finally:
            db.close()

    def _invoke_provider(
        self,
        provider_name: str,
        prompt: str,
        *,
        schema_model: Type[T] | None = None,
        model_name: str,
        stream: bool = False,
    ) -> ProviderResult:
        provider = self.providers[provider_name]
        if schema_model is None:
            return provider.generate(prompt, model=model_name, stream=stream)
        return provider.generate_structured(prompt, schema_model, model=model_name, stream=stream)

    def _generate_with_providers(
        self,
        prompt: str,
        *,
        use_pro: bool,
        user_id: int | None,
        feature: str,
        prompt_version: str,
        schema_model: Type[T] | None = None,
        cache_ttl: int | None = None,
    ) -> tuple[str, Dict[str, int]]:
        sanitized_prompt = self.sanitize_prompt(prompt)
        request_id = uuid.uuid4().hex[:12]
        start = time.perf_counter()
        retries = 0
        route = self._provider_order(feature)
        self._record_routing_decision(feature, route)
        if cache_ttl is None:
            cache_ttl = settings.AI_CACHE_TTL_SECONDS

        last_error: Exception | None = None
        for provider_name in route:
            provider = self.providers.get(provider_name)
            if not provider:
                continue

            for model_name in self._candidate_models(provider_name, use_pro, feature):
                if not model_name:
                    continue

                cache_key = self._cache_key(feature, prompt_version, provider_name, model_name, sanitized_prompt)
                cached = ai_cache.get(cache_key)
                if isinstance(cached, str) and cached:
                    provider_health.mark_cache_hit(provider_name)
                    self._log_request(
                        request_id=request_id,
                        module=feature,
                        prompt_version=prompt_version,
                        model_name=model_name,
                        duration_ms=0,
                        success=True,
                        retry_count=0,
                        user_id=user_id,
                        detail=f"cache_hit:{provider_name}",
                    )
                    return cached, {}

                for attempt in range(1, settings.AI_RETRY_ATTEMPTS + 1):
                    retries = attempt - 1
                    try:
                        result = self._invoke_provider(
                            provider_name,
                            sanitized_prompt,
                            schema_model=schema_model,
                            model_name=model_name,
                            stream=False,
                        )
                        text = _clean_json(result.text)
                        if not text:
                            raise ProviderError("Empty AI response")

                        if user_id and result.usage:
                            self._log_tokens(result.usage, user_id, feature, result.model or model_name)

                        if cache_ttl and text:
                            ai_cache.set(cache_key, text, cache_ttl)

                        provider_health.mark_success(
                            provider_name,
                            model=result.model or model_name,
                            latency_ms=(time.perf_counter() - start) * 1000,
                            usage=result.usage,
                        )
                        self._log_request(
                            request_id=request_id,
                            module=feature,
                            prompt_version=prompt_version,
                            model_name=result.model or model_name,
                            duration_ms=int((time.perf_counter() - start) * 1000),
                            success=True,
                            retry_count=retries,
                            user_id=user_id,
                            token_usage=result.usage,
                            detail=provider_name,
                        )
                        return text, result.usage
                    except HTTPException:
                        raise
                    except Exception as exc:
                        last_error = exc
                        provider_health.mark_failure(provider_name, model=model_name, error=exc)
                        logger.warning("AI request attempt failed for %s on %s: %s", feature, model_name, exc)
                        if attempt < settings.AI_RETRY_ATTEMPTS and not self._should_fallback_to_next_provider(exc):
                            time.sleep(min(2 ** (attempt - 1), 8))
                            continue
                        if provider_name != route[-1]:
                            provider_health.mark_fallback(provider_name)
                        break

                if provider_name != route[-1]:
                    logger.warning("Falling back to next AI provider for %s after %s failure", feature, provider_name)

        self._log_request(
            request_id=request_id,
            module=feature,
            prompt_version=prompt_version,
            model_name="unknown",
            duration_ms=int((time.perf_counter() - start) * 1000),
            success=False,
            retry_count=retries,
            user_id=user_id,
            detail=str(last_error) if last_error else "unknown_error",
        )
        raise HTTPException(status_code=503, detail=f"AI request failed: {last_error}")

    def generate_content(
        self,
        prompt: str,
        use_pro: bool = False,
        user_id: int | None = None,
        feature: str = "orchestration",
        prompt_version: str = "v1",
        cache_ttl: int | None = None,
    ) -> str:
        text, _ = self._generate_with_providers(
            prompt,
            use_pro=use_pro,
            user_id=user_id,
            feature=feature,
            prompt_version=prompt_version,
            cache_ttl=cache_ttl,
        )
        return text

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

        raw_text, _ = self._generate_with_providers(
            prompt,
            use_pro=use_pro,
            user_id=user_id,
            feature=feature,
            prompt_version=prompt_version,
            schema_model=schema_model,
        )

        try:
            return _parse(raw_text)
        except Exception:
            repaired = self.generate_content(
                prompt=repair_json_prompt(schema_model.__name__, raw_text, schema_model.model_json_schema()),
                use_pro=use_pro,
                user_id=user_id,
                feature="offline_chat",
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
        gemini = self.providers["gemini"]
        client = getattr(gemini, "client", None)
        if not client:
            raise HTTPException(status_code=503, detail="AI service is unavailable.")

        payload = (text or "").strip()
        if not payload:
            return [0.0] * 768

        if cache_ttl is None:
            cache_ttl = settings.AI_CACHE_TTL_SECONDS

        route = self._provider_order(feature)
        self._record_routing_decision(feature, route)

        request_id = uuid.uuid4().hex[:12]
        start = time.perf_counter()
        retries = 0
        last_error: Exception | None = None

        for provider_name in route:
            provider = self.providers.get(provider_name)
            if not provider:
                continue

            for attempt in range(1, settings.AI_RETRY_ATTEMPTS + 1):
                retries = attempt - 1
                try:
                    cache_key = self._cache_key(feature, prompt_version, provider_name, "nomic-embed-text" if provider_name == "ollama" else "gemini-embedding-001", payload)
                    cached = ai_cache.get(cache_key)
                    if isinstance(cached, list) and cached:
                        provider_health.mark_cache_hit(provider_name)
                        return cached

                    if provider_name == "ollama":
                        embedding = provider.embed_text(payload, model="nomic-embed-text")  # type: ignore[attr-defined]
                        model_name = "nomic-embed-text"
                    else:
                        response = client.models.embed_content(
                            model="gemini-embedding-001",
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
                        model_name = "gemini-embedding-001"

                    if not embedding:
                        raise ValueError("Empty embedding response")

                    embedding_list = list(embedding)
                    if len(embedding_list) < 3072:
                        embedding_list.extend([0.0] * (3072 - len(embedding_list)))
                    elif len(embedding_list) > 3072:
                        embedding_list = embedding_list[:3072]

                    if cache_ttl:
                        ai_cache.set(cache_key, embedding_list, cache_ttl)

                    provider_health.mark_success(
                        provider_name,
                        model=model_name,
                        latency_ms=(time.perf_counter() - start) * 1000,
                        usage={},
                    )
                    self._log_request(
                        request_id=request_id,
                        module=feature,
                        prompt_version=prompt_version,
                        model_name=model_name,
                        duration_ms=int((time.perf_counter() - start) * 1000),
                        success=True,
                        retry_count=retries,
                        user_id=user_id,
                        detail=f"embedding:{provider_name}",
                    )
                    return embedding_list
                except HTTPException:
                    raise
                except Exception as exc:
                    last_error = exc
                    provider_health.mark_failure(provider_name, model="nomic-embed-text" if provider_name == "ollama" else "gemini-embedding-001", error=exc)
                    logger.warning("Embedding attempt failed for %s on %s: %s", feature, provider_name, exc)
                    if attempt < settings.AI_RETRY_ATTEMPTS and not self._should_fallback_to_next_provider(exc):
                        time.sleep(min(2 ** (attempt - 1), 8))
                        continue
                    if provider_name != route[-1]:
                        provider_health.mark_fallback(provider_name)
                    break

        self._log_request(
            request_id=request_id,
            module=feature,
            prompt_version=prompt_version,
            model_name="nomic-embed-text" if route and route[0] == "ollama" else "gemini-embedding-001",
            duration_ms=int((time.perf_counter() - start) * 1000),
            success=False,
            retry_count=retries,
            user_id=user_id,
            detail=str(last_error) if last_error else "unknown_error",
        )
        raise HTTPException(status_code=503, detail=f"Embedding generation failed: {last_error}")

    def provider_status(self) -> list[Dict[str, Any]]:
        return provider_health.refresh(self.providers)

    def routing_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "active_provider": provider_health.active_provider,
                "last_feature": self._last_feature,
                "last_routing_decision": self._last_routing_decision,
                "routing_matrix": {
                    "resume_analysis": self._provider_order("resume_analysis"),
                    "interview_evaluation": self._provider_order("interview_evaluation"),
                    "career_dna": self._provider_order("career_dna"),
                    "question_generation": self._provider_order("question_generation"),
                    "quiz_generation": self._provider_order("quiz_generation"),
                    "study_materials": self._provider_order("study_materials"),
                    "learning_summary": self._provider_order("learning_summary"),
                    "learning_chat": self._provider_order("learning_chat"),
                    "offline_chat": self._provider_order("offline_chat"),
                    "embeddings": self._provider_order("embeddings"),
                    "job_ai": self._provider_order("job_ai"),
                },
            }

    def chat_session(self, use_pro: bool = False):
        gemini = self.providers["gemini"]
        client = getattr(gemini, "client", None)
        if not client:
            raise HTTPException(status_code=503, detail="AI service is unavailable.")
        model_name = settings.GEMINI_MODEL_PRO if use_pro else settings.GEMINI_MODEL_FLASH
        return client.chats.create(model=model_name, history=[])


gateway = AIGateway()
