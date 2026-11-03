import pytest
from uuid6 import uuid7

from src.planning.application.ports.sse_job_port import SseJobNotFoundError
from src.shared_kernel.infrastructure.sse.job_store import (
    InMemorySseJobStore,
    RedisSseJobStore,
)


@pytest.mark.asyncio
async def test_sse_job_store_idempotency_last_event_id_replay_and_idor() -> None:
    """Verify 2-Stage SSE Job Store (ADR-005):
    - Idempotency-Key deduplication scoped by (user_id, operation, idempotency_key)
    - Monotonic event IDs (1..N) & Last-Event-ID replay
    - IDOR protection (accessing another user's job raises SseJobNotFoundError -> 404)
    """
    store = InMemorySseJobStore()
    owner_id = uuid7()
    attacker_id = uuid7()
    roadmap_id = uuid7()
    reservation_id = uuid7()
    job_id = uuid7()

    # 1. Create job with Idempotency-Key
    created = await store.create_job(
        job_id=job_id,
        user_id=owner_id,
        roadmap_id=roadmap_id,
        reservation_id=reservation_id,
        job_type="MILESTONE_GEN",
        operation=f"MILESTONE_GEN:{roadmap_id}",
        idempotency_key="idem-key-001",
    )
    assert created.job_id == job_id
    assert created.status == "RESERVED"

    # 2. Idempotency lookup for same user & operation returns existing job
    hit = await store.get_by_idempotency_key(
        user_id=owner_id,
        operation=f"MILESTONE_GEN:{roadmap_id}",
        idempotency_key="idem-key-001",
    )
    assert hit is not None
    assert hit.job_id == job_id

    # Different user with same idempotency_key does NOT collide
    miss_other_user = await store.get_by_idempotency_key(
        user_id=attacker_id,
        operation=f"MILESTONE_GEN:{roadmap_id}",
        idempotency_key="idem-key-001",
    )
    assert miss_other_user is None

    # 3. IDOR check: attacker cannot read owner's job
    with pytest.raises(SseJobNotFoundError):
        await store.get_job_for_user(job_id=job_id, user_id=attacker_id)

    # 4. Append events (stage -> validation_retry -> completed)
    await store.append_event(
        job_id=job_id,
        event="stage",
        data={"stage": "RESERVED", "progress": 10},
    )
    await store.append_event(
        job_id=job_id,
        event="validation_retry",
        data={"stage": "VALIDATING_TIER_1_2_3", "progress": 60, "retry_attempt": 1},
    )
    await store.append_event(
        job_id=job_id,
        event="completed",
        data={"stage": "COMPLETED", "progress": 100, "payload": {"ok": True}},
    )

    # Full stream (last_event_id=None) yields all 3 events
    all_events = [
        ev async for ev in store.stream_events(job_id=job_id, user_id=owner_id, last_event_id=None)
    ]
    assert [e.id for e in all_events] == [1, 2, 3]
    assert [e.event for e in all_events] == ["stage", "validation_retry", "completed"]

    # Reconnect replay with Last-Event-ID = 1 yields only events 2 and 3
    replayed = [
        ev async for ev in store.stream_events(job_id=job_id, user_id=owner_id, last_event_id=1)
    ]
    assert [e.id for e in replayed] == [2, 3]
    assert [e.event for e in replayed] == ["validation_retry", "completed"]
    assert "id: 2\nevent: validation_retry\ndata:" in replayed[0].format_sse()

    # RedisSseJobStore fallback works seamlessly in unit test environment
    redis_store = RedisSseJobStore(redis_url="redis://localhost:6399/0", fallback_store=store)
    fetched = await redis_store.get_job_for_user(job_id=job_id, user_id=owner_id)
    assert fetched.job_id == job_id
