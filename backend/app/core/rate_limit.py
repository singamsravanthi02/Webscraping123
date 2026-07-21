from __future__ import annotations

import logging

import redis.asyncio as redis
from fastapi import FastAPI, Request
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

from app.core.config import settings

logger = logging.getLogger(__name__)


async def init_rate_limiter(app: FastAPI):
    try:
        redis_conn = redis.from_url(
            settings.REDIS_URL,
            encoding="utf8",
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
            retry_on_timeout=True,
        )
        await redis_conn.ping()
        await FastAPILimiter.init(redis_conn)
        logger.info("FastAPILimiter initialized.")
    except Exception as exc:
        logger.warning("Rate limiter unavailable: %s", exc)


def RateLimiterWrapper(times: int, seconds: int):
    if FastAPILimiter.redis is None:
        async def _noop(request: Request):
            return None

        return _noop
    return RateLimiter(times=times, seconds=seconds)
