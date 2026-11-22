from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class IcsEventItem:
    """Pure-domain representation of a VEVENT in an RFC 5545 calendar feed."""

    uid: str
    summary: str
    description: str
    start_time: datetime
    end_time: datetime
    status: str = "CONFIRMED"


def escape_ics_text(value: str) -> str:
    """Escape text properties according to RFC 5545 Section 3.3.11."""
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    return (
        normalized.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def format_ics_utc(dt: datetime) -> str:
    """Format a datetime as UTC YYYYMMDDTHHMMSSZ per RFC 5545."""
    aware = dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)
    return aware.strftime("%Y%m%dT%H%M%SZ")


def _fold_ics_line(line: str, max_octets: int = 75) -> str:
    """Fold a single ICS content line to <= 75 UTF-8 octets per RFC 5545 Section 3.1.

    Continuation lines begin with a single space (` `) and are joined with CRLF (`\\r\\n `).
    Splits occur strictly on character boundaries so multi-byte UTF-8 sequences
    (e.g. Vietnamese diacritics) are never corrupted.
    """
    if len(line.encode("utf-8")) <= max_octets:
        return line

    chunks: list[str] = []
    current_chars: list[str] = []
    current_octets = 0
    budget = max_octets

    for ch in line:
        ch_octets = len(ch.encode("utf-8"))
        if current_chars and current_octets + ch_octets > budget:
            chunks.append("".join(current_chars))
            current_chars = [ch]
            current_octets = ch_octets
            # Continuation lines have a leading single space (1 octet)
            budget = max_octets - 1
        else:
            current_chars.append(ch)
            current_octets += ch_octets

    if current_chars:
        chunks.append("".join(current_chars))

    return "\r\n ".join(chunks)


def build_ics_calendar(
    events: Sequence[IcsEventItem],
    *,
    timezone: str,
    generated_at: datetime,
    calendar_name: str = "FocusFlow Study Schedule",
) -> str:
    """Build an RFC 5545 `text/calendar` payload using CRLF line endings."""
    dtstamp = format_ics_utc(generated_at)
    safe_tz = escape_ics_text(timezone.strip() or "Asia/Ho_Chi_Minh")
    safe_calname = escape_ics_text(calendar_name)

    lines: list[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//FocusFlow//Official Schedule//VN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{safe_calname}",
        f"X-WR-TIMEZONE:{safe_tz}",
    ]

    for event in events:
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{event.uid}",
                f"DTSTAMP:{dtstamp}",
                f"DTSTART:{format_ics_utc(event.start_time)}",
                f"DTEND:{format_ics_utc(event.end_time)}",
                f"SUMMARY:{escape_ics_text(event.summary)}",
                f"DESCRIPTION:{escape_ics_text(event.description)}",
                f"STATUS:{event.status}",
                "END:VEVENT",
            ]
        )

    lines.append("END:VCALENDAR")
    folded_lines = [_fold_ics_line(line) for line in lines]
    return "\r\n".join(folded_lines) + "\r\n"
