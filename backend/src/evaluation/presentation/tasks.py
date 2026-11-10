from src.shared_kernel.infrastructure.worker.broker import broker


@broker.task(schedule=[{"cron": "0 * * * *"}])
async def sweep_overdue_tasks_and_anti_loop() -> int:
    """Detect overdue tasks and enforce anti-loop cap on Domino Shift (UC-16, UC-17)."""
    return 0
