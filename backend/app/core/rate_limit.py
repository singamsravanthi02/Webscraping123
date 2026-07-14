import redis.asyncio as redis
from fastapi import FastAPI, Depends, Request
from app.core.config import settings
import logging

_rate_limiter_enabled = False

async def init_rate_limiter(app: FastAPI):
    global _rate_limiter_enabled
    try:
        redis_conn = redis.from_url(settings.REDIS_URL, encoding="utf8", decode_responses=True)
        await redis_conn.ping()
        from fastapi_limiter import FastAPILimiter
        await FastAPILimiter.init(redis_conn)
        _rate_limiter_enabled = True
        logging.info("FastAPILimiter initialized.")
    except Exception as e:
        logging.warning(f"Failed to initialize FastAPILimiter: {e}. Rate limiting will be disabled gracefully.")

def RateLimiterWrapper(times: int, seconds: int):
    async def _rate_limit_dependency(request: Request):
        if not _rate_limiter_enabled:
            return
        from fastapi_limiter.depends import RateLimiter
        return await RateLimiter(times=times, seconds=seconds)(request)
    return _rate_limit_dependency
