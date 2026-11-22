from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy import delete, select
from uuid6 import uuid7

from src.account.infrastructure.orm.user_orm import UserORM
from src.account.infrastructure.security.jwt_token_provider import JwtTokenProvider
from src.execution.infrastructure.orm.session_orm import StudyNoteORM, StudySessionORM
from src.execution.infrastructure.orm.task_orm import TaskDependencyORM, TaskORM
from src.main import app
from src.planning.infrastructure.orm.planning_orm import GoalORM, MilestoneORM, RoadmapORM
from src.shared_kernel.infrastructure.database.session import async_session_factory


async def _seed_user_with_task_and_session(prefix: str) -> tuple[UUID, UUID, UUID, UUID]:
    user_id = uuid7()
    goal_id = uuid7()
    roadmap_id = uuid7()
    milestone_id = uuid7()
    task_id = uuid7()
    session_id = uuid7()
    now = datetime.now(UTC)

    async with async_session_factory() as session:
        session.add(
            UserORM(
                id=user_id,
                email=f"{prefix}_{user_id.hex}@focusflow.vn",
                password_hash="argon2id$mockhash",
                full_name=f"User {prefix}",
                timezone="Asia/Ho_Chi_Minh",
                role="LEARNER",
                tier="FREE",
                is_locked=False,
            )
        )
        await session.flush()

        session.add(
            GoalORM(
                id=goal_id,
                user_id=user_id,
                title=f"Goal {prefix}",
                raw_description="IDOR test goal",
                status="ACTIVE",
                prior_knowledge_level="BEGINNER",
                created_at=now,
                updated_at=now,
            )
        )
        await session.flush()

        session.add(
            RoadmapORM(
                id=roadmap_id,
                goal_id=goal_id,
                user_id=user_id,
                title=f"Roadmap {prefix}",
                status="ACTIVE",
                created_at=now,
                updated_at=now,
            )
        )
        await session.flush()

        session.add(
            MilestoneORM(
                id=milestone_id,
                roadmap_id=roadmap_id,
                sequence_order=1,
                title=f"Milestone {prefix}",
                status="IN_PROGRESS",
                created_at=now,
                updated_at=now,
            )
        )
        await session.flush()

        session.add(
            TaskORM(
                id=task_id,
                roadmap_id=roadmap_id,
                milestone_id=milestone_id,
                title=f"Task {prefix}",
                estimated_minutes=45,
                status="TODO",
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            StudySessionORM(
                id=session_id,
                user_id=user_id,
                roadmap_id=roadmap_id,
                started_at=now,
                ended_at=now,
                planned_minutes=45,
                actual_minutes=45,
                status="COMPLETED",
                last_heartbeat_at=now,
                session_mode="STANDARD",
                pending_takeaway=False,
                created_at=now,
                updated_at=now,
            )
        )
        await session.commit()

    return user_id, roadmap_id, task_id, session_id


async def _cleanup_users(user_ids: list[UUID]) -> None:
    async with async_session_factory() as session:
        await session.execute(delete(StudyNoteORM).where(StudyNoteORM.user_id.in_(user_ids)))
        await session.execute(delete(StudySessionORM).where(StudySessionORM.user_id.in_(user_ids)))
        await session.execute(delete(UserORM).where(UserORM.id.in_(user_ids)))
        await session.commit()


def _auth_headers(user_id: UUID) -> dict[str, str]:
    token = JwtTokenProvider().create_access_token(
        user_id=user_id,
        email=f"idor_{user_id.hex}@focusflow.vn",
        role="LEARNER",
        tier="FREE",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_sticky_note_cross_user_idor_and_crud_regression() -> None:
    user_a, _, task_a, session_a = await _seed_user_with_task_and_session("idor_a")
    user_b, _, task_b, _ = await _seed_user_with_task_and_session("idor_b")
    nonexistent_task = uuid7()

    try:
        headers_a = _auth_headers(user_a)
        headers_b = _auth_headers(user_b)

        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # 1. Valid User A creates sticky note linked to own task & session
            create_a = await client.post(
                "/api/v1/sessions/notes",
                headers=headers_a,
                json={
                    "title": "User A Note",
                    "body": "Private study takeaway",
                    "color": "amber",
                    "task_id": str(task_a),
                    "origin_session_id": str(session_a),
                },
            )
            assert create_a.status_code == 201, create_a.text
            note_a_id = create_a.json()["id"]
            assert create_a.json()["task_id"] == str(task_a)

            # 2. User B creating sticky note with User A's task_id -> 404 (not created)
            idor_create_task = await client.post(
                "/api/v1/sessions/notes",
                headers=headers_b,
                json={
                    "title": "Stolen Task Ref",
                    "body": "Trying to link User A task",
                    "task_id": str(task_a),
                },
            )
            assert idor_create_task.status_code == 404, idor_create_task.text

            # Nonexistent task_id returns exact same 404 & code (no UUID existence oracle)
            missing_create_task = await client.post(
                "/api/v1/sessions/notes",
                headers=headers_b,
                json={
                    "title": "Missing Task Ref",
                    "body": "Trying nonexistent task",
                    "task_id": str(nonexistent_task),
                },
            )
            assert missing_create_task.status_code == 404, missing_create_task.text
            assert idor_create_task.json()["code"] == missing_create_task.json()["code"]

            # 3. User B creating sticky note with User A's origin_session_id -> 404
            idor_create_sess = await client.post(
                "/api/v1/sessions/notes",
                headers=headers_b,
                json={
                    "title": "Stolen Session Ref",
                    "body": "Trying to link User A session",
                    "origin_session_id": str(session_a),
                },
            )
            assert idor_create_sess.status_code == 404, idor_create_sess.text

            # Verify ZERO notes were created for User B in DB
            async with async_session_factory() as db:
                b_notes = list(
                    (await db.execute(select(StudyNoteORM).where(StudyNoteORM.user_id == user_b)))
                    .scalars()
                    .all()
                )
                assert b_notes == []

            # 4. User B listing sticky notes -> sees ZERO of User A's notes
            list_b = await client.get("/api/v1/sessions/notes", headers=headers_b)
            assert list_b.status_code == 200, list_b.text
            assert list_b.json() == []

            # 5. User B updating User A's sticky note -> 404
            upd_b = await client.patch(
                f"/api/v1/sessions/notes/{note_a_id}",
                headers=headers_b,
                json={"title": "Tampered by B"},
            )
            assert upd_b.status_code == 404, upd_b.text

            # 6. User B deleting User A's sticky note -> 404
            del_b = await client.delete(
                f"/api/v1/sessions/notes/{note_a_id}",
                headers=headers_b,
            )
            assert del_b.status_code == 404, del_b.text

            # 7. Valid User A read / update / delete regression still passes
            list_a = await client.get("/api/v1/sessions/notes", headers=headers_a)
            assert list_a.status_code == 200
            assert len(list_a.json()) == 1
            assert list_a.json()[0]["title"] == "User A Note"

            upd_a = await client.patch(
                f"/api/v1/sessions/notes/{note_a_id}",
                headers=headers_a,
                json={"title": "User A Updated", "pinned": False},
            )
            assert upd_a.status_code == 200, upd_a.text
            assert upd_a.json()["title"] == "User A Updated"
            assert upd_a.json()["pinned"] is False

            del_a = await client.delete(
                f"/api/v1/sessions/notes/{note_a_id}",
                headers=headers_a,
            )
            assert del_a.status_code == 204, del_a.text

            list_a_after = await client.get("/api/v1/sessions/notes", headers=headers_a)
            assert list_a_after.status_code == 200
            assert list_a_after.json() == []

            # Ensure User B can still create a valid note on own task_b
            create_b_own = await client.post(
                "/api/v1/sessions/notes",
                headers=headers_b,
                json={"title": "User B Own Note", "task_id": str(task_b)},
            )
            assert create_b_own.status_code == 201, create_b_own.text
    finally:
        await _cleanup_users([user_a, user_b])


@pytest.mark.asyncio
async def test_mixed_ownership_session_start_and_task_dependency_return_404_no_oracle() -> None:
    user_a, _, task_a, _ = await _seed_user_with_task_and_session("oracle_a")
    user_b, _, task_b, _ = await _seed_user_with_task_and_session("oracle_b")
    nonexistent_task = uuid7()

    try:
        headers_b = _auth_headers(user_b)
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # 1. StartStudySessionUseCase mixing own task_b + foreign task_a -> 404 (NOT 409!)
            start_mixed_foreign = await client.post(
                "/api/v1/sessions/start",
                headers=headers_b,
                json={"task_ids": [str(task_b), str(task_a)], "session_mode": "STANDARD"},
            )
            start_mixed_missing = await client.post(
                "/api/v1/sessions/start",
                headers=headers_b,
                json={
                    "task_ids": [str(task_b), str(nonexistent_task)],
                    "session_mode": "STANDARD",
                },
            )
            assert start_mixed_foreign.status_code == 404, start_mixed_foreign.text
            assert start_mixed_missing.status_code == 404, start_mixed_missing.text
            assert start_mixed_foreign.json()["code"] == start_mixed_missing.json()["code"]

            # 2. AddTaskDependencyUseCase: own successor + foreign predecessor -> 404 (NOT 409!)
            dep_foreign_pred = await client.post(
                f"/api/v1/tasks/{task_b}/dependencies",
                headers=headers_b,
                json={"predecessor_id": str(task_a), "is_mandatory": True},
            )
            dep_missing_pred = await client.post(
                f"/api/v1/tasks/{task_b}/dependencies",
                headers=headers_b,
                json={"predecessor_id": str(nonexistent_task), "is_mandatory": True},
            )
            assert dep_foreign_pred.status_code == 404, dep_foreign_pred.text
            assert dep_missing_pred.status_code == 404, dep_missing_pred.text
            assert dep_foreign_pred.json()["code"] == dep_missing_pred.json()["code"]

            # 3. AddTaskDependencyUseCase: foreign successor + own predecessor -> 404 (NOT 409!)
            dep_foreign_succ = await client.post(
                f"/api/v1/tasks/{task_a}/dependencies",
                headers=headers_b,
                json={"predecessor_id": str(task_b), "is_mandatory": True},
            )
            assert dep_foreign_succ.status_code == 404, dep_foreign_succ.text
            assert dep_foreign_succ.json()["code"] == dep_missing_pred.json()["code"]

        # Confirm no dependency row was persisted
        async with async_session_factory() as db:
            deps = list(
                (
                    await db.execute(
                        select(TaskDependencyORM).where(
                            TaskDependencyORM.successor_id.in_([task_a, task_b])
                        )
                    )
                )
                .scalars()
                .all()
            )
            assert deps == []
    finally:
        await _cleanup_users([user_a, user_b])
