import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import httpx


class UnsafeUrlError(ValueError):
    code = "KNOWLEDGE_SOURCE_QUARANTINED"


@dataclass(frozen=True, slots=True)
class FetchedDocument:
    final_url: str
    content: bytes
    content_type: str


class SafeUrlFetcher:
    def __init__(
        self,
        *,
        max_bytes: int = 5 * 1024 * 1024,
        timeout_seconds: float = 8.0,
        max_redirects: int = 3,
    ) -> None:
        self._max_bytes = max_bytes
        self._timeout = timeout_seconds
        self._max_redirects = max_redirects

    @staticmethod
    def _validate_shape(url: str) -> tuple[str, int]:
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"}:
            raise UnsafeUrlError("Chỉ cho phép URL HTTP/HTTPS công khai")
        if not parsed.hostname or parsed.username or parsed.password:
            raise UnsafeUrlError("URL không hợp lệ hoặc chứa thông tin xác thực")
        return parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80)

    @classmethod
    async def _validate_public_destination(cls, url: str) -> None:
        host, port = cls._validate_shape(url)
        try:
            infos = await asyncio.to_thread(
                socket.getaddrinfo,
                host,
                port,
                type=socket.SOCK_STREAM,
            )
        except socket.gaierror as exc:
            raise UnsafeUrlError("Không thể phân giải tên miền nguồn học liệu") from exc
        addresses = {info[4][0] for info in infos}
        if not addresses:
            raise UnsafeUrlError("Tên miền không có địa chỉ IP hợp lệ")
        for address in addresses:
            ip = ipaddress.ip_address(address)
            if not ip.is_global:
                raise UnsafeUrlError("URL trỏ đến mạng nội bộ, loopback hoặc link-local")

    async def fetch(self, url: str) -> FetchedDocument:
        current = url.strip()
        timeout = httpx.Timeout(self._timeout)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            for redirect_count in range(self._max_redirects + 1):
                await self._validate_public_destination(current)
                async with client.stream(
                    "GET", current, headers={"User-Agent": "FocusFlow-Knowledge/1.0"}
                ) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        location = response.headers.get("location")
                        if not location or redirect_count >= self._max_redirects:
                            raise UnsafeUrlError("Chuỗi chuyển hướng nguồn học liệu không hợp lệ")
                        current = urljoin(current, location)
                        continue
                    response.raise_for_status()
                    declared = response.headers.get("content-length")
                    if declared and int(declared) > self._max_bytes:
                        raise ValueError("Nguồn URL vượt giới hạn 5 MB")
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > self._max_bytes:
                            raise ValueError("Nguồn URL vượt giới hạn 5 MB")
                    return FetchedDocument(
                        final_url=str(response.url),
                        content=bytes(body),
                        content_type=response.headers.get(
                            "content-type", "application/octet-stream"
                        ),
                    )
        raise UnsafeUrlError("Không thể tải nguồn học liệu")
