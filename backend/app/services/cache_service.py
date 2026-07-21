from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)


class BaseCacheService(ABC):
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError

    @abstractmethod
    def set(self, key: str, value: Any, expiration: int = 3600) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, key: str) -> None:
        raise NotImplementedError


class RedisCacheService(BaseCacheService):
    def __init__(self) -> None:
        self.redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
            retry_on_timeout=True,
        )

    def get(self, key: str) -> Optional[Any]:
        try:
            raw_value = self.redis_client.get(key)
            if raw_value is None:
                return None
            return json.loads(raw_value)
        except Exception as exc:
            logger.warning("Redis cache read failed: %s", exc)
            return None

    def set(self, key: str, value: Any, expiration: int = 3600) -> None:
        try:
            self.redis_client.setex(key, expiration, json.dumps(value))
        except Exception as exc:
            logger.warning("Redis cache write failed: %s", exc)

    def delete(self, key: str) -> None:
        try:
            self.redis_client.delete(key)
        except Exception as exc:
            logger.warning("Redis cache delete failed: %s", exc)


cache = RedisCacheService()
