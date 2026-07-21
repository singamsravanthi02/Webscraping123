from __future__ import annotations

import logging
from collections.abc import Callable

import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Request, status

from app.core.config import settings

logger = logging.getLogger(__name__)
_redis_client: redis.Redis | None = None


async def init_rate_limiter(app: FastAPI):
    try:
        global _redis_client
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf8",
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
            retry_on_timeout=True,
        )
        await _redis_client.ping()
        logger.info("Rate limiter initialized.")
    except Exception as exc:
        logger.warning("Rate limiter unavailable: %s", exc)


async def close_rate_limiter():
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None


def RateLimiterWrapper(times: int, seconds: int):
    async def _check(request: Request):
        if _redis_client is None:
            return None

        client = request.client.host if request.client else "unknown"
        key = f"ratelimit:{client}:{request.method}:{request.url.path}"
        current = await _redis_client.incr(key)
        if current == 1:
            await _redis_client.expire(key, seconds)
        if current > times:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too Many Requests",
                headers={"Retry-After": str(seconds)},
            )

    return _check
