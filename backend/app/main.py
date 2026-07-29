from contextlib import asynccontextmanager
import re

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
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

local_dev_origin_regex = None
if settings.ENVIRONMENT.lower() in {"local", "development"}:
    local_dev_origin_regex = (
        r"^https?://(?:localhost|127\.0\.0\.1|"
        r"10(?:\.\d{1,3}){3}|"
        r"192\.168(?:\.\d{1,3}){2}|"
        r"172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2}):\d{2,5}$"
    )


def _is_allowed_origin(origin: str | None) -> bool:
    if not origin:
        return False
    if origin in origins:
        return True
    if local_dev_origin_regex and re.fullmatch(local_dev_origin_regex, origin):
        return True
    return False

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=local_dev_origin_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
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


@app.middleware("http")
async def allow_private_network_preflight(request: Request, call_next):
    if (
        request.method == "OPTIONS"
        and request.headers.get("access-control-request-private-network") == "true"
        and _is_allowed_origin(request.headers.get("origin"))
    ):
        requested_headers = request.headers.get("access-control-request-headers", "content-type")
        response = PlainTextResponse("OK", status_code=200)
        response.headers["Access-Control-Allow-Origin"] = request.headers["origin"]
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE"
        response.headers["Access-Control-Allow-Headers"] = requested_headers
        response.headers["Access-Control-Allow-Private-Network"] = "true"
        response.headers["Access-Control-Max-Age"] = "600"
        response.headers["Vary"] = "Origin"
        return response

    return await call_next(request)

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
