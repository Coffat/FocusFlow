import copy
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from src.account.domain.ports.calendar_provider_port import (
    CalendarConflictError,
    CalendarEventDTO,
    CalendarPreconditionFailedError,
    CalendarProviderPort,
    CalendarRateLimitError,
    CalendarSyncEventsResultDTO,
    CalendarTimeInterval,
    CalendarWatchResultDTO,
    get_deterministic_event_id,
)


class MockCalendarAdapter(CalendarProviderPort):
    """In-memory mock adapter for Google Calendar API v3 with fault injection and pagination."""

    def __init__(self, page_size: int = 10) -> None:
        self.page_size = page_size
        self._calendars: dict[str, dict[str, Any]] = {
            "primary": {"id": "primary", "summary": "Primary Calendar"}
        }
        self._events: dict[str, dict[str, CalendarEventDTO]] = {"primary": {}}
        self._channels: dict[str, dict[str, Any]] = {}

        # Fault injection toggles
        self.inject_fault_410: bool = False
        self.inject_fault_409: bool = False
        self.inject_fault_412: bool = False
        self.inject_fault_429: bool = False

    def reset(self) -> None:
        """Reset internal storage and fault toggles."""
        self._calendars = {"primary": {"id": "primary", "summary": "Primary Calendar"}}
        self._events = {"primary": {}}
        self._channels.clear()
        self.inject_fault_410 = False
        self.inject_fault_409 = False
        self.inject_fault_412 = False
        self.inject_fault_429 = False

    async def get_free_busy_intervals(
        self,
        refresh_token: str,
        calendar_ids: list[str],
        time_min: datetime,
        time_max: datetime,
    ) -> list[CalendarTimeInterval]:
        if self.inject_fault_429:
            raise CalendarRateLimitError()

        busy_intervals: list[CalendarTimeInterval] = []
        for cal_id in calendar_ids:
            cal_events = self._events.get(cal_id, {})
            for event in cal_events.values():
                if event.status == "cancelled":
                    continue
                # Overlap check: start < time_max and end > time_min
                if event.start_time < time_max and event.end_time > time_min:
                    interval_start = max(event.start_time, time_min)
                    interval_end = min(event.end_time, time_max)
                    if interval_end > interval_start:
                        busy_intervals.append(
                            CalendarTimeInterval(start_time=interval_start, end_time=interval_end)
                        )

        busy_intervals.sort(key=lambda x: x.start_time)
        return busy_intervals

    async def create_secondary_calendar(
        self,
        refresh_token: str,
        title: str = "FocusFlow",
    ) -> str:
        if self.inject_fault_429:
            raise CalendarRateLimitError()

        cal_id = f"ff_cal_{uuid4().hex[:12]}"
        self._calendars[cal_id] = {"id": cal_id, "summary": title}
        self._events[cal_id] = {}
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
        if self.inject_fault_429:
            raise CalendarRateLimitError()

        if self.inject_fault_410 or sync_token == "invalid_token":
            return CalendarSyncEventsResultDTO(
                events=[],
                next_sync_token=None,
                next_page_token=None,
                sync_reset_needed=True,
            )

        cal_events = list(self._events.get(calendar_id, {}).values())

        # Filter by time bounds if requested
        filtered_events: list[CalendarEventDTO] = []
        for ev in cal_events:
            if time_min and ev.end_time <= time_min:
                continue
            if time_max and ev.start_time >= time_max:
                continue
            filtered_events.append(ev)

        filtered_events.sort(key=lambda x: x.start_time)

        # Pagination logic
        offset = 0
        if page_token and page_token.startswith("offset_"):
            try:
                offset = int(page_token.split("_")[1])
            except ValueError:
                offset = 0

        paged_slice = filtered_events[offset : offset + self.page_size]
        has_more = (offset + self.page_size) < len(filtered_events)

        if has_more:
            next_page = f"offset_{offset + self.page_size}"
            next_sync = None
        else:
            next_page = None
            next_sync = f"sync_token_{len(filtered_events)}_{int(datetime.now(UTC).timestamp())}"

        return CalendarSyncEventsResultDTO(
            events=paged_slice,
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
        if self.inject_fault_429:
            raise CalendarRateLimitError()
        cal = self._events.get(calendar_id, {})
        ev = cal.get(event_id)
        return copy.deepcopy(ev) if ev is not None else None

    async def create_event(
        self,
        refresh_token: str,
        calendar_id: str,
        event: CalendarEventDTO,
    ) -> CalendarEventDTO:
        if self.inject_fault_429:
            raise CalendarRateLimitError()
        if self.inject_fault_409:
            raise CalendarConflictError()

        if calendar_id not in self._events:
            self._events[calendar_id] = {}

        event_id = event.id
        if not event_id:
            if event.block_id:
                event_id = get_deterministic_event_id(event.block_id)
            else:
                event_id = f"ff_{uuid4().hex}"
            event.id = event_id

        if event_id in self._events[calendar_id]:
            raise CalendarConflictError(
                f"Event with id '{event_id}' already exists (409 Conflict)."
            )

        event_copy = copy.deepcopy(event)
        event_copy.etag = f'"{uuid4().hex[:12]}"'
        self._events[calendar_id][event_id] = event_copy
        return copy.deepcopy(event_copy)

    async def update_event(
        self,
        refresh_token: str,
        calendar_id: str,
        event: CalendarEventDTO,
    ) -> CalendarEventDTO:
        if self.inject_fault_429:
            raise CalendarRateLimitError()
        if self.inject_fault_412:
            raise CalendarPreconditionFailedError()

        cal = self._events.get(calendar_id, {})
        existing = cal.get(event.id)
        if not existing:
            # If doesn't exist, create it
            return await self.create_event(refresh_token, calendar_id, event)

        if event.etag and existing.etag and event.etag != existing.etag:
            raise CalendarPreconditionFailedError()

        event_copy = copy.deepcopy(event)
        event_copy.etag = f'"{uuid4().hex[:12]}"'
        self._events[calendar_id][event.id] = event_copy
        return copy.deepcopy(event_copy)

    async def delete_event(
        self,
        refresh_token: str,
        calendar_id: str,
        event_id: str,
        etag: str | None = None,
    ) -> bool:
        if self.inject_fault_429:
            raise CalendarRateLimitError()
        if self.inject_fault_412:
            raise CalendarPreconditionFailedError()

        cal = self._events.get(calendar_id, {})
        existing = cal.get(event_id)
        if not existing:
            return False

        if etag and existing.etag and etag != existing.etag:
            raise CalendarPreconditionFailedError()

        del self._events[calendar_id][event_id]
        return True

    async def watch_calendar(
        self,
        refresh_token: str,
        calendar_id: str,
        channel_id: str,
        webhook_url: str,
        channel_token: str | None = None,
    ) -> CalendarWatchResultDTO:
        if self.inject_fault_429:
            raise CalendarRateLimitError()

        resource_id = f"res_{uuid4().hex[:16]}"
        expiration = datetime.now(UTC) + timedelta(days=7)
        self._channels[channel_id] = {
            "calendar_id": calendar_id,
            "resource_id": resource_id,
            "expiration": expiration,
            "webhook_url": webhook_url,
            "token": channel_token,
        }
        return CalendarWatchResultDTO(
            channel_id=channel_id,
            resource_id=resource_id,
            expiration=expiration,
            token=channel_token,
        )

    async def stop_watch_channel(
        self,
        refresh_token: str,
        channel_id: str,
        resource_id: str,
    ) -> bool:
        if self.inject_fault_429:
            raise CalendarRateLimitError()

        if channel_id in self._channels:
            del self._channels[channel_id]
            return True
        return False
