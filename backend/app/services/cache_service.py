from abc import ABC, abstractmethod
from typing import Any, Optional

class BaseCacheService(ABC):
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    def set(self, key: str, value: Any, expiration: int = 3600) -> None:
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        pass

import redis
import json
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class InMemoryCacheService(BaseCacheService):
    def __init__(self):
        self._cache = {}

    def get(self, key: str) -> Optional[Any]:
        return self._cache.get(key)

    def set(self, key: str, value: Any, expiration: int = 3600) -> None:
        self._cache[key] = value

    def delete(self, key: str) -> None:
        if key in self._cache:
            del self._cache[key]

class RedisCacheService(BaseCacheService):
    def __init__(self):
        try:
            self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            self.redis_client.ping()
            self._is_active = True
        except Exception as e:
            logger.warning(f"Redis not available, falling back to in-memory cache: {e}")
            self._is_active = False
            self.fallback = InMemoryCacheService()

    def get(self, key: str) -> Optional[Any]:
        if not self._is_active:
            return self.fallback.get(key)
        try:
            val = self.redis_client.get(key)
            if val:
                return json.loads(val)
        except Exception as e:
            logger.warning(f"Redis get error: {e}")
        return None

    def set(self, key: str, value: Any, expiration: int = 3600) -> None:
        if not self._is_active:
            return self.fallback.set(key, value, expiration)
        try:
            self.redis_client.setex(key, expiration, json.dumps(value))
        except Exception as e:
            logger.warning(f"Redis set error: {e}")

    def delete(self, key: str) -> None:
        if not self._is_active:
            return self.fallback.delete(key)
        try:
            self.redis_client.delete(key)
        except Exception as e:
            logger.warning(f"Redis delete error: {e}")

cache = RedisCacheService()
