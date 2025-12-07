"""Celery application configuration."""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "rwa_aggregator",
    broker=str(settings.celery_broker_url),
    backend=str(settings.celery_result_backend),
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    worker_prefetch_multiplier=1,  # Fair task distribution
    # Beat schedule for periodic tasks
    beat_schedule={
        "fetch-prices-every-30s": {
            "task": "app.rwa_aggregator.infrastructure.tasks.price_tasks.fetch_all_prices",
            "schedule": settings.price_poll_interval_seconds,
        },
        "check-alerts-every-5m": {
            "task": "app.rwa_aggregator.infrastructure.tasks.alert_tasks.check_alerts",
            "schedule": settings.alert_check_interval_seconds,
        },
    },
)

# Auto-discover tasks from the tasks module
celery_app.autodiscover_tasks(
    [
        "app.rwa_aggregator.infrastructure.tasks",
    ]
)

