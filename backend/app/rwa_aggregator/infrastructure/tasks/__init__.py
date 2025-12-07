# Celery tasks - price fetcher, alert checker, daily summaries
from app.rwa_aggregator.infrastructure.tasks.celery_app import celery_app

__all__ = ["celery_app"]
