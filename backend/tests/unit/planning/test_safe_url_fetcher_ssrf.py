from __future__ import annotations

import socket
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx
import pytest
from uuid6 import uuid7

from src.planning.application.knowledge.safe_url_fetcher import SafeUrlFetcher, UnsafeUrlError
from src.planning.application.use_cases.knowledge_source_use_cases import (
    CreateKnowledgeSourceUseCase,
)
from src.planning.domain.models.goal import Goal, GoalStatus
from src.planning.domain.models.knowledge_source import KnowledgeSource


class _RecordingTransport(httpx.AsyncBaseTransport):
    def __init__(self, handler: Any) -> None:
        self._handler = handler
        self.requests: list[httpx.Request] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self._handler(request)


def _addrinfo_for(addresses: list[str], port: int = 443) -> list[tuple[Any, ...]]:
    results: list[tuple[Any, ...]] = []
    for addr in addresses:
        if ":" in addr:
            results.append((socket.AF_INET6, socket.SOCK_STREAM, 6, "", (addr, port, 0, 0)))
        else:
            results.append((socket.AF_INET, socket.SOCK_STREAM, 6, "", (addr, port)))
    return results


@pytest.mark.asyncio
@pytest.mark.parametrize("rebound_ip", ["169.254.169.254", "127.0.0.1"])
async def test_dns_rebinding_uses_pinned_ip_without_second_lookup(
    monkeypatch: pytest.MonkeyPatch,
    rebound_ip: str,
) -> None:
    call_count = 0

    def rebinding_getaddrinfo(
        host: str, port: Any, *args: Any, **kwargs: Any
    ) -> list[tuple[Any, ...]]:
        nonlocal call_count
        del args, kwargs
        call_count += 1
        assert host == "rebind.example.test"
        if call_count == 1:
            return _addrinfo_for(["93.184.216.34"], int(port))
        return _addrinfo_for([rebound_ip], int(port))

    monkeypatch.setattr(socket, "getaddrinfo", rebinding_getaddrinfo)

    transport = _RecordingTransport(
        lambda req: httpx.Response(
            200,
            headers={"content-type": "text/plain; charset=utf-8"},
            content=b"safe public content",
            request=req,
        )
    )
    fetcher = SafeUrlFetcher(transport=transport)

    doc = await fetcher.fetch("https://rebind.example.test/docs/guide.txt")

    assert call_count == 1
    assert len(transport.requests) == 1
    sent = transport.requests[0]
    assert sent.url.scheme == "https"
    assert sent.url.host == "93.184.216.34"
    assert sent.url.path == "/docs/guide.txt"
    assert sent.headers["host"] == "rebind.example.test"
    assert sent.extensions.get("sni_hostname") == "rebind.example.test"
    assert doc.final_url == "https://rebind.example.test/docs/guide.txt"
    assert doc.content == b"safe public content"


@pytest.mark.asyncio
async def test_mixed_public_and_private_dns_records_are_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mixed_getaddrinfo(host: str, port: Any, *args: Any, **kwargs: Any) -> list[tuple[Any, ...]]:
        del host, args, kwargs
        return _addrinfo_for(["93.184.216.34", "169.254.169.254"], int(port))

    monkeypatch.setattr(socket, "getaddrinfo", mixed_getaddrinfo)
    transport = _RecordingTransport(lambda req: httpx.Response(200, content=b"nope", request=req))
    fetcher = SafeUrlFetcher(transport=transport)

    with pytest.raises(UnsafeUrlError):
        await fetcher.fetch("https://mixed.example.test/doc.txt")
    assert transport.requests == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "blocked_ip",
    [
        "127.0.0.1",
        "10.0.0.1",
        "192.168.1.1",
        "169.254.169.254",
        "0.0.0.0",
        "172.16.0.1",
        "224.0.0.1",
        "::1",
        "fe80::1",
        "fc00::1",
        "::ffff:127.0.0.1",
        "::ffff:169.254.169.254",
        "::",
        "ff02::1",
    ],
)
async def test_fetch_rejects_non_global_resolved_ips(
    monkeypatch: pytest.MonkeyPatch,
    blocked_ip: str,
) -> None:
    def fake_getaddrinfo(host: str, port: Any, *args: Any, **kwargs: Any) -> list[tuple[Any, ...]]:
        del host, args, kwargs
        return _addrinfo_for([blocked_ip], int(port))

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    transport = _RecordingTransport(lambda req: httpx.Response(200, content=b"secret", request=req))
    fetcher = SafeUrlFetcher(transport=transport)

    with pytest.raises(UnsafeUrlError):
        await fetcher.fetch("https://target.example.test/resource")
    assert transport.requests == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("redirect_target", "dns_map"),
    [
        (
            "http://169.254.169.254/latest/meta-data/",
            {"public.example.test": ["93.184.216.34"]},
        ),
        (
            "https://internal.example.test/admin",
            {
                "public.example.test": ["93.184.216.34"],
                "internal.example.test": ["127.0.0.1"],
            },
        ),
        (
            "file:///etc/passwd",
            {"public.example.test": ["93.184.216.34"]},
        ),
        (
            "https://[::ffff:169.254.169.254]/latest/meta-data/",
            {"public.example.test": ["93.184.216.34"]},
        ),
    ],
)
async def test_multi_hop_redirect_to_unsafe_target_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    redirect_target: str,
    dns_map: dict[str, list[str]],
) -> None:
    def fake_getaddrinfo(host: str, port: Any, *args: Any, **kwargs: Any) -> list[tuple[Any, ...]]:
        del args, kwargs
        return _addrinfo_for(dns_map[host], int(port))

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            302,
            headers={"location": redirect_target},
            request=req,
        )

    transport = _RecordingTransport(handler)
    fetcher = SafeUrlFetcher(transport=transport)

    with pytest.raises(UnsafeUrlError):
        await fetcher.fetch("https://public.example.test/start")

    assert len(transport.requests) == 1
    assert transport.requests[0].url.host == "93.184.216.34"


@pytest.mark.asyncio
async def test_valid_multi_hop_public_redirect_pins_each_hop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dns_map = {
        "hop1.example.test": ["93.184.216.34"],
        "hop2.example.test": ["93.184.216.35"],
    }

    def fake_getaddrinfo(host: str, port: Any, *args: Any, **kwargs: Any) -> list[tuple[Any, ...]]:
        del args, kwargs
        return _addrinfo_for(dns_map[host], int(port))

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

    def handler(req: httpx.Request) -> httpx.Response:
        if req.headers["host"] == "hop1.example.test":
            return httpx.Response(
                302,
                headers={"location": "https://hop2.example.test:8443/final.txt?v=1"},
                request=req,
            )
        return httpx.Response(
            200,
            headers={"content-type": "text/plain"},
            content=b"reached final",
            request=req,
        )

    transport = _RecordingTransport(handler)
    fetcher = SafeUrlFetcher(transport=transport)

    doc = await fetcher.fetch("https://hop1.example.test/start")

    assert len(transport.requests) == 2
    assert transport.requests[0].url.host == "93.184.216.34"
    assert transport.requests[0].headers["host"] == "hop1.example.test"
    assert transport.requests[0].extensions.get("sni_hostname") == "hop1.example.test"

    assert transport.requests[1].url.host == "93.184.216.35"
    assert transport.requests[1].url.port == 8443
    assert transport.requests[1].headers["host"] == "hop2.example.test:8443"
    assert transport.requests[1].extensions.get("sni_hostname") == "hop2.example.test"

    assert doc.final_url == "https://hop2.example.test:8443/final.txt?v=1"
    assert doc.content == b"reached final"


@pytest.mark.asyncio
async def test_proxy_env_vars_ignored_and_tls_verify_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9999")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9999")
    monkeypatch.setenv("ALL_PROXY", "http://127.0.0.1:9999")

    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, port, *a, **kw: _addrinfo_for(["93.184.216.34"], int(port)),
    )

    observed_kwargs: dict[str, Any] = {}
    original_init = httpx.AsyncClient.__init__

    def spy_init(self: httpx.AsyncClient, *args: Any, **kwargs: Any) -> None:
        observed_kwargs.update(kwargs)
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", spy_init)

    transport = _RecordingTransport(
        lambda req: httpx.Response(
            200,
            headers={"content-type": "text/plain"},
            content=b"ok",
            request=req,
        )
    )
    fetcher = SafeUrlFetcher(transport=transport)

    doc = await fetcher.fetch("https://docs.example.test/page")

    assert doc.content == b"ok"
    assert observed_kwargs.get("trust_env") is False
    assert observed_kwargs.get("verify") is True
    assert observed_kwargs.get("follow_redirects") is False


@pytest.mark.asyncio
async def test_valid_public_ipv6_url_is_bracketed_and_pinned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    public_v6 = "2606:2800:220:1:248:1893:25c8:1946"
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, port, *a, **kw: _addrinfo_for([public_v6], int(port)),
    )

    transport = _RecordingTransport(
        lambda req: httpx.Response(
            200,
            headers={"content-type": "text/plain"},
            content=b"ipv6 ok",
            request=req,
        )
    )
    fetcher = SafeUrlFetcher(transport=transport)

    doc = await fetcher.fetch("https://ipv6.example.test/notes.txt")

    assert len(transport.requests) == 1
    sent = transport.requests[0]
    assert sent.url.host == public_v6
    assert sent.headers["host"] == "ipv6.example.test"
    assert sent.extensions.get("sni_hostname") == "ipv6.example.test"
    assert doc.final_url == "https://ipv6.example.test/notes.txt"
    assert doc.content == b"ipv6 ok"


class _FakeGoalRepo:
    def __init__(self, goal: Goal) -> None:
        self._goal = goal

    async def get_by_id_for_user(self, goal_id: UUID, user_id: UUID) -> Goal | None:
        if goal_id == self._goal.id and user_id == self._goal.user_id:
            return self._goal
        return None


class _FakeSourceRepo:
    def __init__(self) -> None:
        self.saved: list[KnowledgeSource] = []

    async def save_source(self, source: KnowledgeSource) -> KnowledgeSource:
        self.saved.append(source)
        return source


class _FakeFileStore:
    async def save(self, source_id: UUID, ext: str, content: bytes) -> str:
        del source_id, ext, content
        return ""

    async def read(self, uri: str) -> bytes:
        del uri
        return b""

    async def delete(self, uri: str) -> None:
        del uri


class _FakeUoW:
    async def __aenter__(self) -> _FakeUoW:
        return self

    async def __aexit__(self, *args: Any) -> None:
        del args

    async def commit(self) -> None:
        return None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "unsafe_url",
    [
        "http://127.0.0.1/secret",
        "http://10.0.0.1/internal",
        "http://192.168.1.1/router",
        "http://169.254.169.254/latest/meta-data/",
        "http://0.0.0.0/",
        "http://[::1]/secret",
        "http://[fe80::1]/",
        "http://[fc00::1]/",
        "http://[::ffff:127.0.0.1]/secret",
        "http://[::ffff:169.254.169.254]/latest/meta-data/",
        "http://localhost/admin",
        "http://sub.localhost/admin",
        "http://2130706433/decimal-loopback",
        "http://127.1/short-loopback",
        "http://user:pass@example.com/doc.txt",
        "http://@example.com/doc.txt",
        "ftp://example.com/file.txt",
        "file:///etc/passwd",
        "https://example.com:99999/bad-port",
    ],
)
async def test_create_url_intake_rejects_unsafe_urls(unsafe_url: str) -> None:
    user_id = uuid7()
    goal_id = uuid7()
    now = datetime.now(UTC)
    goal = Goal(
        id=goal_id,
        user_id=user_id,
        title="Security",
        raw_description="Learn SSRF defense",
        target_date=None,
        status=GoalStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    source_repo = _FakeSourceRepo()
    use_case = CreateKnowledgeSourceUseCase(
        goal_repository=_FakeGoalRepo(goal),  # type: ignore[arg-type]
        source_repository=source_repo,  # type: ignore[arg-type]
        file_store=_FakeFileStore(),
        uow=_FakeUoW(),  # type: ignore[arg-type]
        max_file_bytes=1024,
    )

    with pytest.raises(UnsafeUrlError):
        await use_case.create_url(
            user_id=user_id,
            goal_id=goal_id,
            title="Unsafe",
            url=unsafe_url,
        )

    assert source_repo.saved == []
