from __future__ import annotations

import httpx
import pytest
from httpx import ASGITransport
from uuid6 import uuid7

from src.account.infrastructure.orm.user_orm import UserORM
from src.account.presentation.deps import get_current_user
from src.main import app


def _make_user(role: str) -> UserORM:
    return UserORM(
        id=uuid7(),
        email=f"{role.lower()}@focusflow.vn",
        password_hash="argon2id$mockhash",
        full_name=f"Test {role}",
        timezone="Asia/Ho_Chi_Minh",
        role=role,
        tier="FREE",
        is_locked=False,
    )


@pytest.mark.asyncio
async def test_admin_status_unauthenticated_returns_401() -> None:
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/v1/account/admin/status")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_status_learner_returns_403() -> None:
    learner = _make_user("LEARNER")
    app.dependency_overrides[get_current_user] = lambda: learner
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/account/admin/status")
            assert resp.status_code == 403
            assert resp.json()["detail"] == "Admin privileges required"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_admin_status_admin_returns_200() -> None:
    admin = _make_user("ADMIN")
    app.dependency_overrides[get_current_user] = lambda: admin
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/account/admin/status")
            assert resp.status_code == 200
            assert resp.json() == {
                "enabled": False,
                "role": "ADMIN",
                "message": "Cổng quản trị chưa được kích hoạt trong bản phát hành hiện tại.",
            }
    finally:
        app.dependency_overrides.pop(get_current_user, None)
