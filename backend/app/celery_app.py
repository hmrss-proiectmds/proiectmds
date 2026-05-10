import os
from celery import Celery
from app.config import settings

# Use Redis from centralized settings
REDIS_URL = settings.REDIS_URL

celery_app = Celery(
    "game_simulation",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

# Load tasks after the app is defined to avoid circular imports
celery_app.conf.update(
    imports=["app.tasks.simulations"]
)

# Optional configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max for simulations
    broker_connection_retry_on_startup=True,
)

if __name__ == "__main__":
    celery_app.start()
