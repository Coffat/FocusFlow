import os
from celery import Celery

broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

celery_app = Celery(
    "focusflow_worker",
    broker=broker_url,
    backend=result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Ho_Chi_Minh",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes hard limit
    # Celery Beat Periodic Tasks Configuration (ADR-004)
    beat_schedule={
        # OS-07: Scan interrupted study sessions without heartbeat every 5 minutes
        "scan-interrupted-sessions-every-5-min": {
            "task": "src.infrastructure.workers.tasks.scan_interrupted_sessions",
            "schedule": 300.0,
        },
        # FR-ADAPT-001: Scan overdue pending tasks daily at 00:01
        "scan-daily-overdue-tasks": {
            "task": "src.infrastructure.workers.tasks.scan_overdue_tasks",
            "schedule": 60.0 * 60.0 * 24.0,  # daily
        },
    },
)


@celery_app.task(name="src.infrastructure.workers.tasks.scan_interrupted_sessions")
def scan_interrupted_sessions() -> str:
    """Mock periodic task for scanning interrupted sessions (OS-07 / BUSR-09)."""
    return "Scan completed successfully."


@celery_app.task(name="src.infrastructure.workers.tasks.scan_overdue_tasks")
def scan_overdue_tasks() -> str:
    """Mock periodic task for marking overdue tasks (FR-ADAPT-001)."""
    return "Daily overdue scan completed."
