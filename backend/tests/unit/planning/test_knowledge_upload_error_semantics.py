from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import UUID

import httpx
import pytest
from fastapi import FastAPI
from uuid6 import uuid7

from src.planning.application.use_cases.knowledge_source_use_cases import (
    CreateKnowledgeSourceUseCase,
)
from src.planning.domain.models.goal import Goal, GoalStatus
from src.planning.domain.models.knowledge_source import KnowledgeSource
from src.planning.presentation.deps import (
    get_create_knowledge_source_use_case,
    get_current_learner_id,
)
from src.planning.presentation.routers import router as planning_router
from src.planning.presentation.tasks import dispatch_ingest_knowledge_source


class _FakeGoalRepo:
    def __init__(self, goals: dict[tuple[UUID, UUID], Goal]) -> None:
        self._goals = goals

    async def get_by_id_for_user(self, goal_id: UUID, user_id: UUID) -> Goal | None:
        return self._goals.get((goal_id, user_id))


class _FakeKnowledgeSourceRepo:
    async def save_source(self, source: KnowledgeSource) -> KnowledgeSource:
        return source


class _FakeFileStore:
    def __init__(self) -> None:
        self.saved: dict[str, bytes] = {}

    async def save(self, source_id: UUID, ext: str, content: bytes) -> str:
        uri = f"mem://{source_id}.{ext}"
        self.saved[uri] = content
        return uri

    async def read(self, uri: str) -> bytes:
        return self.saved[uri]

    async def delete(self, uri: str) -> None:
        self.saved.pop(uri, None)


class _FakeUoW:
    async def __aenter__(self) -> _FakeUoW:
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None

    async def commit(self) -> None:
        return None


class _ExplodingUseCase:
    async def create_file(self, **kwargs: Any) -> KnowledgeSource:
        raise RuntimeError("unexpected storage subsystem failure")

    async def create_url(self, **kwargs: Any) -> KnowledgeSource:
        raise RuntimeError("unexpected database failure")


def _make_goal(user_id: UUID, goal_id: UUID) -> Goal:
    now = datetime.now(UTC)
    return Goal(
        id=goal_id,
        user_id=user_id,
        title="Backend Architecture",
        raw_description="Learn hexagonal architecture",
        target_date=None,
        status=GoalStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )


def _build_test_app(
    *,
    user_id: UUID,
    use_case: Any,
) -> FastAPI:
    app = FastAPI()
    app.include_router(planning_router)
    app.dependency_overrides[get_current_learner_id] = lambda: user_id
    app.dependency_overrides[get_create_knowledge_source_use_case] = lambda: use_case
    return app


@pytest.mark.asyncio
async def test_upload_knowledge_file_validation_errors_return_422() -> None:
    user_id = uuid7()
    goal_id = uuid7()
    use_case = CreateKnowledgeSourceUseCase(
        goal_repository=_FakeGoalRepo({(goal_id, user_id): _make_goal(user_id, goal_id)}),  # type: ignore[arg-type]
        source_repository=_FakeKnowledgeSourceRepo(),  # type: ignore[arg-type]
        file_store=_FakeFileStore(),
        uow=_FakeUoW(),  # type: ignore[arg-type]
        max_file_bytes=64,
    )
    app = _build_test_app(user_id=user_id, use_case=use_case)

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Unsupported extension (.exe)
        resp_ext = await client.post(
            f"/api/v1/planning/goals/{goal_id}/knowledge-sources/files",
            files={"file": ("malware.exe", b"MZ\x90\x00", "application/octet-stream")},
            data={"title": "Bad Binary"},
        )
        assert resp_ext.status_code == 422

        # 2. Empty file
        resp_empty = await client.post(
            f"/api/v1/planning/goals/{goal_id}/knowledge-sources/files",
            files={"file": ("empty.txt", b"", "text/plain")},
            data={"title": "Empty"},
        )
        assert resp_empty.status_code == 422

        # 3. Oversized file (> max_file_bytes=64)
        resp_big = await client.post(
            f"/api/v1/planning/goals/{goal_id}/knowledge-sources/files",
            files={"file": ("huge.txt", b"a" * 128, "text/plain")},
            data={"title": "Oversized"},
        )
        assert resp_big.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_url",
    [
        "file:///etc/passwd",
        "http://user:pass@example.com/doc.txt",
        "https:///missing-host",
    ],
)
async def test_add_knowledge_url_unsafe_urls_return_422(bad_url: str) -> None:
    user_id = uuid7()
    goal_id = uuid7()
    use_case = CreateKnowledgeSourceUseCase(
        goal_repository=_FakeGoalRepo({(goal_id, user_id): _make_goal(user_id, goal_id)}),  # type: ignore[arg-type]
        source_repository=_FakeKnowledgeSourceRepo(),  # type: ignore[arg-type]
        file_store=_FakeFileStore(),
        uow=_FakeUoW(),  # type: ignore[arg-type]
        max_file_bytes=1024,
    )
    app = _build_test_app(user_id=user_id, use_case=use_case)

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/planning/goals/{goal_id}/knowledge-sources/urls",
            json={"title": "Unsafe Resource", "url": bad_url},
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_knowledge_upload_missing_or_unauthorized_goal_returns_404() -> None:
    owner_id = uuid7()
    other_user_id = uuid7()
    goal_id = uuid7()
    use_case = CreateKnowledgeSourceUseCase(
        goal_repository=_FakeGoalRepo({(goal_id, owner_id): _make_goal(owner_id, goal_id)}),  # type: ignore[arg-type]
        source_repository=_FakeKnowledgeSourceRepo(),  # type: ignore[arg-type]
        file_store=_FakeFileStore(),
        uow=_FakeUoW(),  # type: ignore[arg-type]
        max_file_bytes=1024,
    )
    app = _build_test_app(user_id=other_user_id, use_case=use_case)

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp_file = await client.post(
            f"/api/v1/planning/goals/{goal_id}/knowledge-sources/files",
            files={"file": ("notes.txt", b"hello", "text/plain")},
            data={"title": "Notes"},
        )
        assert resp_file.status_code == 404

        resp_url = await client.post(
            f"/api/v1/planning/goals/{goal_id}/knowledge-sources/urls",
            json={"title": "Docs", "url": "https://example.com/docs"},
        )
        assert resp_url.status_code == 404


@pytest.mark.asyncio
async def test_knowledge_upload_unexpected_runtime_error_bubbles_as_500() -> None:
    user_id = uuid7()
    goal_id = uuid7()
    app = _build_test_app(user_id=user_id, use_case=_ExplodingUseCase())

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp_file = await client.post(
            f"/api/v1/planning/goals/{goal_id}/knowledge-sources/files",
            files={"file": ("notes.txt", b"hello", "text/plain")},
            data={"title": "Notes"},
        )
        assert resp_file.status_code == 500

        resp_url = await client.post(
            f"/api/v1/planning/goals/{goal_id}/knowledge-sources/urls",
            json={"title": "Docs", "url": "https://example.com/docs"},
        )
        assert resp_url.status_code == 500


@pytest.mark.asyncio
async def test_dispatch_ingest_knowledge_source_inline_fallback_swallows_and_logs_error() -> None:
    source_id = str(uuid7())
    user_id = str(uuid7())

    inline_mock = AsyncMock(
        side_effect=RuntimeError("ingestion failed after persisting FAILED"),
    )
    inline_mock.kiq = AsyncMock(side_effect=ConnectionError("broker unreachable"))

    with patch("src.planning.presentation.tasks.ingest_knowledge_source", new=inline_mock):
        # Must not raise so 202 Accepted upload does not turn into 500
        await dispatch_ingest_knowledge_source(source_id=source_id, user_id=user_id)
        inline_mock.assert_awaited_once_with(source_id=source_id, user_id=user_id)
