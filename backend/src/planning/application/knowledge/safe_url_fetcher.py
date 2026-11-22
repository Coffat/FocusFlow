from __future__ import annotations

import asyncio
import ipaddress
import socket
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx


class UnsafeUrlError(ValueError):
    code = "KNOWLEDGE_SOURCE_QUARANTINED"


class SafeUrlFetchError(ValueError):
    code = "KNOWLEDGE_URL_FETCH_FAILED"


_ALLOWED_URL_CONTENT_TYPES: frozenset[str] = frozenset(
    {
        "text/plain",
        "text/html",
        "text/markdown",
        "text/x-markdown",
        "text/csv",
        "application/pdf",
        "application/json",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/xhtml+xml",
    }
)


@dataclass(frozen=True, slots=True)
class FetchedDocument:
    final_url: str
    content: bytes
    content_type: str


@dataclass(frozen=True, slots=True)
class ResolvedDestination:
    scheme: str
    host: str
    port: int
    pinned_ip: str
    pinned_url: str
    host_header: str
    sni_hostname: str | None


class SafeUrlFetcher:
    def __init__(
        self,
        *,
        max_bytes: int = 5 * 1024 * 1024,
        timeout_seconds: float = 8.0,
        max_redirects: int = 3,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._max_bytes = max_bytes
        self._timeout = timeout_seconds
        self._max_redirects = max_redirects
        self._transport = transport

    @classmethod
    def _is_public_ip(cls, ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        if (
            not ip.is_global
            or ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return False
        if isinstance(ip, ipaddress.IPv6Address):
            if ip.ipv4_mapped is not None and not cls._is_public_ip(ip.ipv4_mapped):
                return False
            if ip.sixtofour is not None and not cls._is_public_ip(ip.sixtofour):
                return False
            if ip.teredo is not None:
                server_ip, client_ip = ip.teredo
                if not cls._is_public_ip(server_ip) or not cls._is_public_ip(client_ip):
                    return False
        return True

    @classmethod
    def _validate_ip_address(cls, address: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
        if "%" in address:
            raise UnsafeUrlError("URL trỏ đến mạng nội bộ, loopback hoặc link-local")
        try:
            ip = ipaddress.ip_address(address)
        except ValueError as exc:
            raise UnsafeUrlError("Địa chỉ IP nguồn học liệu không hợp lệ") from exc
        if not cls._is_public_ip(ip):
            raise UnsafeUrlError("URL trỏ đến mạng nội bộ, loopback hoặc link-local")
        return ip

    @staticmethod
    def _parse_ip_literal(
        host: str,
    ) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
        try:
            return ipaddress.ip_address(host)
        except ValueError:
            pass
        try:
            packed = socket.inet_aton(host)
        except OSError:
            return None
        return ipaddress.IPv4Address(packed)

    @classmethod
    def validate_url(cls, url: str) -> tuple[str, int]:
        if any(ch in url for ch in ("\r", "\n", "\x00", "\t")):
            raise UnsafeUrlError("URL chứa ký tự điều khiển không hợp lệ")
        parsed = urlsplit(url)
        scheme = parsed.scheme.lower()
        if scheme not in {"http", "https"}:
            raise UnsafeUrlError("Chỉ cho phép URL HTTP/HTTPS công khai")
        if not parsed.hostname or parsed.username is not None or parsed.password is not None:
            raise UnsafeUrlError("URL không hợp lệ hoặc chứa thông tin xác thực")
        try:
            port = parsed.port or (443 if scheme == "https" else 80)
        except ValueError as exc:
            raise UnsafeUrlError("Cổng URL không hợp lệ") from exc
        if port < 1 or port > 65535:
            raise UnsafeUrlError("Cổng URL không hợp lệ")
        host = parsed.hostname
        if "%" in host:
            raise UnsafeUrlError("URL trỏ đến mạng nội bộ, loopback hoặc link-local")
        normalized_host = host.rstrip(".").lower()
        if (
            not normalized_host
            or normalized_host == "localhost"
            or normalized_host.endswith(".localhost")
        ):
            raise UnsafeUrlError("URL trỏ đến mạng nội bộ, loopback hoặc link-local")
        literal_ip = cls._parse_ip_literal(host)
        if literal_ip is not None and not cls._is_public_ip(literal_ip):
            raise UnsafeUrlError("URL trỏ đến mạng nội bộ, loopback hoặc link-local")
        return host, port

    @classmethod
    def _validate_shape(cls, url: str) -> tuple[str, int]:
        return cls.validate_url(url)

    @classmethod
    async def _resolve_and_pin_destination(cls, url: str) -> ResolvedDestination:
        host, port = cls.validate_url(url)
        parsed = urlsplit(url)
        scheme = parsed.scheme.lower()

        literal_ip = cls._parse_ip_literal(host)
        if literal_ip is not None:
            if not cls._is_public_ip(literal_ip):
                raise UnsafeUrlError("URL trỏ đến mạng nội bộ, loopback hoặc link-local")
            pinned_ip = str(literal_ip)
        else:
            try:
                infos = await asyncio.to_thread(
                    socket.getaddrinfo,
                    host,
                    port,
                    type=socket.SOCK_STREAM,
                )
            except (socket.gaierror, OSError) as exc:
                raise UnsafeUrlError("Không thể phân giải tên miền nguồn học liệu") from exc
            ordered_addresses: list[str] = []
            seen: set[str] = set()
            for info in infos:
                address = str(info[4][0])
                if address not in seen:
                    seen.add(address)
                    ordered_addresses.append(address)
            if not ordered_addresses:
                raise UnsafeUrlError("Tên miền không có địa chỉ IP hợp lệ")
            validated_ips = [cls._validate_ip_address(address) for address in ordered_addresses]
            pinned_ip = str(validated_ips[0])

        default_port = 443 if scheme == "https" else 80
        ip_netloc = f"[{pinned_ip}]" if ":" in pinned_ip else pinned_ip
        netloc = ip_netloc if port == default_port else f"{ip_netloc}:{port}"
        pinned_url = urlunsplit((scheme, netloc, parsed.path, parsed.query, ""))

        host_for_header = f"[{host}]" if ":" in host else host
        host_header = host_for_header if port == default_port else f"{host_for_header}:{port}"

        sni_hostname: str | None = None
        if scheme == "https":
            try:
                sni_hostname = host.encode("idna").decode("ascii")
            except UnicodeError as exc:
                raise UnsafeUrlError("Tên miền nguồn học liệu không hợp lệ") from exc

        return ResolvedDestination(
            scheme=scheme,
            host=host,
            port=port,
            pinned_ip=pinned_ip,
            pinned_url=pinned_url,
            host_header=host_header,
            sni_hostname=sni_hostname,
        )

    @classmethod
    async def _validate_public_destination(cls, url: str) -> str:
        destination = await cls._resolve_and_pin_destination(url)
        return destination.pinned_ip

    @staticmethod
    def _validate_response_content_type(raw_content_type: str) -> str:
        media_type = raw_content_type.split(";", 1)[0].strip().lower()
        if media_type not in _ALLOWED_URL_CONTENT_TYPES:
            raise UnsafeUrlError("Định dạng nội dung từ URL không được hỗ trợ")
        return raw_content_type

    async def fetch(self, url: str) -> FetchedDocument:
        current = url.strip()
        timeout = httpx.Timeout(self._timeout)
        try:
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=False,
                trust_env=False,
                verify=True,
                transport=self._transport,
            ) as client:
                for redirect_count in range(self._max_redirects + 1):
                    destination = await self._resolve_and_pin_destination(current)
                    headers = {
                        "User-Agent": "FocusFlow-Knowledge/1.0",
                        "Host": destination.host_header,
                    }
                    extensions = (
                        {"sni_hostname": destination.sni_hostname}
                        if destination.sni_hostname is not None
                        else None
                    )
                    async with client.stream(
                        "GET",
                        destination.pinned_url,
                        headers=headers,
                        extensions=extensions,
                    ) as response:
                        if response.status_code in {301, 302, 303, 307, 308}:
                            location = response.headers.get("location")
                            if not location or redirect_count >= self._max_redirects:
                                raise UnsafeUrlError(
                                    "Chuỗi chuyển hướng nguồn học liệu không hợp lệ"
                                )
                            current = urljoin(current, location)
                            continue
                        if response.status_code >= 400:
                            raise SafeUrlFetchError(
                                f"Nguồn URL trả về mã lỗi HTTP {response.status_code}"
                            )
                        content_type = self._validate_response_content_type(
                            response.headers.get("content-type", "application/octet-stream")
                        )
                        declared = response.headers.get("content-length")
                        if declared and declared.isdigit() and int(declared) > self._max_bytes:
                            raise SafeUrlFetchError("Nguồn URL vượt giới hạn 5 MB")
                        body = bytearray()
                        async for chunk in response.aiter_bytes():
                            body.extend(chunk)
                            if len(body) > self._max_bytes:
                                raise SafeUrlFetchError("Nguồn URL vượt giới hạn 5 MB")
                        return FetchedDocument(
                            final_url=current,
                            content=bytes(body),
                            content_type=content_type,
                        )
        except (UnsafeUrlError, SafeUrlFetchError):
            raise
        except httpx.TimeoutException as exc:
            raise SafeUrlFetchError("Hết thời gian kết nối khi tải nguồn học liệu từ URL") from exc
        except (httpx.HTTPError, OSError) as exc:
            raise SafeUrlFetchError("Không thể kết nối đến nguồn học liệu URL") from exc
        raise UnsafeUrlError("Không thể tải nguồn học liệu")

    async def probe_reachable(
        self,
        url: str,
        *,
        url_validator: Callable[[str], bool] | None = None,
        user_agent: str = "FocusFlow-ResourceCheck/1.0",
    ) -> bool:
        """Check URL reachability via pinned IP + Host + SNI without leaking SSRF redirects."""
        current = url.strip()
        timeout = httpx.Timeout(self._timeout)
        try:
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=False,
                trust_env=False,
                verify=True,
                transport=self._transport,
            ) as client:
                for redirect_count in range(self._max_redirects + 1):
                    if url_validator is not None and not url_validator(current):
                        return False
                    destination = await self._resolve_and_pin_destination(current)
                    headers = {
                        "User-Agent": user_agent,
                        "Host": destination.host_header,
                    }
                    extensions = (
                        {"sni_hostname": destination.sni_hostname}
                        if destination.sni_hostname is not None
                        else None
                    )
                    resp = await client.head(
                        destination.pinned_url,
                        headers=headers,
                        extensions=extensions,
                    )
                    if resp.status_code == 405:
                        resp = await client.get(
                            destination.pinned_url,
                            headers={**headers, "Range": "bytes=0-0"},
                            extensions=extensions,
                        )
                    if resp.status_code in {301, 302, 303, 307, 308}:
                        location = resp.headers.get("location")
                        if not location or redirect_count >= self._max_redirects:
                            return False
                        current = urljoin(current, location)
                        continue
                    return 200 <= resp.status_code < 400
        except (
            TimeoutError,
            UnsafeUrlError,
            SafeUrlFetchError,
            httpx.HTTPError,
            ValueError,
            OSError,
        ):
            return False
        return False
