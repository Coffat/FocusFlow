from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx

from src.account.domain.ports.calendar_provider_port import (
    CalendarAuthError,
    CalendarConflictError,
    CalendarEventDTO,
    CalendarGoneError,
    CalendarPreconditionFailedError,
    CalendarProviderError,
    CalendarProviderPort,
    CalendarRateLimitError,
    CalendarSyncEventsResultDTO,
    CalendarTimeInterval,
    CalendarWatchResultDTO,
    get_deterministic_event_id,
)
from src.shared_kernel.config import Settings, get_settings
from src.shared_kernel.infrastructure.security.encryption import (
    ensure_calendar_encryption_key_valid,
)

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"


def parse_rfc3339(date_str: str) -> datetime:
    """Parse RFC3339 / ISO 8601 timestamp to timezone-aware UTC datetime."""
    norm = date_str.replace("Z", "+00:00")
    dt = datetime.fromisoformat(norm)
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


class GoogleCalendarAdapter(CalendarProviderPort):
    """Production adapter for Google Calendar API v3 using httpx.AsyncClient (UC-17)."""

    def __init__(
        self,
        settings: Settings | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._client = client
        ensure_calendar_encryption_key_valid(self.settings)

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is not None:
            return self._client
        return httpx.AsyncClient(timeout=15.0)

    async def _get_access_token(self, refresh_token: str) -> str:
        """Exchange refresh token for ephemeral Google OAuth access token."""
        client = self._get_client()
        payload = {
            "client_id": self.settings.google_client_id,
            "client_secret": self.settings.google_client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        try:
            resp = await client.post(GOOGLE_TOKEN_URL, data=payload)
            if resp.status_code == 400 or resp.status_code == 401:
                raise CalendarAuthError(
                    f"Google OAuth refresh failed ({resp.status_code}): {resp.text}"
                )
            resp.raise_for_status()
            data = resp.json()
            access_token: str = data["access_token"]
            return access_token
        except httpx.HTTPError as exc:
            if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in (400, 401):
                raise CalendarAuthError("Google OAuth token exchange rejected.") from exc
            raise CalendarProviderError(f"HTTP error during token refresh: {exc}") from exc

    def _handle_error_response(self, resp: httpx.Response) -> None:
        """Map HTTP error status codes to FocusFlow calendar domain exceptions."""
        status = resp.status_code
        if status == 401:
            raise CalendarAuthError(f"Google API Unauthorized (401): {resp.text}")
        if status == 409:
            raise CalendarConflictError(f"Google Calendar resource conflict (409): {resp.text}")
        if status == 410:
            raise CalendarGoneError(f"Google Calendar syncToken expired (410 Gone): {resp.text}")
        if status == 412:
            raise CalendarPreconditionFailedError(
                f"Google Calendar ETag precondition failed (412): {resp.text}"
            )
        if status == 429:
            raise CalendarRateLimitError(f"Google Calendar rate limit exceeded (429): {resp.text}")
        raise CalendarProviderError(f"Google Calendar API error ({status}): {resp.text}")

    async def get_free_busy_intervals(
        self,
        refresh_token: str,
        calendar_ids: list[str],
        time_min: datetime,
        time_max: datetime,
    ) -> list[CalendarTimeInterval]:
        access_token = await self._get_access_token(refresh_token)
        client = self._get_client()

        body = {
            "timeMin": time_min.isoformat(),
            "timeMax": time_max.isoformat(),
            "items": [{"id": cid} for cid in calendar_ids],
        }
        headers = {"Authorization": f"Bearer {access_token}"}

        resp = await client.post(
            f"{GOOGLE_CALENDAR_API_BASE}/freeBusy",
            json=body,
            headers=headers,
        )
        if resp.is_error:
            self._handle_error_response(resp)

        data = resp.json()
        calendars = data.get("calendars", {})
        intervals: list[CalendarTimeInterval] = []

        for _cid, cal_data in calendars.items():
            for busy in cal_data.get("busy", []):
                b_start = parse_rfc3339(busy["start"])
                b_end = parse_rfc3339(busy["end"])
                intervals.append(CalendarTimeInterval(start_time=b_start, end_time=b_end))

        intervals.sort(key=lambda x: x.start_time)
        return intervals

    async def create_secondary_calendar(
        self,
        refresh_token: str,
        title: str = "FocusFlow",
    ) -> str:
        access_token = await self._get_access_token(refresh_token)
        client = self._get_client()

        body = {
            "summary": title,
            "description": "Lịch học tập cá nhân hóa tạo bởi FocusFlow Learning Intelligence.",
            "timeZone": "Asia/Ho_Chi_Minh",
        }
        headers = {"Authorization": f"Bearer {access_token}"}

        resp = await client.post(
            f"{GOOGLE_CALENDAR_API_BASE}/calendars",
            json=body,
            headers=headers,
        )
        if resp.is_error:
            self._handle_error_response(resp)

        cal_data = resp.json()
        cal_id: str = cal_data["id"]
        return cal_id

    async def list_events(
        self,
        refresh_token: str,
        calendar_id: str,
        sync_token: str | None = None,
        page_token: str | None = None,
        time_min: datetime | None = None,
        time_max: datetime | None = None,
    ) -> CalendarSyncEventsResultDTO:
        access_token = await self._get_access_token(refresh_token)
        client = self._get_client()

        params: dict[str, Any] = {"singleEvents": "true", "showDeleted": "true"}
        if sync_token:
            params["syncToken"] = sync_token
        else:
            if time_min:
                params["timeMin"] = time_min.isoformat()
            if time_max:
                params["timeMax"] = time_max.isoformat()

        if page_token:
            params["pageToken"] = page_token

        headers = {"Authorization": f"Bearer {access_token}"}
        resp = await client.get(
            f"{GOOGLE_CALENDAR_API_BASE}/calendars/{calendar_id}/events",
            params=params,
            headers=headers,
        )

        if resp.status_code == 410:
            # Expired syncToken per Google Calendar spec
            return CalendarSyncEventsResultDTO(
                events=[],
                next_sync_token=None,
                next_page_token=None,
                sync_reset_needed=True,
            )

        if resp.is_error:
            self._handle_error_response(resp)

        data = resp.json()
        raw_items = data.get("items", [])
        events: list[CalendarEventDTO] = []

        for item in raw_items:
            status = item.get("status", "confirmed")
            start_raw = item.get("start", {}).get("dateTime") or item.get("start", {}).get("date")
            end_raw = item.get("end", {}).get("dateTime") or item.get("end", {}).get("date")
            if status != "cancelled" and (not start_raw or not end_raw):
                continue

            start_dt = parse_rfc3339(start_raw) if start_raw else datetime.now(UTC)
            end_dt = parse_rfc3339(end_raw) if end_raw else start_dt

            # Block ID mapping from extendedProperties.private
            private_props = item.get("extendedProperties", {}).get("private", {})
            block_id_str = private_props.get("focusflow_block_id")
            block_id = UUID(block_id_str) if block_id_str else None

            events.append(
                CalendarEventDTO(
                    id=item["id"],
                    title=item.get("summary", ""),
                    start_time=start_dt,
                    end_time=end_dt,
                    description=item.get("description"),
                    location=item.get("location"),
                    etag=item.get("etag"),
                    status=item.get("status", "confirmed"),
                    block_id=block_id,
                    extended_properties=private_props,
                )
            )

        next_page = data.get("nextPageToken")
        next_sync = data.get("nextSyncToken")

        return CalendarSyncEventsResultDTO(
            events=events,
            next_sync_token=next_sync,
            next_page_token=next_page,
            sync_reset_needed=False,
        )

    async def get_event(
        self,
        refresh_token: str,
        calendar_id: str,
        event_id: str,
    ) -> CalendarEventDTO | None:
        access_token = await self._get_access_token(refresh_token)
        client = self._get_client()
        headers = {"Authorization": f"Bearer {access_token}"}
        resp = await client.get(
            f"{GOOGLE_CALENDAR_API_BASE}/calendars/{calendar_id}/events/{event_id}",
            headers=headers,
        )
        if resp.status_code == 404:
            return None
        if resp.is_error:
            self._handle_error_response(resp)

        item = resp.json()
        start_raw = item.get("start", {}).get("dateTime") or item.get("start", {}).get("date")
        end_raw = item.get("end", {}).get("dateTime") or item.get("end", {}).get("date")
        start_dt = parse_rfc3339(start_raw) if start_raw else datetime.now(UTC)
        end_dt = parse_rfc3339(end_raw) if end_raw else datetime.now(UTC)

        private_props = item.get("extendedProperties", {}).get("private", {})
        block_id_str = private_props.get("focusflow_block_id")
        block_id = UUID(block_id_str) if block_id_str else None

        return CalendarEventDTO(
            id=item["id"],
            title=item.get("summary", ""),
            start_time=start_dt,
            end_time=end_dt,
            description=item.get("description"),
            location=item.get("location"),
            etag=item.get("etag"),
            status=item.get("status", "confirmed"),
            block_id=block_id,
            extended_properties=private_props,
        )

    async def create_event(
        self,
        refresh_token: str,
        calendar_id: str,
        event: CalendarEventDTO,
    ) -> CalendarEventDTO:
        access_token = await self._get_access_token(refresh_token)
        client = self._get_client()

        event_id = event.id
        if not event_id:
            if event.block_id:
                event_id = get_deterministic_event_id(event.block_id)
            event.id = event_id

        private_props = dict(event.extended_properties)
        if event.block_id:
            private_props["focusflow_block_id"] = str(event.block_id)

        body: dict[str, Any] = {
            "summary": event.title,
            "description": event.description or "",
            "start": {"dateTime": event.start_time.isoformat()},
            "end": {"dateTime": event.end_time.isoformat()},
            "extendedProperties": {"private": private_props},
        }
        if event_id:
            body["id"] = event_id

        headers = {"Authorization": f"Bearer {access_token}"}
        resp = await client.post(
            f"{GOOGLE_CALENDAR_API_BASE}/calendars/{calendar_id}/events",
            json=body,
            headers=headers,
        )

        if resp.is_error:
            self._handle_error_response(resp)

        created_data = resp.json()
        event.id = created_data["id"]
        event.etag = created_data.get("etag")
        return event

    async def update_event(
        self,
        refresh_token: str,
        calendar_id: str,
        event: CalendarEventDTO,
    ) -> CalendarEventDTO:
        access_token = await self._get_access_token(refresh_token)
        client = self._get_client()

        private_props = dict(event.extended_properties)
        if event.block_id:
            private_props["focusflow_block_id"] = str(event.block_id)

        body: dict[str, Any] = {
            "summary": event.title,
            "description": event.description or "",
            "start": {"dateTime": event.start_time.isoformat()},
            "end": {"dateTime": event.end_time.isoformat()},
            "extendedProperties": {"private": private_props},
        }

        headers = {"Authorization": f"Bearer {access_token}"}
        if event.etag:
            headers["If-Match"] = event.etag

        resp = await client.put(
            f"{GOOGLE_CALENDAR_API_BASE}/calendars/{calendar_id}/events/{event.id}",
            json=body,
            headers=headers,
        )

        if resp.is_error:
            self._handle_error_response(resp)

        updated_data = resp.json()
        event.etag = updated_data.get("etag")
        return event

    async def delete_event(
        self,
        refresh_token: str,
        calendar_id: str,
        event_id: str,
        etag: str | None = None,
    ) -> bool:
        access_token = await self._get_access_token(refresh_token)
        client = self._get_client()

        headers = {"Authorization": f"Bearer {access_token}"}
        if etag:
            headers["If-Match"] = etag

        resp = await client.delete(
            f"{GOOGLE_CALENDAR_API_BASE}/calendars/{calendar_id}/events/{event_id}",
            headers=headers,
        )

        if resp.status_code == 404:
            return False
        if resp.is_error:
            self._handle_error_response(resp)

        return True

    async def watch_calendar(
        self,
        refresh_token: str,
        calendar_id: str,
        channel_id: str,
        webhook_url: str,
        channel_token: str | None = None,
    ) -> CalendarWatchResultDTO:
        access_token = await self._get_access_token(refresh_token)
        client = self._get_client()

        body: dict[str, Any] = {
            "id": channel_id,
            "type": "web_hook",
            "address": webhook_url,
        }
        if channel_token:
            body["token"] = channel_token

        headers = {"Authorization": f"Bearer {access_token}"}
        resp = await client.post(
            f"{GOOGLE_CALENDAR_API_BASE}/calendars/{calendar_id}/events/watch",
            json=body,
            headers=headers,
        )

        if resp.is_error:
            self._handle_error_response(resp)

        watch_data = resp.json()
        exp_ms = watch_data.get("expiration")
        expiration_dt = datetime.fromtimestamp(int(exp_ms) / 1000.0, tz=UTC) if exp_ms else None

        return CalendarWatchResultDTO(
            channel_id=watch_data["id"],
            resource_id=watch_data["resourceId"],
            expiration=expiration_dt,
            token=channel_token,
        )

    async def stop_watch_channel(
        self,
        refresh_token: str,
        channel_id: str,
        resource_id: str,
    ) -> bool:
        access_token = await self._get_access_token(refresh_token)
        client = self._get_client()

        body = {
            "id": channel_id,
            "resourceId": resource_id,
        }
        headers = {"Authorization": f"Bearer {access_token}"}
        resp = await client.post(
            f"{GOOGLE_CALENDAR_API_BASE}/channels/stop",
            json=body,
            headers=headers,
        )

        if resp.status_code == 404:
            return False
        if resp.is_error:
            self._handle_error_response(resp)

        return True
