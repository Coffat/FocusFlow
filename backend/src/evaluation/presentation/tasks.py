import importlib
from datetime import datetime
from typing import Any

from src.execution.public_api import NotificationServicePort
from src.shared_kernel.infrastructure.worker.broker import broker


# Executable Taskiq task delegating to execution sweeper (scheduled via execution module at 17:05 UTC = 00:05 UTC+7 to prevent duplicate daily execution).
@broker.task
async def sweep_overdue_tasks_and_anti_loop(
    *,
    session_factory: Any = None,
    now: datetime | None = None,
    notification_service: NotificationServicePort | None = None,
) -> int:
    """Detect overdue tasks and enforce anti-loop cap on Domino Shift (UC-16, UC-17, UC-25)."""
    tasks_mod = importlib.import_module("src.execution.presentation.tasks")
    fn = getattr(tasks_mod, "sweep_overdue_tasks_and_anti_loop")
    res: int = await fn(
        session_factory=session_factory,
        now=now,
        notification_service=notification_service,
    )
    return res
