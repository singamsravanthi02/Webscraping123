from __future__ import annotations

import json
import logging
from functools import wraps
from typing import Any, Callable

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

def cache_response(ttl: int = 300, key_prefix: str = "cache"):
    """
    A decorator to cache FastAPI endpoint responses in Redis.
    Note: In a real implementation, this requires access to the request object 
    to build dynamic keys. For simplicity, we use static prefix + kwargs.
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key based on function name and kwargs
            # (Simplified for demonstration)
            kwargs_str = "_".join([f"{k}:{v}" for k, v in kwargs.items() if isinstance(v, (str, int))])
            cache_key = f"{key_prefix}:{func.__name__}:{kwargs_str}"
            
            cached_data = await redis_client.get(cache_key)
            if cached_data is not None:
                logger.debug("Cache hit for %s", cache_key)
                return json.loads(cached_data)

            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache the result
            if isinstance(result, (dict, list)):
                await redis_client.setex(cache_key, ttl, json.dumps(result))
            elif hasattr(result, "model_dump"):
                await redis_client.setex(cache_key, ttl, json.dumps(result.model_dump()))
                
            return result
        return wrapper
    return decorator
