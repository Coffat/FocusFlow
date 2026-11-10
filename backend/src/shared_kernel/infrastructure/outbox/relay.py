from datetime import UTC, datetime

from sqlalchemy import select

from src.shared_kernel.infrastructure.database.session import async_session_factory
from src.shared_kernel.infrastructure.outbox.models import OutboxEventORM
from src.shared_kernel.infrastructure.worker.broker import broker


@broker.task(schedule=[{"cron": "* * * * *"}])
async def relay_pending_outbox_events(batch_size: int = 100) -> int:
    """Poll PENDING outbox_events with FOR UPDATE SKIP LOCKED and mark PUBLISHED."""
    async with async_session_factory() as session:
        stmt = (
            select(OutboxEventORM)
            .where(OutboxEventORM.status == "PENDING")
            .order_by(OutboxEventORM.created_at.asc())
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
        result = await session.execute(stmt)
        events = list(result.scalars().all())
        now = datetime.now(UTC)
        for event in events:
            event.status = "PUBLISHED"
            event.published_at = now
        if events:
            await session.commit()
        return len(events)
