from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import logging
import re
import threading
import time
from typing import Any, Dict, Type, TypeVar

import httpx
from google import genai
from google.genai import types
from pydantic import BaseModel
from urllib.parse import urlparse, urlunparse

from app.core.config import settings

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class ProviderError(RuntimeError):
    pass


class ProviderUnavailableError(ProviderError):
    pass


class ProviderRateLimitError(ProviderError):
    pass


class ProviderQuotaError(ProviderError):
    pass


class ProviderTimeoutError(ProviderError):
    pass


@dataclass
class ProviderResult:
    text: str
    model: str
    usage: Dict[str, int] = field(default_factory=dict)
    streamed: bool = False


@dataclass
class ProviderHealth:
    provider: str
    available: bool = False
    latency_ms: float | None = None
    request_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    fallback_count: int = 0
    cache_hit_count: int = 0
    total_latency_ms: float = 0.0
    current_model: str | None = None
    last_failure: str | None = None
    models: list[str] = field(default_factory=list)
    last_checked_at: datetime | None = None

    @property
    def success_rate(self) -> float:
        if not self.request_count:
            return 0.0
        return round((self.success_count / self.request_count) * 100.0, 1)

    @property
    def status(self) -> str:
        if not self.available:
            return "offline"
        if self.failure_count and self.failure_count >= self.success_count:
            return "degraded"
        return "healthy"

    @property
    def average_latency_ms(self) -> float:
        if not self.request_count:
            return 0.0
        return round(self.total_latency_ms / self.request_count, 1)

    @property
    def cache_hit_rate(self) -> float:
        total = self.request_count + self.cache_hit_count
        if not total:
            return 0.0
        return round((self.cache_hit_count / total) * 100.0, 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "status": self.status,
            "available": self.available,
            "latency_ms": self.latency_ms,
            "average_latency_ms": self.average_latency_ms,
            "request_count": self.request_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "fallback_count": self.fallback_count,
            "cache_hit_count": self.cache_hit_count,
            "cache_hit_rate": self.cache_hit_rate,
            "success_rate": self.success_rate,
            "current_model": self.current_model,
            "last_failure": self.last_failure,
            "models": self.models,
            "last_checked_at": self.last_checked_at.isoformat() if self.last_checked_at else None,
        }


class ProviderHealthRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._states: dict[str, ProviderHealth] = {
            "gemini": ProviderHealth(provider="gemini"),
            "nvidia": ProviderHealth(provider="nvidia"),
            "ollama": ProviderHealth(provider="ollama"),
        }
        self._active_provider: str | None = None

    def _state(self, provider: str) -> ProviderHealth:
        return self._states[provider]

    def mark_success(
        self,
        provider: str,
        *,
        model: str | None,
        latency_ms: float,
        usage: Dict[str, int] | None = None,
    ) -> None:
        with self._lock:
            state = self._state(provider)
            state.available = True
            state.latency_ms = round(latency_ms, 1)
            state.total_latency_ms += latency_ms
            state.request_count += 1
            state.success_count += 1
            state.current_model = model or state.current_model
            state.last_failure = None
            state.last_checked_at = datetime.now(timezone.utc)
            self._active_provider = provider

    def mark_failure(self, provider: str, *, model: str | None, error: Exception) -> None:
        with self._lock:
            state = self._state(provider)
            state.available = False
            state.total_latency_ms += 0.0
            state.request_count += 1
            state.failure_count += 1
            state.current_model = model or state.current_model
            state.last_failure = str(error)
            state.last_checked_at = datetime.now(timezone.utc)

    def mark_cache_hit(self, provider: str) -> None:
        with self._lock:
            state = self._state(provider)
            state.cache_hit_count += 1
            state.available = True
            state.last_checked_at = datetime.now(timezone.utc)

    def mark_fallback(self, provider: str) -> None:
        with self._lock:
            state = self._state(provider)
            state.fallback_count += 1
            state.last_checked_at = datetime.now(timezone.utc)

    def refresh(self, providers: dict[str, "AIProvider"]) -> list[Dict[str, Any]]:
        snapshot: list[Dict[str, Any]] = []
        for name, provider in providers.items():
            start = time.perf_counter()
            try:
                available = provider.health_check()
                models = provider.model_list() if available else []
                latency_ms = (time.perf_counter() - start) * 1000
                with self._lock:
                    state = self._state(name)
                    state.available = available
                    state.latency_ms = round(latency_ms, 1)
                    state.models = models
                    state.current_model = models[0] if models else state.current_model
                    state.last_checked_at = datetime.now(timezone.utc)
                    snapshot.append(state.to_dict())
            except Exception as exc:
                with self._lock:
                    state = self._state(name)
                    state.available = False
                    state.latency_ms = round((time.perf_counter() - start) * 1000, 1)
                    state.last_failure = str(exc)
                    state.last_checked_at = datetime.now(timezone.utc)
                    snapshot.append(state.to_dict())
        return snapshot

    def snapshot(self) -> list[Dict[str, Any]]:
        with self._lock:
            return [state.to_dict() for state in self._states.values()]

    @property
    def active_provider(self) -> str | None:
        return self._active_provider


provider_health = ProviderHealthRegistry()


def _json_schema(model: Type[T]) -> Dict[str, Any]:
    return model.model_json_schema()


def _clean_text(text: str) -> str:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()
    return cleaned


def _extract_json_fragment(text: str) -> str:
    cleaned = _clean_text(text)
    fenced = re.search(r"```json\s*(\{.*?\})\s*```", cleaned, re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        return cleaned[start : end + 1].strip()

    return cleaned


def _usage_dict(*, prompt_tokens: int = 0, completion_tokens: int = 0, total_tokens: int = 0) -> Dict[str, int]:
    return {
        "prompt_tokens": int(prompt_tokens or 0),
        "completion_tokens": int(completion_tokens or 0),
        "total_tokens": int(total_tokens or 0),
    }


class AIProvider(ABC):
    name: str

    @abstractmethod
    def generate(self, prompt: str, model: str | None = None, *, stream: bool = False) -> ProviderResult:
        raise NotImplementedError

    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        schema_model: Type[T],
        model: str | None = None,
        *,
        stream: bool = False,
    ) -> ProviderResult:
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def model_list(self) -> list[str]:
        raise NotImplementedError


class GeminiProvider(AIProvider):
    name = "gemini"

    def __init__(self) -> None:
        self.client: genai.Client | None = genai.Client(api_key=settings.GEMINI_API_KEY) if settings.GEMINI_API_KEY else None
        self._safety_settings = [
            types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH),
            types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH),
            types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH),
            types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH),
        ]

    def _ensure_client(self) -> genai.Client:
        if not self.client:
            raise ProviderUnavailableError("Gemini API key is missing")
        return self.client

    def _config(self, *, response_schema: Any | None = None, max_output_tokens: int | None = None):
        config_kwargs: Dict[str, Any] = {
            "temperature": 0.2,
            "top_p": 0.95,
            "max_output_tokens": max_output_tokens or 2048,
            "safety_settings": self._safety_settings,
        }
        if response_schema is not None:
            config_kwargs["response_mime_type"] = "application/json"
            config_kwargs["response_schema"] = response_schema
        return types.GenerateContentConfig(**config_kwargs)

    def _extract_text(self, response: Any) -> str:
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

    def _usage(self, response: Any) -> Dict[str, int]:
        usage = getattr(response, "usage_metadata", None)
        if not usage:
            return {}
        return _usage_dict(
            prompt_tokens=getattr(usage, "prompt_token_count", 0) or 0,
            completion_tokens=getattr(usage, "candidates_token_count", 0) or 0,
            total_tokens=getattr(usage, "total_token_count", 0) or 0,
        )

    def model_list(self) -> list[str]:
        models = [settings.GEMINI_MODEL_PRO, settings.GEMINI_MODEL_FLASH, settings.GEMINI_MODEL_FLASH_LITE]
        return [model for index, model in enumerate(models) if model and model not in models[:index]]

    def health_check(self) -> bool:
        return self.client is not None

    def generate(self, prompt: str, model: str | None = None, *, stream: bool = False) -> ProviderResult:
        client = self._ensure_client()
        model_name = model or settings.GEMINI_MODEL_FLASH
        if stream and hasattr(client.models, "generate_content_stream"):
            chunks = client.models.generate_content_stream(
                model=model_name,
                contents=prompt,
                config=self._config(),
            )
            parts: list[str] = []
            for chunk in chunks:
                part = self._extract_text(chunk)
                if part:
                    parts.append(part)
            text = "".join(parts).strip()
            if not text:
                raise ProviderError("Empty Gemini streaming response")
            return ProviderResult(text=text, model=model_name, usage={})

        response = client.models.generate_content(model=model_name, contents=prompt, config=self._config())
        text = self._extract_text(response)
        if not text:
            raise ProviderError("Empty Gemini response")
        return ProviderResult(text=text, model=model_name, usage=self._usage(response))

    def generate_structured(self, prompt: str, schema_model: Type[T], model: str | None = None, *, stream: bool = False) -> ProviderResult:
        client = self._ensure_client()
        model_name = model or settings.GEMINI_MODEL_FLASH
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=self._config(response_schema=_json_schema(schema_model)),
        )
        text = self._extract_text(response)
        if not text:
            raise ProviderError("Empty Gemini structured response")
        return ProviderResult(text=text, model=model_name, usage=self._usage(response))


class NvidiaProvider(AIProvider):
    name = "nvidia"

    def __init__(self) -> None:
        self.base_url = settings.NVIDIA_BASE_URL.rstrip("/")
        self.api_key = settings.NVIDIA_API_KEY
        self.default_model = settings.NVIDIA_MODEL

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _request(self, method: str, path: str, *, json_body: Dict[str, Any] | None = None, stream: bool = False):
        if not self.api_key:
            raise ProviderUnavailableError("NVIDIA API key is missing")
        timeout = settings.AI_REQUEST_TIMEOUT_SECONDS
        url = f"{self.base_url}{path}"
        try:
            if stream:
                return httpx.stream(method, url, json=json_body, timeout=timeout, headers=self._headers())
            return httpx.request(method, url, json=json_body, timeout=timeout, headers=self._headers())
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(str(exc)) from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError(str(exc)) from exc

    def model_list(self) -> list[str]:
        try:
            response = self._request("GET", "/models")
            if response.status_code >= 400:
                return []
            payload = response.json()
            data = payload.get("data", []) if isinstance(payload, dict) else []
            models = [item.get("id") or item.get("name") for item in data if isinstance(item, dict)]
            return [model for index, model in enumerate(models) if model and model not in models[:index]]
        except Exception:
            return []

    def health_check(self) -> bool:
        return bool(self.model_list())

    def _parse_usage(self, payload: Dict[str, Any]) -> Dict[str, int]:
        usage = payload.get("usage") if isinstance(payload, dict) else None
        if not isinstance(usage, dict):
            return {}
        return _usage_dict(
            prompt_tokens=usage.get("prompt_tokens", 0) or 0,
            completion_tokens=usage.get("completion_tokens", 0) or 0,
            total_tokens=usage.get("total_tokens", 0) or 0,
        )

    def _candidate_model(self, model: str | None) -> str:
        models = self.model_list()
        if model and (not models or model in models):
            return model
        if self.default_model and (not models or self.default_model in models):
            return self.default_model
        if models:
            return models[0]
        return model or self.default_model

    def generate(self, prompt: str, model: str | None = None, *, stream: bool = False) -> ProviderResult:
        model_name = self._candidate_model(model)
        payload: Dict[str, Any] = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "stream": stream,
            "temperature": 0.2,
            "max_tokens": 2048,
        }
        response = self._request("POST", "/chat/completions", json_body=payload, stream=stream)

        try:
            if stream:
                content_parts: list[str] = []
                with response as streamed:
                    for line in streamed.iter_lines():
                        if not line:
                            continue
                        text = line.decode("utf-8") if isinstance(line, bytes) else line
                        if text.startswith("data: "):
                            text = text.removeprefix("data: ").strip()
                        if text == "[DONE]":
                            break
                        chunk = json.loads(text)
                        choices = chunk.get("choices", []) if isinstance(chunk, dict) else []
                        if choices:
                            delta = choices[0].get("delta", {})
                            part = delta.get("content") or ""
                            if part:
                                content_parts.append(part)
                text = "".join(content_parts).strip()
                if not text:
                    raise ProviderError("Empty NVIDIA streaming response")
                return ProviderResult(text=text, model=model_name, usage={})

            payload = response.json()
            choices = payload.get("choices", []) if isinstance(payload, dict) else []
            text = ""
            if choices:
                message = choices[0].get("message", {})
                text = (message.get("content") or "").strip()
            if not text:
                raise ProviderError("Empty NVIDIA response")
            return ProviderResult(text=text, model=model_name, usage=self._parse_usage(payload))
        finally:
            response.close()

    def generate_structured(self, prompt: str, schema_model: Type[T], model: str | None = None, *, stream: bool = False) -> ProviderResult:
        model_name = self._candidate_model(model)
        payload: Dict[str, Any] = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "stream": stream,
            "temperature": 0.2,
            "max_tokens": 2048,
                "nvext": {"guided_json": _json_schema(schema_model)},
            }
        response = self._request("POST", "/chat/completions", json_body=payload, stream=stream)
        try:
            if stream:
                content_parts: list[str] = []
                with response as streamed:
                    for line in streamed.iter_lines():
                        if not line:
                            continue
                        text = line.decode("utf-8") if isinstance(line, bytes) else line
                        if text.startswith("data: "):
                            text = text.removeprefix("data: ").strip()
                        if text == "[DONE]":
                            break
                        chunk = json.loads(text)
                        choices = chunk.get("choices", []) if isinstance(chunk, dict) else []
                        if choices:
                            delta = choices[0].get("delta", {})
                            part = delta.get("content") or ""
                            if part:
                                content_parts.append(part)
                text = "".join(content_parts).strip()
                if not text:
                    raise ProviderError("Empty NVIDIA structured streaming response")
                return ProviderResult(text=text, model=model_name, usage={})

            payload = response.json()
            choices = payload.get("choices", []) if isinstance(payload, dict) else []
            text = ""
            if choices:
                message = choices[0].get("message", {})
                text = (message.get("content") or "").strip()
            if not text:
                raise ProviderError("Empty NVIDIA structured response")
            extracted = _extract_json_fragment(text)
            try:
                schema_model.model_validate_json(extracted)
                return ProviderResult(text=extracted, model=model_name, usage=self._parse_usage(payload))
            except Exception:
                fallback = self.generate(prompt, model=model_name, stream=stream)
                extracted = _extract_json_fragment(fallback.text)
                schema_model.model_validate_json(extracted)
                return ProviderResult(text=extracted, model=fallback.model, usage=fallback.usage, streamed=fallback.streamed)
        finally:
            response.close()


class OllamaProvider(AIProvider):
    name = "ollama"

    def __init__(self) -> None:
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self.preferred_models = [model.strip() for model in settings.OLLAMA_PREFERRED_MODELS.split(",") if model.strip()]

    def _normalize_model(self, model: str) -> str:
        return model.removesuffix(":latest").strip()

    def _base_urls(self) -> list[str]:
        urls = [self.base_url]
        parsed = urlparse(self.base_url)
        if parsed.hostname in {"localhost", "127.0.0.1"}:
            fallback = parsed._replace(netloc=f"host.docker.internal:{parsed.port}" if parsed.port else "host.docker.internal")
            fallback_url = urlunparse(fallback)
            if fallback_url not in urls:
                urls.append(fallback_url)
        return urls

    def _request(self, method: str, path: str, *, json_body: Dict[str, Any] | None = None, stream: bool = False):
        timeout = settings.AI_REQUEST_TIMEOUT_SECONDS
        last_error: Exception | None = None
        for base_url in self._base_urls():
            url = f"{base_url}{path}"
            try:
                if stream:
                    return httpx.stream(method, url, json=json_body, timeout=timeout)
                return httpx.request(method, url, json=json_body, timeout=timeout)
            except httpx.TimeoutException as exc:
                last_error = exc
                continue
            except httpx.HTTPError as exc:
                last_error = exc
                continue
        if isinstance(last_error, httpx.TimeoutException):
            raise ProviderTimeoutError(str(last_error)) from last_error
        raise ProviderUnavailableError(str(last_error) if last_error else "Ollama is unavailable")

    def model_list(self) -> list[str]:
        try:
            response = self._request("GET", "/api/tags")
            if response.status_code >= 400:
                return []
            payload = response.json()
            models = []
            for item in payload.get("models", []) if isinstance(payload, dict) else []:
                if not isinstance(item, dict):
                    continue
                name = item.get("name") or item.get("model")
                if name:
                    models.append(name)
            ordered: list[str] = []
            seen: set[str] = set()
            for preferred in self.preferred_models:
                preferred_norm = self._normalize_model(preferred)
                for model in models:
                    if self._normalize_model(model) == preferred_norm and model not in seen:
                        ordered.append(model)
                        seen.add(model)
                        break
            for model in models:
                if model not in seen:
                    ordered.append(model)
                    seen.add(model)
            return ordered
        except Exception:
            return []

    def health_check(self) -> bool:
        return bool(self.model_list())

    def _candidate_model(self, model: str | None) -> str:
        models = self.model_list()
        if model:
            normalized = self._normalize_model(model)
            for candidate in models:
                if self._normalize_model(candidate) == normalized:
                    return candidate
            if not models:
                return model
        for preferred in self.preferred_models:
            preferred_norm = self._normalize_model(preferred)
            for candidate in models:
                if self._normalize_model(candidate) == preferred_norm:
                    return candidate
            if not models:
                return preferred
        if models:
            return models[0]
        return model or "mistral"

    def _parse_usage(self, payload: Dict[str, Any]) -> Dict[str, int]:
        if not isinstance(payload, dict):
            return {}
        prompt_tokens = payload.get("prompt_eval_count", 0) or 0
        completion_tokens = payload.get("eval_count", 0) or 0
        total_tokens = prompt_tokens + completion_tokens
        return _usage_dict(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

    def _stream_text(self, response: httpx.Response) -> str:
        parts: list[str] = []
        with response as streamed:
            for line in streamed.iter_lines():
                if not line:
                    continue
                text = line.decode("utf-8") if isinstance(line, bytes) else line
                payload = json.loads(text)
                message = payload.get("message", {}) if isinstance(payload, dict) else {}
                part = message.get("content") or payload.get("response") or ""
                if part:
                    parts.append(part)
                if payload.get("done"):
                    break
        return "".join(parts).strip()

    def generate(self, prompt: str, model: str | None = None, *, stream: bool = False) -> ProviderResult:
        model_name = self._candidate_model(model)
        payload = {"model": model_name, "messages": [{"role": "user", "content": prompt}], "stream": stream}
        response = self._request("POST", "/api/chat", json_body=payload, stream=stream)
        try:
            if stream:
                text = self._stream_text(response)
                if not text:
                    raise ProviderError("Empty Ollama streaming response")
                return ProviderResult(text=text, model=model_name, usage={})

            payload = response.json()
            message = payload.get("message", {}) if isinstance(payload, dict) else {}
            text = (message.get("content") or payload.get("response") or "").strip()
            if not text:
                raise ProviderError("Empty Ollama response")
            return ProviderResult(text=text, model=model_name, usage=self._parse_usage(payload))
        finally:
            response.close()

    def generate_structured(self, prompt: str, schema_model: Type[T], model: str | None = None, *, stream: bool = False) -> ProviderResult:
        model_name = self._candidate_model(model)
        payload = {
            "model": model_name,
            "prompt": prompt,
            "format": _json_schema(schema_model),
            "stream": stream,
        }
        response = self._request("POST", "/api/generate", json_body=payload, stream=stream)
        try:
            if stream:
                text = self._stream_text(response)
                if not text:
                    raise ProviderError("Empty Ollama structured streaming response")
                return ProviderResult(text=text, model=model_name, usage={})

            payload = response.json()
            text = (payload.get("response") or "").strip()
            if not text:
                message = payload.get("message", {}) if isinstance(payload, dict) else {}
                text = (message.get("content") or "").strip()
            if not text:
                raise ProviderError("Empty Ollama structured response")
            return ProviderResult(text=_extract_json_fragment(text), model=model_name, usage=self._parse_usage(payload))
        finally:
            response.close()

    def embed_text(self, text: str, model: str | None = None) -> list[float]:
        model_name = model or "nomic-embed-text"
        response = self._request(
            "POST",
            "/api/embeddings",
            json_body={"model": model_name, "prompt": (text or "").strip()},
        )
        try:
            payload = response.json()
            embedding = None
            if isinstance(payload, dict):
                embedding = payload.get("embedding") or payload.get("embeddings")
                if isinstance(embedding, dict):
                    embedding = embedding.get("embedding")
            if not embedding:
                raise ProviderError("Empty Ollama embedding response")
            return [float(value) for value in embedding]
        finally:
            response.close()
