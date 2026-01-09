"""Celery application configuration"""

from celery import Celery
from app.config import settings

# Create Celery app
celery_app = Celery(
    "loman_ai",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.jobs.tasks",
    ],
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Beat schedule for periodic tasks
    beat_schedule={
        "send-reservation-reminders": {
            "task": "send_reservation_reminders",
            "schedule": 3600.0,  # Every hour
        },
        "cleanup-old-calls": {
            "task": "cleanup_old_calls",
            "schedule": 86400.0,  # Daily
        },
    },
)

