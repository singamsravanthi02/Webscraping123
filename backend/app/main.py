from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.exceptions import domain_exception_handler, DomainException
from app.core.rate_limit import close_rate_limiter, init_rate_limiter
from app.api.v1 import auth, users, jobs, assessments, interviews, learning, notifications, knowledge, analytics, ai
from prometheus_fastapi_instrumentator import Instrumentator
from asgi_correlation_id import CorrelationIdMiddleware

import logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_rate_limiter(app)
    try:
        yield
    finally:
        try:
            await close_rate_limiter()
        except Exception as exc:
            logger.warning("Failed to close rate limiter cleanly: %s", exc)


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)

origins = list(dict.fromkeys([settings.FRONTEND_URL, "http://localhost:3000", "http://127.0.0.1:3000"]))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

app.add_exception_handler(DomainException, domain_exception_handler)

instrumentator = Instrumentator().instrument(app)
instrumentator.expose(app, endpoint="/metrics")

app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(jobs.router, prefix=f"{settings.API_V1_STR}/jobs", tags=["jobs"])
app.include_router(assessments.router, prefix=f"{settings.API_V1_STR}/assessments", tags=["assessments"])
app.include_router(interviews.router, prefix=f"{settings.API_V1_STR}/interviews", tags=["interviews"])
app.include_router(learning.router, prefix=f"{settings.API_V1_STR}/learning", tags=["learning"])
app.include_router(notifications.router, prefix=f"{settings.API_V1_STR}/notifications", tags=["notifications"])
app.include_router(knowledge.router, prefix=f"{settings.API_V1_STR}/knowledge", tags=["knowledge"])
app.include_router(analytics.router, prefix=f"{settings.API_V1_STR}/analytics", tags=["analytics"])
app.include_router(ai.router, prefix=f"{settings.API_V1_STR}/ai", tags=["ai"])


@app.get("/health")
def health_check():
    return {"status": "ok", "message": "SPIP API is running"}
