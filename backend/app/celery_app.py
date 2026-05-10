import os
from celery import Celery

# Use Redis from environment or default to localhost
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "game_simulation",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks.simulations"]
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
)

if __name__ == "__main__":
    celery_app.start()
