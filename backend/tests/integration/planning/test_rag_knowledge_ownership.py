from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import UUID

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy import delete
from uuid6 import uuid7

from src.account.infrastructure.orm.user_orm import UserORM
from src.account.infrastructure.security.jwt_token_provider import JwtTokenProvider
from src.main import app
from src.planning.infrastructure.orm.knowledge_orm import KnowledgeChunkORM, KnowledgeSourceORM
from src.planning.infrastructure.orm.planning_orm import GoalORM
from src.shared_kernel.infrastructure.database.session import async_session_factory


async def _seed_user_and_goal(prefix: str) -> tuple[UUID, UUID]:
    user_id = uuid7()
    goal_id = uuid7()
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
                raw_description="RAG ownership integration test goal",
                status="ACTIVE",
                prior_knowledge_level="BEGINNER",
                created_at=now,
                updated_at=now,
            )
        )
        await session.commit()
    return user_id, goal_id


async def _cleanup_users(user_ids: list[UUID], goal_ids: list[UUID]) -> None:
    async with async_session_factory() as session:
        await session.execute(
            delete(KnowledgeChunkORM).where(KnowledgeChunkORM.goal_id.in_(goal_ids))
        )
        await session.execute(
            delete(KnowledgeSourceORM).where(KnowledgeSourceORM.goal_id.in_(goal_ids))
        )
        await session.execute(delete(GoalORM).where(GoalORM.id.in_(goal_ids)))
        await session.execute(delete(UserORM).where(UserORM.id.in_(user_ids)))
        await session.commit()


def _auth_headers(user_id: UUID) -> dict[str, str]:
    token = JwtTokenProvider().create_access_token(
        user_id=user_id,
        email=f"user_{user_id.hex}@focusflow.vn",
        role="LEARNER",
        tier="FREE",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_cross_user_rag_knowledge_source_ownership_enforced() -> None:
    user_a, goal_a = await _seed_user_and_goal("rag_owner_a")
    user_b, goal_b = await _seed_user_and_goal("rag_other_b")

    try:
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        with patch(
            "src.planning.presentation.routers.dispatch_ingest_knowledge_source",
            new=AsyncMock(),
        ):
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                # 1. User A uploads a valid TXT file to Goal A -> 202
                resp_upload_a = await client.post(
                    f"/api/v1/planning/goals/{goal_a}/knowledge-sources/files",
                    headers=_auth_headers(user_a),
                    files={"file": ("notes.txt", b"User A study notes", "text/plain")},
                    data={"title": "User A Notes"},
                )
                assert resp_upload_a.status_code == 202
                source_a_id = resp_upload_a.json()["id"]

                # 2. User A can list and read their own knowledge sources -> 200
                resp_list_a = await client.get(
                    f"/api/v1/planning/goals/{goal_a}/knowledge-sources",
                    headers=_auth_headers(user_a),
                )
                assert resp_list_a.status_code == 200
                assert any(item["id"] == source_a_id for item in resp_list_a.json())

                resp_get_a = await client.get(
                    f"/api/v1/planning/knowledge-sources/{source_a_id}",
                    headers=_auth_headers(user_a),
                )
                assert resp_get_a.status_code == 200
                assert resp_get_a.json()["id"] == source_a_id

                # 3. User B CANNOT upload a file to User A's goal -> 404
                resp_upload_b = await client.post(
                    f"/api/v1/planning/goals/{goal_a}/knowledge-sources/files",
                    headers=_auth_headers(user_b),
                    files={"file": ("evil.txt", b"User B injection", "text/plain")},
                    data={"title": "Injected"},
                )
                assert resp_upload_b.status_code == 404

                # 4. User B CANNOT add a URL to User A's goal -> 404
                resp_url_b = await client.post(
                    f"/api/v1/planning/goals/{goal_a}/knowledge-sources/urls",
                    headers=_auth_headers(user_b),
                    json={"title": "Injected URL", "url": "https://example.com/docs"},
                )
                assert resp_url_b.status_code == 404

                # 5. User B CANNOT list knowledge sources of User A's goal -> 404
                resp_list_b = await client.get(
                    f"/api/v1/planning/goals/{goal_a}/knowledge-sources",
                    headers=_auth_headers(user_b),
                )
                assert resp_list_b.status_code == 404

                # 6. User B CANNOT read User A's knowledge source by source_id -> 404
                resp_get_b = await client.get(
                    f"/api/v1/planning/knowledge-sources/{source_a_id}",
                    headers=_auth_headers(user_b),
                )
                assert resp_get_b.status_code == 404
    finally:
        await _cleanup_users([user_a, user_b], [goal_a, goal_b])
