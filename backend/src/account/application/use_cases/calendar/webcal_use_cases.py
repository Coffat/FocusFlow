from __future__ import annotations

import hashlib
import re
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from src.account.application.dtos.calendar import (
    WebcalRevokeResponseDTO,
    WebcalRotateResponseDTO,
    WebcalStatusResponseDTO,
)
from src.account.application.ports.user_repository_port import UserRepositoryPort
from src.account.application.ports.webcal_token_repository_port import (
    WebcalTokenRepositoryPort,
)
from src.account.domain.services.ics_builder import IcsEventItem, build_ics_calendar
from src.planning.public_api import PlanningExecutionBridgePort
from src.shared_kernel.application.uow import AsyncUnitOfWork

_TOKEN_HEX_RE = re.compile(r"^[0-9a-f]{64}$")


class WebcalTokenInvalidError(LookupError):
    """Raised when a WebCal token is malformed, missing, or revoked."""


def _hash_webcal_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


class GetWebcalStatusUseCase:
    """Return WebCal subscription status without ever exposing a plaintext token."""

    def __init__(self, repository: WebcalTokenRepositoryPort) -> None:
        self._repository = repository

    async def execute(self, user_id: UUID) -> WebcalStatusResponseDTO:
        record = await self._repository.get_by_user_id(user_id)
        if record is None:
            return WebcalStatusResponseDTO(
                has_active_token=False,
                is_active=False,
                rotated_at=None,
                last_used_at=None,
            )
        return WebcalStatusResponseDTO(
            has_active_token=record.is_active,
            is_active=record.is_active,
            rotated_at=record.rotated_at,
            last_used_at=record.last_used_at,
        )


class RotateWebcalTokenUseCase:
    """Generate/rotate a 256-bit WebCal token, storing only its SHA-256 hash (ADR-008)."""

    def __init__(
        self,
        repository: WebcalTokenRepositoryPort,
        uow: AsyncUnitOfWork,
        *,
        public_base_url: str | None = None,
    ) -> None:
        self._repository = repository
        self._uow = uow
        self._public_base_url = (public_base_url or "").strip().rstrip("/")

    async def execute(self, user_id: UUID) -> WebcalRotateResponseDTO:
        raw_token = secrets.token_hex(32)
        token_hash = _hash_webcal_token(raw_token)
        now = datetime.now(UTC)

        async with self._uow:
            await self._repository.upsert_token(
                user_id=user_id,
                token_hash=token_hash,
                now=now,
            )
            await self._uow.commit()

        feed_path = f"/api/v1/feeds/{raw_token}.ics"
        if self._public_base_url:
            feed_url = f"{self._public_base_url}{feed_path}"
            if feed_url.startswith("https://"):
                webcal_url = "webcal://" + feed_url.removeprefix("https://")
            elif feed_url.startswith("http://"):
                webcal_url = "webcal://" + feed_url.removeprefix("http://")
            else:
                webcal_url = feed_url
        else:
            feed_url = feed_path
            webcal_url = feed_path

        return WebcalRotateResponseDTO(
            webcal_url=webcal_url,
            feed_url=feed_url,
            rotated_at=now,
        )


class RevokeWebcalTokenUseCase:
    """Revoke the authenticated learner's active WebCal token."""

    def __init__(
        self,
        repository: WebcalTokenRepositoryPort,
        uow: AsyncUnitOfWork,
    ) -> None:
        self._repository = repository
        self._uow = uow

    async def execute(self, user_id: UUID) -> WebcalRevokeResponseDTO:
        now = datetime.now(UTC)
        async with self._uow:
            revoked = await self._repository.revoke_for_user(user_id=user_id, now=now)
            await self._uow.commit()
        return WebcalRevokeResponseDTO(revoked=revoked, is_active=False)


class GetWebcalIcsFeedUseCase:
    """Authenticate a WebCal feed token via SHA-256 hash and render owner's active schedule as ICS."""

    def __init__(
        self,
        repository: WebcalTokenRepositoryPort,
        user_repo: UserRepositoryPort,
        planning_bridge: PlanningExecutionBridgePort,
        uow: AsyncUnitOfWork,
    ) -> None:
        self._repository = repository
        self._user_repo = user_repo
        self._planning_bridge = planning_bridge
        self._uow = uow

    async def execute(self, raw_token: str) -> str:
        if not _TOKEN_HEX_RE.fullmatch(raw_token):
            raise WebcalTokenInvalidError("Invalid WebCal token")

        token_hash = _hash_webcal_token(raw_token)
        record = await self._repository.get_active_by_token_hash(token_hash)
        if record is None:
            raise WebcalTokenInvalidError("WebCal token not found or revoked")

        now = datetime.now(UTC)
        async with self._uow:
            await self._repository.touch_last_used(record.id, now)
            await self._uow.commit()

        user = await self._user_repo.find_by_id(record.user_id)
        timezone = (getattr(user, "timezone", None) or "Asia/Ho_Chi_Minh").strip()

        today = now.date()
        start_date = today - timedelta(days=30)
        end_date = today + timedelta(days=180)
        blocks = await self._planning_bridge.get_week_schedule_blocks(
            user_id=record.user_id,
            start_date=start_date,
            end_date=end_date,
        )

        active_blocks = [
            block
            for block in blocks
            if block.roadmap_status == "ACTIVE" and block.official_schedule_id is not None
        ]

        events = [
            IcsEventItem(
                uid=f"{block.id}@focusflow.app",
                summary=f"[FocusFlow] {block.roadmap_title} - {block.block_type}",
                description=(
                    block.placement_rationale
                    or f"FocusFlow study block ({block.scheduled_duration_minutes} mins)"
                ),
                start_time=block.start_time,
                end_time=block.end_time,
                status="CONFIRMED",
            )
            for block in active_blocks
        ]

        return build_ics_calendar(
            events,
            timezone=timezone,
            generated_at=now,
        )
