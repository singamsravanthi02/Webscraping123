from __future__ import annotations

from fastapi import APIRouter, Depends
import redis

from app.api.dependencies.auth import get_current_active_user
from app.core.config import settings
from app.domain.ai_orchestration.gateway import gateway
from app.domain.ai_orchestration.providers import provider_health
from app.domain.users.models import User

router = APIRouter()


def _queue_size() -> int:
    client = None
    try:
        client = redis.from_url(settings.REDIS_URL)
        return int(client.llen("celery"))
    except Exception:
        return 0
    finally:
        if client is not None:
            client.close()


@router.get("/providers")
def get_ai_providers(current_user: User = Depends(get_current_active_user)):
    provider_rows = gateway.provider_status()
    diagnostics = gateway.routing_snapshot()
    return {
        "configured_mode": settings.AI_PROVIDER.upper(),
        "active_provider": provider_health.active_provider,
        "queue_size": _queue_size(),
        "routing_decision": diagnostics.get("last_routing_decision", {}),
        "routing_matrix": diagnostics.get("routing_matrix", {}),
        "totals": {
            "requests": sum(item.get("request_count", 0) for item in provider_rows),
            "failures": sum(item.get("failure_count", 0) for item in provider_rows),
            "fallbacks": sum(item.get("fallback_count", 0) for item in provider_rows),
            "cache_hits": sum(item.get("cache_hit_count", 0) for item in provider_rows),
            "avg_latency_ms": round(
                sum((item.get("average_latency_ms", 0.0) or 0.0) for item in provider_rows) / max(len(provider_rows), 1),
                1,
            ),
        },
        "providers": provider_rows,
    }
