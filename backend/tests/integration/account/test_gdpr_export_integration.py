from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy import delete
from uuid6 import uuid7

from src.account.domain.models.availability import AvailabilityProfile
from src.account.infrastructure.orm.learner_memory_orm import LearnerMemoryItemORM
from src.account.infrastructure.orm.user_orm import (
    LearnerProfileORM,
    UserORM,
    WebCalTokenORM,
)
from src.account.infrastructure.repositories.availability_repository import (
    SqlAlchemyAvailabilityRepository,
)
from src.account.infrastructure.security.jwt_token_provider import JwtTokenProvider
from src.execution.infrastructure.orm.session_orm import StudySessionORM
from src.execution.infrastructure.orm.task_orm import TaskORM
from src.main import app
from src.planning.infrastructure.orm.planning_orm import GoalORM, MilestoneORM, RoadmapORM
from src.shared_kernel.infrastructure.database.session import async_session_factory


async def _seed_gdpr_users() -> tuple[UUID, UUID, dict[str, str]]:
    user_a_id = uuid7()
    user_b_id = uuid7()
    now = datetime.now(UTC)

    secrets_markers = {
        "password_hash_a": "argon2id$super_secret_hash_user_a_999",
        "token_hash_a": "a" * 64,
        "oauth_refresh_a": "fernet_encrypted_refresh_token_secret_xyz",
        "user_b_roadmap": "User B Secret Roadmap Title",
        "user_b_task": "User B Confidential Task",
        "user_b_email": f"gdpr_b_{user_b_id.hex}@focusflow.vn",
    }

    async with async_session_factory() as session:
        session.add_all(
            [
                UserORM(
                    id=user_a_id,
                    email=f"gdpr_a_{user_a_id.hex}@focusflow.vn",
                    password_hash=secrets_markers["password_hash_a"],
                    full_name="GDPR Learner A",
                    timezone="Asia/Ho_Chi_Minh",
                    role="LEARNER",
                    tier="FREE",
                    is_locked=False,
                ),
                UserORM(
                    id=user_b_id,
                    email=secrets_markers["user_b_email"],
                    password_hash="argon2id$secret_hash_b",
                    full_name="GDPR Learner B",
                    timezone="UTC",
                    role="LEARNER",
                    tier="PREMIUM",
                    is_locked=False,
                ),
            ]
        )
        await session.flush()

        # User A sensitive token (must NEVER appear in export)
        session.add(
            WebCalTokenORM(
                id=uuid7(),
                user_id=user_a_id,
                token_hash=secrets_markers["token_hash_a"],
                oauth_refresh_token_encrypted=secrets_markers["oauth_refresh_a"],
                is_active=True,
            )
        )

        # User A LearnerProfile
        session.add(
            LearnerProfileORM(
                id=uuid7(),
                user_id=user_a_id,
                optimal_focus_duration_mins=50,
                peak_productivity_slots=["MORNING", "EVENING"],
                estimation_bias_factor=Decimal("1.10"),
                weekly_completion_rate=Decimal("82.50"),
                total_completed_sessions=4,
                is_cold_start=False,
            )
        )

        # User A LearnerMemory
        session.add(
            LearnerMemoryItemORM(
                id=uuid7(),
                user_id=user_a_id,
                memory_key="preferred_session_style",
                value={"style": "deep_work"},
                category="PREFERENCE",
                epistemic_level="EXPLICIT",
                confidence=Decimal("1.00"),
                sample_size=1,
                evidence=[],
                status="CONFIRMED",
            )
        )

        # User A Availability
        avail_repo = SqlAlchemyAvailabilityRepository(session)
        await avail_repo.save(AvailabilityProfile.create_default(user_a_id))

        # User A Goal, Roadmap, Milestone, Task, StudySession
        goal_a = uuid7()
        rm_a = uuid7()
        ms_a = uuid7()
        session.add(
            GoalORM(
                id=goal_a,
                user_id=user_a_id,
                title="User A Python Mastery",
                raw_description="Learn Python async",
                status="ACTIVE",
            )
        )
        await session.flush()
        session.add(
            RoadmapORM(
                id=rm_a,
                user_id=user_a_id,
                goal_id=goal_a,
                title="User A Async Roadmap",
                status="ACTIVE",
            )
        )
        await session.flush()
        session.add(
            MilestoneORM(
                id=ms_a,
                roadmap_id=rm_a,
                title="Asyncio Fundamentals",
                sequence_order=1,
                status="IN_PROGRESS",
            )
        )
        await session.flush()
        session.add(
            TaskORM(
                id=uuid7(),
                roadmap_id=rm_a,
                milestone_id=ms_a,
                title="Build Event Loop Demo",
                estimated_minutes=60,
                scheduled_date=now.date(),
                status="COMPLETED",
                completed_at=now,
            )
        )
        session.add(
            StudySessionORM(
                id=uuid7(),
                user_id=user_a_id,
                roadmap_id=rm_a,
                started_at=now - timedelta(minutes=50),
                ended_at=now,
                planned_minutes=50,
                actual_minutes=50,
                status="COMPLETED",
                session_mode="STANDARD",
            )
        )

        # User B Goal, Roadmap, Milestone, Task, StudySession (MUST NEVER LEAK TO USER A)
        goal_b = uuid7()
        rm_b = uuid7()
        ms_b = uuid7()
        session.add(
            GoalORM(
                id=goal_b,
                user_id=user_b_id,
                title="User B Goal",
                raw_description="Confidential",
                status="ACTIVE",
            )
        )
        await session.flush()
        session.add(
            RoadmapORM(
                id=rm_b,
                user_id=user_b_id,
                goal_id=goal_b,
                title=secrets_markers["user_b_roadmap"],
                status="ACTIVE",
            )
        )
        await session.flush()
        session.add(
            MilestoneORM(
                id=ms_b,
                roadmap_id=rm_b,
                title="Secret Milestone B",
                sequence_order=1,
                status="PENDING",
            )
        )
        await session.flush()
        session.add(
            TaskORM(
                id=uuid7(),
                roadmap_id=rm_b,
                milestone_id=ms_b,
                title=secrets_markers["user_b_task"],
                estimated_minutes=45,
                scheduled_date=now.date(),
                status="TODO",
            )
        )
        session.add(
            StudySessionORM(
                id=uuid7(),
                user_id=user_b_id,
                roadmap_id=rm_b,
                started_at=now - timedelta(minutes=30),
                ended_at=now,
                planned_minutes=30,
                actual_minutes=30,
                status="COMPLETED",
                session_mode="STANDARD",
            )
        )

        await session.commit()

    return user_a_id, user_b_id, secrets_markers


async def _cleanup_users(*user_ids: UUID) -> None:
    async with async_session_factory() as session:
        await session.execute(delete(UserORM).where(UserORM.id.in_(list(user_ids))))
        await session.commit()


@pytest.mark.asyncio
async def test_gdpr_export_contains_real_data_zero_secrets_and_strict_idor_isolation() -> None:
    user_a_id, user_b_id, markers = await _seed_gdpr_users()
    token_a = JwtTokenProvider.create_access_token(
        user_id=user_a_id,
        email=f"gdpr_a_{user_a_id.hex}@focusflow.vn",
        role="LEARNER",
        tier="FREE",
    )
    headers_a = {"Authorization": f"Bearer {token_a}"}

    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/account/export", headers=headers_a)
            assert resp.status_code == 200
            data = resp.json()

            assert data["schema_version"] == "1.0"
            assert data["exported_at"] is not None
            assert data["user"]["id"] == str(user_a_id)
            assert data["user"]["full_name"] == "GDPR Learner A"
            assert data["learner_profile"]["optimal_focus_duration_mins"] == 50
            assert len(data["learner_memory"]) == 1
            assert data["learner_memory"][0]["memory_key"] == "preferred_session_style"
            assert data["availability"] is not None
            assert data["availability"]["mode"] == "MODE_A"

            assert len(data["roadmaps"]) == 1
            assert data["roadmaps"][0]["title"] == "User A Async Roadmap"
            assert data["tasks_count"] == 1
            assert len(data["tasks"]) == 1
            assert data["tasks"][0]["title"] == "Build Event Loop Demo"
            assert data["study_sessions_count"] == 1
            assert len(data["study_sessions"]) == 1
            assert data["study_sessions"][0]["actual_minutes"] == 50
            assert data["analytics_summary"]["completed_tasks_count"] == 1

            # Strict secret scrubbing & IDOR isolation checks
            serialized = json.dumps(data)
            assert "password_hash" not in serialized
            assert "token_hash" not in serialized
            assert "oauth_refresh_token_encrypted" not in serialized
            assert markers["password_hash_a"] not in serialized
            assert markers["token_hash_a"] not in serialized
            assert markers["oauth_refresh_a"] not in serialized
            assert markers["user_b_roadmap"] not in serialized
            assert markers["user_b_task"] not in serialized
            assert markers["user_b_email"] not in serialized
            assert str(user_b_id) not in serialized
    finally:
        await _cleanup_users(user_a_id, user_b_id)
