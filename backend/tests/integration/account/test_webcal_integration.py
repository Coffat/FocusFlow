from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy import delete, select
from uuid6 import uuid7

from src.account.infrastructure.orm.user_orm import UserORM, WebCalTokenORM
from src.account.infrastructure.security.jwt_token_provider import JwtTokenProvider
from src.main import app
from src.planning.infrastructure.orm.planning_orm import (
    GoalORM,
    OfficialScheduleORM,
    RoadmapORM,
    ScheduleBlockORM,
)
from src.shared_kernel.infrastructure.database.session import async_session_factory


async def _seed_webcal_fixtures() -> tuple[UUID, UUID, UUID, UUID, UUID]:
    owner_id = uuid7()
    other_user_id = uuid7()
    owner_active_block_id = uuid7()
    owner_paused_block_id = uuid7()
    other_block_id = uuid7()

    now = datetime.now(UTC)
    today = now.date()
    start_dt = datetime(today.year, today.month, today.day, 9, 0, tzinfo=UTC) + timedelta(days=1)
    end_dt = start_dt + timedelta(minutes=60)

    async with async_session_factory() as session:
        session.add_all(
            [
                UserORM(
                    id=owner_id,
                    email=f"webcal_owner_{owner_id.hex}@focusflow.vn",
                    password_hash="argon2id$mockhash",
                    full_name="WebCal Owner",
                    timezone="Asia/Ho_Chi_Minh",
                    role="LEARNER",
                    tier="FREE",
                    is_locked=False,
                ),
                UserORM(
                    id=other_user_id,
                    email=f"webcal_other_{other_user_id.hex}@focusflow.vn",
                    password_hash="argon2id$mockhash",
                    full_name="WebCal Other",
                    timezone="UTC",
                    role="LEARNER",
                    tier="FREE",
                    is_locked=False,
                ),
            ]
        )
        await session.flush()

        # Owner active roadmap + official schedule + block
        owner_goal_id = uuid7()
        owner_active_rm_id = uuid7()
        owner_active_sched_id = uuid7()
        session.add(
            GoalORM(
                id=owner_goal_id,
                user_id=owner_id,
                title="System Design",
                raw_description="Learn distributed systems",
                status="ACTIVE",
            )
        )
        await session.flush()
        session.add(
            RoadmapORM(
                id=owner_active_rm_id,
                user_id=owner_id,
                goal_id=owner_goal_id,
                title="System Design Active",
                status="ACTIVE",
            )
        )
        await session.flush()
        session.add(
            OfficialScheduleORM(
                id=owner_active_sched_id,
                roadmap_id=owner_active_rm_id,
                total_sessions=1,
                total_planned_minutes=60,
            )
        )
        await session.flush()
        session.add(
            ScheduleBlockORM(
                id=owner_active_block_id,
                roadmap_id=owner_active_rm_id,
                official_schedule_id=owner_active_sched_id,
                block_type="STUDY",
                block_date=start_dt.date(),
                start_time=start_dt,
                end_time=end_dt,
                scheduled_duration_minutes=60,
                status="PLANNED",
                placement_rationale="Morning deep focus session",
            )
        )

        # Owner PAUSED roadmap + block (must be excluded from feed)
        owner_paused_rm_id = uuid7()
        owner_paused_sched_id = uuid7()
        session.add(
            RoadmapORM(
                id=owner_paused_rm_id,
                user_id=owner_id,
                goal_id=owner_goal_id,
                title="Paused Roadmap",
                status="PAUSED",
            )
        )
        await session.flush()
        session.add(
            OfficialScheduleORM(
                id=owner_paused_sched_id,
                roadmap_id=owner_paused_rm_id,
                total_sessions=1,
                total_planned_minutes=60,
            )
        )
        await session.flush()
        session.add(
            ScheduleBlockORM(
                id=owner_paused_block_id,
                roadmap_id=owner_paused_rm_id,
                official_schedule_id=owner_paused_sched_id,
                block_type="STUDY",
                block_date=start_dt.date(),
                start_time=start_dt + timedelta(hours=2),
                end_time=end_dt + timedelta(hours=2),
                scheduled_duration_minutes=60,
                status="PLANNED",
            )
        )

        # Other user's ACTIVE roadmap + block (must NEVER appear in owner's feed)
        other_goal_id = uuid7()
        other_rm_id = uuid7()
        other_sched_id = uuid7()
        session.add(
            GoalORM(
                id=other_goal_id,
                user_id=other_user_id,
                title="Other Secret Goal",
                raw_description="Private study plan",
                status="ACTIVE",
            )
        )
        await session.flush()
        session.add(
            RoadmapORM(
                id=other_rm_id,
                user_id=other_user_id,
                goal_id=other_goal_id,
                title="Other User Secret Roadmap",
                status="ACTIVE",
            )
        )
        await session.flush()
        session.add(
            OfficialScheduleORM(
                id=other_sched_id,
                roadmap_id=other_rm_id,
                total_sessions=1,
                total_planned_minutes=60,
            )
        )
        await session.flush()
        session.add(
            ScheduleBlockORM(
                id=other_block_id,
                roadmap_id=other_rm_id,
                official_schedule_id=other_sched_id,
                block_type="STUDY",
                block_date=start_dt.date(),
                start_time=start_dt,
                end_time=end_dt,
                scheduled_duration_minutes=60,
                status="PLANNED",
            )
        )

        await session.commit()

    return (
        owner_id,
        other_user_id,
        owner_active_block_id,
        owner_paused_block_id,
        other_block_id,
    )


async def _cleanup_users(*user_ids: UUID) -> None:
    async with async_session_factory() as session:
        await session.execute(delete(UserORM).where(UserORM.id.in_(list(user_ids))))
        await session.commit()


def _extract_raw_token(feed_url: str) -> str:
    match = re.search(r"/api/v1/feeds/([0-9a-f]{64})\.ics$", feed_url)
    assert match is not None, f"Unexpected feed_url format: {feed_url}"
    return match.group(1)


@pytest.mark.asyncio
async def test_webcal_token_lifecycle_sha256_storage_and_ics_feed() -> None:
    (
        owner_id,
        other_user_id,
        owner_active_block_id,
        owner_paused_block_id,
        other_block_id,
    ) = await _seed_webcal_fixtures()

    owner_jwt = JwtTokenProvider.create_access_token(
        user_id=owner_id,
        email=f"webcal_owner_{owner_id.hex}@focusflow.vn",
        role="LEARNER",
        tier="FREE",
    )
    owner_headers = {"Authorization": f"Bearer {owner_jwt}"}

    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # 0. Initial status -> no active token
            status_resp = await client.get("/api/v1/account/calendar/webcal", headers=owner_headers)
            assert status_resp.status_code == 200
            assert status_resp.json()["has_active_token"] is False
            assert status_resp.json()["is_active"] is False

            # 1. Create / rotate token
            rotate_resp = await client.post(
                "/api/v1/account/calendar/webcal/rotate", headers=owner_headers
            )
            assert rotate_resp.status_code == 200
            rotate_data = rotate_resp.json()
            raw_token_1 = _extract_raw_token(rotate_data["feed_url"])
            assert rotate_data["rotated_at"] is not None

            # Verify DB stores ONLY 64-char hex SHA-256 hash (never plaintext)
            expected_hash_1 = hashlib.sha256(raw_token_1.encode("utf-8")).hexdigest()
            async with async_session_factory() as session:
                token_row = (
                    await session.execute(
                        select(WebCalTokenORM).where(WebCalTokenORM.user_id == owner_id)
                    )
                ).scalar_one()
                assert token_row.token_hash == expected_hash_1
                assert token_row.token_hash != raw_token_1
                assert len(token_row.token_hash) == 64
                assert token_row.is_active is True

            # Verify status endpoint never leaks plaintext token
            active_status = await client.get(
                "/api/v1/account/calendar/webcal", headers=owner_headers
            )
            assert active_status.status_code == 200
            assert active_status.json()["has_active_token"] is True
            assert raw_token_1 not in active_status.text

            # 2. Fetch ICS feed -> valid RFC 5545 with owner's ACTIVE block only
            feed_resp = await client.get(f"/api/v1/feeds/{raw_token_1}.ics")
            assert feed_resp.status_code == 200
            assert "text/calendar" in feed_resp.headers["content-type"]
            assert feed_resp.headers.get("cache-control") == "no-store, private"
            assert feed_resp.headers.get("referrer-policy") == "no-referrer"
            assert feed_resp.headers.get("x-content-type-options") == "nosniff"
            ics = feed_resp.text
            assert "BEGIN:VCALENDAR\r\n" in ics
            assert "END:VCALENDAR\r\n" in ics
            assert "X-WR-TIMEZONE:Asia/Ho_Chi_Minh\r\n" in ics
            assert "BEGIN:VEVENT\r\n" in ics
            assert f"UID:{owner_active_block_id}@focusflow.app\r\n" in ics
            assert f"UID:{owner_paused_block_id}@focusflow.app" not in ics
            assert f"UID:{other_block_id}@focusflow.app" not in ics
            assert "Other User Secret Roadmap" not in ics

            # 3. Rotate token -> old token immediately 404, new token 200
            rotate_resp_2 = await client.post(
                "/api/v1/account/calendar/webcal/rotate", headers=owner_headers
            )
            assert rotate_resp_2.status_code == 200
            raw_token_2 = _extract_raw_token(rotate_resp_2.json()["feed_url"])
            assert raw_token_2 != raw_token_1

            old_feed_resp = await client.get(f"/api/v1/feeds/{raw_token_1}.ics")
            assert old_feed_resp.status_code == 404

            new_feed_resp = await client.get(f"/api/v1/feeds/{raw_token_2}.ics")
            assert new_feed_resp.status_code == 200

            # 4. Revoke token -> token immediately returns 404
            revoke_resp = await client.delete(
                "/api/v1/account/calendar/webcal", headers=owner_headers
            )
            assert revoke_resp.status_code == 200
            assert revoke_resp.json()["is_active"] is False

            revoked_feed_resp = await client.get(f"/api/v1/feeds/{raw_token_2}.ics")
            assert revoked_feed_resp.status_code == 404

            # 5. Invalid / random tokens return 404
            assert (await client.get("/api/v1/feeds/not-a-valid-token.ics")).status_code == 404
            assert (await client.get(f"/api/v1/feeds/{'a' * 64}.ics")).status_code == 404
    finally:
        await _cleanup_users(owner_id, other_user_id)


@pytest.mark.asyncio
async def test_webcal_security_headers_rfc5545_vietnamese_folding_and_rate_limit() -> None:
    from src.account.domain.services.ics_builder import IcsEventItem, build_ics_calendar

    # 1. RFC 5545 Section 3.1 75-octet UTF-8 folding for long Vietnamese titles
    long_vi_title = (
        "Ôn tập chuyên sâu Kiến trúc Hệ thống Phân tán & Thuật toán Đồng thuận "
        "Raft, Paxos, và Thiết kế Cơ sở Dữ liệu Chịu lỗi Cao"
    )
    now = datetime.now(UTC)
    ics_payload = build_ics_calendar(
        events=[
            IcsEventItem(
                uid="vi-test@focusflow.app",
                summary=long_vi_title,
                description="Ghi chú chi tiết về bài học tiếng Việt có dấu dài hơn 75 byte UTF-8 để kiểm tra gấp dòng chuẩn RFC 5545.",
                start_time=now,
                end_time=now + timedelta(minutes=60),
            )
        ],
        timezone="Asia/Ho_Chi_Minh",
        generated_at=now,
    )
    raw_lines = ics_payload.split("\r\n")
    for raw_line in raw_lines:
        assert len(raw_line.encode("utf-8")) <= 75, f"Line exceeds 75 octets: {raw_line!r}"
    # Unfolding (\r\n followed by single space) must faithfully restore original UTF-8 text
    unfolded = ics_payload.replace("\r\n ", "")
    assert f"SUMMARY:{long_vi_title.replace(',', '\\,')}" in unfolded

    # 2. Distributed Redis rate limiting (60 req/300s per token hash -> 61st returns 429)
    owner_id, other_user_id, _, _, _ = await _seed_webcal_fixtures()
    owner_jwt = JwtTokenProvider.create_access_token(
        user_id=owner_id,
        email=f"webcal_owner_{owner_id.hex}@focusflow.vn",
        role="LEARNER",
        tier="FREE",
    )
    owner_headers = {"Authorization": f"Bearer {owner_jwt}"}

    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            rotate_resp = await client.post(
                "/api/v1/account/calendar/webcal/rotate", headers=owner_headers
            )
            assert rotate_resp.status_code == 200
            raw_token = _extract_raw_token(rotate_resp.json()["feed_url"])

            for _ in range(60):
                resp = await client.get(f"/api/v1/feeds/{raw_token}.ics")
                assert resp.status_code == 200
                assert resp.headers.get("cache-control") == "no-store, private"
                assert resp.headers.get("referrer-policy") == "no-referrer"
                assert resp.headers.get("x-content-type-options") == "nosniff"

            rate_limited = await client.get(f"/api/v1/feeds/{raw_token}.ics")
            assert rate_limited.status_code == 429
            assert "retry-after" in rate_limited.headers
    finally:
        await _cleanup_users(owner_id, other_user_id)
