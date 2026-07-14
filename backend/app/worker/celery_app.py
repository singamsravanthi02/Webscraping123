from celery import Celery
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

celery_app = Celery(
    "worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.worker.tasks"]
)

def _redis_available() -> bool:
    try:
        import redis

        client = redis.Redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=1,
            socket_timeout=1,
            retry_on_timeout=False,
        )
        return bool(client.ping())
    except Exception as exc:
        logger.warning("Redis unavailable for Celery; running tasks eagerly: %s", exc)
        return False

celery_app.conf.update(
    task_routes={
        "app.worker.tasks.*": {"queue": "main-queue"}
    },
    task_acks_late=True, # Prevent task loss if worker crashes mid-execution
    worker_prefetch_multiplier=1, # Fair distribution of tasks across workers
    task_always_eager=not _redis_available(),
    task_eager_propagates=False,
    beat_schedule={
        "refresh-ai-job-discovery-every-6-hours": {
            "task": "app.worker.tasks.refresh_ai_job_recommendations_task",
            "schedule": 21600.0,
        }
    },
)
