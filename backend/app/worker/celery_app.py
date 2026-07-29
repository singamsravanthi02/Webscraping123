from __future__ import annotations

import logging

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_routes={
        "app.worker.tasks.*": {"queue": "main-queue"},
    },
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_always_eager=False,
    task_eager_propagates=False,
)

beat_schedule = {
    "learning-refresh-every-6-hours": {
        "task": "app.worker.tasks.daily_recommendation_scheduler",
        "schedule": 21600.0,
    },
    "analytics-update-hourly": {
        "task": "app.worker.tasks.update_dashboard_analytics_task",
        "schedule": 3600.0,
    },
    "notification-digest-daily": {
        "task": "app.worker.tasks.send_notification_digest_task",
        "schedule": crontab(hour=8, minute=0),
    },
    "resume-reanalysis-nightly": {
        "task": "app.worker.tasks.reanalyze_resumes_task",
        "schedule": crontab(hour=2, minute=30),
    },
    "career-dna-refresh-nightly": {
        "task": "app.worker.tasks.refresh_career_dna_task",
        "schedule": crontab(hour=3, minute=0),
    },
}

if settings.JOB_ENABLE_BACKGROUND_REFRESH:
    beat_schedule["refresh-ai-job-discovery"] = {
        "task": "app.worker.tasks.refresh_ai_job_recommendations_task",
        "schedule": float(settings.JOB_REFRESH_INTERVAL_MINUTES * 60),
    }
    beat_schedule["scrape-jobs"] = {
        "task": "app.worker.tasks.aggregate_and_process_jobs_task",
        "schedule": 3600.0,
    }

celery_app.conf.beat_schedule = beat_schedule
