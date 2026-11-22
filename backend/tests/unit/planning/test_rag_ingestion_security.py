from __future__ import annotations

import asyncio
import io
import logging
import os
import socket
import stat
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx
import pytest
from docx import Document
from uuid6 import uuid7

from src.planning.application.knowledge.document_extractor import (
    DocumentExtractor,
    InvalidDocumentError,
    sanitize_filename,
)
from src.planning.application.knowledge.safe_url_fetcher import (
    SafeUrlFetcher,
    SafeUrlFetchError,
    UnsafeUrlError,
)
from src.planning.application.knowledge.semantic_chunker import SemanticChunker
from src.planning.application.use_cases.knowledge_source_use_cases import (
    CreateKnowledgeSourceUseCase,
    IngestKnowledgeSourceUseCase,
    InvalidKnowledgeSourceError,
)
from src.planning.domain.models.goal import Goal, GoalStatus
from src.planning.domain.models.knowledge_source import (
    KnowledgeChunk,
    KnowledgeIngestionStatus,
    KnowledgeSource,
    KnowledgeSourceType,
)
from src.planning.infrastructure.knowledge.local_file_store import LocalKnowledgeFileStore


def _make_valid_docx_bytes(text: str = "FocusFlow security guide content") -> bytes:
    buf = io.BytesIO()
    doc = Document()
    doc.add_heading("Chapter 1", level=1)
    doc.add_paragraph(text)
    doc.save(buf)
    return buf.getvalue()


def _make_zip_bytes(
    entries: dict[str, bytes],
    *,
    compression: int = zipfile.ZIP_DEFLATED,
) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=compression) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


def _make_goal(user_id: UUID, goal_id: UUID) -> Goal:
    now = datetime.now(UTC)
    return Goal(
        id=goal_id,
        user_id=user_id,
        title="Security Engineering",
        raw_description="Harden RAG ingestion pipeline",
        target_date=None,
        status=GoalStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )


class _FakeGoalRepo:
    def __init__(self, goals: dict[tuple[UUID, UUID], Goal]) -> None:
        self._goals = goals

    async def get_by_id_for_user(self, goal_id: UUID, user_id: UUID) -> Goal | None:
        return self._goals.get((goal_id, user_id))


class _FakeSourceRepo:
    def __init__(self, *, fail_on_save: bool = False) -> None:
        self.sources: dict[UUID, KnowledgeSource] = {}
        self.chunks: dict[UUID, list[KnowledgeChunk]] = {}
        self._fail_on_save = fail_on_save

    async def save_source(self, source: KnowledgeSource) -> KnowledgeSource:
        if self._fail_on_save:
            raise RuntimeError("db persistence failed")
        self.sources[source.id] = source
        return source

    async def get_source_for_user(self, source_id: UUID, user_id: UUID) -> KnowledgeSource | None:
        src = self.sources.get(source_id)
        if src is not None and src.user_id == user_id:
            return src
        return None

    async def list_sources_for_goal(self, goal_id: UUID, user_id: UUID) -> list[KnowledgeSource]:
        return [s for s in self.sources.values() if s.goal_id == goal_id and s.user_id == user_id]

    async def replace_chunks(self, source_id: UUID, chunks: list[KnowledgeChunk]) -> None:
        self.chunks[source_id] = list(chunks)


class _FakeUoW:
    async def __aenter__(self) -> _FakeUoW:
        return self

    async def __aexit__(self, *args: Any) -> None:
        del args

    async def commit(self) -> None:
        return None


class _FakeEmbeddingProvider:
    model_name = "mock-embed"
    dimensions = 768

    def __init__(self, *, error: BaseException | None = None) -> None:
        self._error = error

    async def embed(
        self, texts: list[str], *, task_type: str = "RETRIEVAL_DOCUMENT"
    ) -> list[list[float]]:
        del task_type
        if self._error is not None:
            raise self._error
        return [[0.01] * 768 for _ in texts]


class _RecordingTransport(httpx.AsyncBaseTransport):
    def __init__(self, handler: Any) -> None:
        self._handler = handler
        self.requests: list[httpx.Request] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self._handler(request)


def _addrinfo_for(addresses: list[str], port: int = 443) -> list[tuple[Any, ...]]:
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (addr, port)) for addr in addresses]


# ---------------------------------------------------------------------------
# 1. Extension / Content / Magic-Byte / MIME Mismatch Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("filename", "payload", "content_type"),
    [
        # PNG disguised as PDF
        ("diagram.pdf", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR", "application/pdf"),
        # Windows PE executable disguised as PDF
        ("installer.pdf", b"MZ\x90\x00\x03\x00\x00\x00", "application/pdf"),
        # Random text disguised as PDF
        ("fake.pdf", b"Hello, I am not a PDF file", "application/pdf"),
        # Valid PDF magic but spoofed image MIME
        ("spoofed.pdf", b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\n%%EOF", "image/png"),
        # Plain text disguised as DOCX
        (
            "notes.docx",
            b"Just plain text, not a ZIP archive",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        # Valid ZIP without word/document.xml disguised as DOCX
        (
            "not_a_docx.docx",
            _make_zip_bytes({"hello.txt": b"not a word document"}),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        # Valid DOCX but spoofed text/plain MIME
        ("spoofed.docx", _make_valid_docx_bytes(), "text/plain"),
        # Binary null bytes disguised as TXT
        ("binary.txt", b"hello\x00world\x00binary", "text/plain"),
        # Invalid UTF-8 bytes disguised as TXT
        ("invalid_utf8.txt", b"\xff\xfe\xfd\x80\x81\x82", "text/plain"),
        # PNG bytes disguised as TXT
        ("image.txt", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR", "image/png"),
        # .url extension must NOT be accepted via file upload
        ("shortcut.url", b"[InternetShortcut]\nURL=http://127.0.0.1/\n", "text/plain"),
    ],
)
async def test_create_file_rejects_mismatched_magic_bytes_and_mime(
    tmp_path: Path,
    filename: str,
    payload: bytes,
    content_type: str,
) -> None:
    user_id = uuid7()
    goal_id = uuid7()
    store = LocalKnowledgeFileStore(str(tmp_path / "uploads"))
    source_repo = _FakeSourceRepo()
    use_case = CreateKnowledgeSourceUseCase(
        goal_repository=_FakeGoalRepo({(goal_id, user_id): _make_goal(user_id, goal_id)}),  # type: ignore[arg-type]
        source_repository=source_repo,  # type: ignore[arg-type]
        file_store=store,
        uow=_FakeUoW(),  # type: ignore[arg-type]
        max_file_bytes=5 * 1024 * 1024,
    )

    with pytest.raises(InvalidKnowledgeSourceError):
        await use_case.create_file(
            user_id=user_id,
            goal_id=goal_id,
            title="Untrusted File",
            filename=filename,
            content=payload,
            content_type=content_type,
        )

    assert source_repo.sources == {}
    # No file should have been written to disk
    upload_dir = tmp_path / "uploads"
    assert not upload_dir.exists() or list(upload_dir.iterdir()) == []


# ---------------------------------------------------------------------------
# 2. Malformed / Corrupt PDF & DOCX Handling (Sanitized Domain Errors)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extractor_handles_corrupt_pdf_with_sanitized_error() -> None:
    corrupt_pdf = b"%PDF-1.7\nthis is completely broken xref/trailer data \x00\xff"
    extractor = DocumentExtractor()

    with pytest.raises(InvalidDocumentError) as exc_info:
        await extractor.extract(corrupt_pdf, KnowledgeSourceType.PDF)

    msg = str(exc_info.value)
    assert "Traceback" not in msg
    assert "/Users/" not in msg
    assert "pypdf" not in msg.lower()


@pytest.mark.asyncio
async def test_extractor_handles_corrupt_docx_xml_with_sanitized_error() -> None:
    corrupt_docx = _make_zip_bytes(
        {
            "[Content_Types].xml": b"<Types></Types>",
            "word/document.xml": b"<w:document><broken xml",
        }
    )
    extractor = DocumentExtractor()

    with pytest.raises(InvalidDocumentError) as exc_info:
        await extractor.extract(corrupt_docx, KnowledgeSourceType.DOCX)

    msg = str(exc_info.value)
    assert "Traceback" not in msg
    assert "lxml" not in msg.lower()


# ---------------------------------------------------------------------------
# 3. DOCX Decompression Bomb & Zip-Slip Protection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_docx_high_compression_ratio_bomb_is_rejected(tmp_path: Path) -> None:
    # 2 MB of repeated 'A' compresses to ~2 KB -> ratio ~1000x (> 100x limit)
    bomb_payload = _make_zip_bytes(
        {
            "[Content_Types].xml": b"<Types/>",
            "word/document.xml": b"A" * (2 * 1024 * 1024),
        },
        compression=zipfile.ZIP_DEFLATED,
    )
    assert len(bomb_payload) < 20_000  # small compressed size, huge expansion

    user_id = uuid7()
    goal_id = uuid7()
    use_case = CreateKnowledgeSourceUseCase(
        goal_repository=_FakeGoalRepo({(goal_id, user_id): _make_goal(user_id, goal_id)}),  # type: ignore[arg-type]
        source_repository=_FakeSourceRepo(),  # type: ignore[arg-type]
        file_store=LocalKnowledgeFileStore(str(tmp_path / "uploads")),
        uow=_FakeUoW(),  # type: ignore[arg-type]
        max_file_bytes=5 * 1024 * 1024,
    )

    with pytest.raises(InvalidKnowledgeSourceError):
        await use_case.create_file(
            user_id=user_id,
            goal_id=goal_id,
            title="Zip Bomb",
            filename="bomb.docx",
            content=bomb_payload,
        )


@pytest.mark.asyncio
async def test_docx_oversized_uncompressed_total_is_rejected() -> None:
    # Use a low uncompressed cap to test total uncompressed size enforcement
    payload = _make_zip_bytes(
        {
            "[Content_Types].xml": b"<Types/>",
            "word/document.xml": b"<w:document>" + (b"x" * 2048) + b"</w:document>",
        },
        compression=zipfile.ZIP_STORED,
    )
    extractor = DocumentExtractor(docx_max_uncompressed_bytes=1024)

    with pytest.raises(InvalidDocumentError):
        await extractor.extract(payload, KnowledgeSourceType.DOCX)


@pytest.mark.asyncio
async def test_docx_excessive_entry_count_is_rejected() -> None:
    entries: dict[str, bytes] = {
        "[Content_Types].xml": b"<Types/>",
        "word/document.xml": b"<w:document/>",
    }
    for i in range(20):
        entries[f"word/extra_{i}.xml"] = b"<x/>"
    payload = _make_zip_bytes(entries, compression=zipfile.ZIP_STORED)
    extractor = DocumentExtractor(docx_max_entries=10)

    with pytest.raises(InvalidDocumentError):
        await extractor.extract(payload, KnowledgeSourceType.DOCX)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "malicious_entry",
    [
        "../../etc/passwd",
        "/etc/passwd",
        "..\\..\\windows\\system.ini",
        "word/../../../evil.xml",
    ],
)
async def test_docx_zip_slip_entries_are_rejected(malicious_entry: str) -> None:
    payload = _make_zip_bytes(
        {
            "[Content_Types].xml": b"<Types/>",
            "word/document.xml": b"<w:document/>",
            malicious_entry: b"pwned",
        },
        compression=zipfile.ZIP_STORED,
    )
    extractor = DocumentExtractor()

    with pytest.raises(InvalidDocumentError):
        await extractor.extract(payload, KnowledgeSourceType.DOCX)


# ---------------------------------------------------------------------------
# 4. Size Limits & Extracted Text Length Cap
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_oversized_upload_and_extracted_text_cap_are_enforced(tmp_path: Path) -> None:
    user_id = uuid7()
    goal_id = uuid7()
    use_case = CreateKnowledgeSourceUseCase(
        goal_repository=_FakeGoalRepo({(goal_id, user_id): _make_goal(user_id, goal_id)}),  # type: ignore[arg-type]
        source_repository=_FakeSourceRepo(),  # type: ignore[arg-type]
        file_store=LocalKnowledgeFileStore(str(tmp_path / "uploads")),
        uow=_FakeUoW(),  # type: ignore[arg-type]
        max_file_bytes=128,
    )

    with pytest.raises(InvalidKnowledgeSourceError):
        await use_case.create_file(
            user_id=user_id,
            goal_id=goal_id,
            title="Too Big",
            filename="big.txt",
            content=b"a" * 129,
        )

    extractor = DocumentExtractor(max_extracted_chars=50)
    with pytest.raises(InvalidDocumentError):
        await extractor.extract(b"a" * 100, KnowledgeSourceType.TXT)


# ---------------------------------------------------------------------------
# 5. Path Traversal Filenames & Private Temp Directory Permissions (0700)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw_name", "expected_safe"),
    [
        ("../../etc/passwd.pdf", "passwd.pdf"),
        ("..\\..\\evil.txt", "evil.txt"),
        ("foo\x00bar.txt", "foobar.txt"),
        ("sub/dir/notes.docx", "notes.docx"),
        ("../../../.hidden.txt", "hidden.txt"),
    ],
)
def test_sanitize_filename_strips_traversal_and_null_bytes(
    raw_name: str, expected_safe: str
) -> None:
    cleaned = sanitize_filename(raw_name)
    assert ".." not in cleaned
    assert "/" not in cleaned
    assert "\\" not in cleaned
    assert "\x00" not in cleaned
    assert cleaned == expected_safe


@pytest.mark.asyncio
async def test_create_file_uses_uuid_filename_and_private_permissions(tmp_path: Path) -> None:
    user_id = uuid7()
    goal_id = uuid7()
    upload_root = tmp_path / "private_knowledge_store"
    store = LocalKnowledgeFileStore(str(upload_root))
    source_repo = _FakeSourceRepo()
    use_case = CreateKnowledgeSourceUseCase(
        goal_repository=_FakeGoalRepo({(goal_id, user_id): _make_goal(user_id, goal_id)}),  # type: ignore[arg-type]
        source_repository=source_repo,  # type: ignore[arg-type]
        file_store=store,
        uow=_FakeUoW(),  # type: ignore[arg-type]
        max_file_bytes=1024 * 1024,
    )

    source = await use_case.create_file(
        user_id=user_id,
        goal_id=goal_id,
        title="",
        filename="../../etc/passwd.txt",
        content=b"safe study notes",
        content_type="text/plain",
    )

    assert source.source_uri is not None
    saved_path = Path(source.source_uri)
    assert saved_path.parent == upload_root.resolve()
    assert saved_path.name == f"{source.id}.txt"
    assert "passwd" not in saved_path.name
    assert source.provenance_metadata["original_filename"] == "passwd.txt"
    assert ".." not in source.title

    if os.name != "nt":
        dir_mode = stat.S_IMODE(os.stat(upload_root).st_mode)
        file_mode = stat.S_IMODE(os.stat(saved_path).st_mode)
        assert dir_mode == 0o700
        assert file_mode == 0o600


# ---------------------------------------------------------------------------
# 6. Guaranteed Temp File Cleanup (Intake Fail, Success, Fail, Timeout, Cancel)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_file_cleans_up_temp_file_on_db_failure(tmp_path: Path) -> None:
    user_id = uuid7()
    goal_id = uuid7()
    upload_root = tmp_path / "uploads"
    store = LocalKnowledgeFileStore(str(upload_root))
    use_case = CreateKnowledgeSourceUseCase(
        goal_repository=_FakeGoalRepo({(goal_id, user_id): _make_goal(user_id, goal_id)}),  # type: ignore[arg-type]
        source_repository=_FakeSourceRepo(fail_on_save=True),  # type: ignore[arg-type]
        file_store=store,
        uow=_FakeUoW(),  # type: ignore[arg-type]
        max_file_bytes=1024 * 1024,
    )

    with pytest.raises(RuntimeError, match="db persistence failed"):
        await use_case.create_file(
            user_id=user_id,
            goal_id=goal_id,
            title="Notes",
            filename="notes.txt",
            content=b"valid content",
        )

    assert list(upload_root.iterdir()) == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "outcome",
    ["success", "failure", "timeout", "cancelled"],
)
async def test_ingest_cleans_up_temp_file_across_all_lifecycle_outcomes(
    tmp_path: Path,
    outcome: str,
) -> None:
    user_id = uuid7()
    goal_id = uuid7()
    upload_root = tmp_path / "uploads"
    store = LocalKnowledgeFileStore(str(upload_root))
    source_repo = _FakeSourceRepo()

    creator = CreateKnowledgeSourceUseCase(
        goal_repository=_FakeGoalRepo({(goal_id, user_id): _make_goal(user_id, goal_id)}),  # type: ignore[arg-type]
        source_repository=source_repo,  # type: ignore[arg-type]
        file_store=store,
        uow=_FakeUoW(),  # type: ignore[arg-type]
        max_file_bytes=1024 * 1024,
    )
    created = await creator.create_file(
        user_id=user_id,
        goal_id=goal_id,
        title="Lifecycle Test",
        filename="study.txt",
        content=b"Clean architecture ensures domain independence and security.",
        content_type="text/plain",
    )
    assert created.source_uri is not None
    temp_path = Path(created.source_uri)
    assert temp_path.exists()

    error_map: dict[str, BaseException | None] = {
        "success": None,
        "failure": RuntimeError("internal embedding host 10.0.1.55:8080 refused connection"),
        "timeout": TimeoutError("embedding timed out at 10.0.1.55"),
        "cancelled": asyncio.CancelledError(),
    }
    ingestor = IngestKnowledgeSourceUseCase(
        source_repository=source_repo,  # type: ignore[arg-type]
        file_store=store,
        embedding_provider=_FakeEmbeddingProvider(error=error_map[outcome]),  # type: ignore[arg-type]
        url_fetcher=SafeUrlFetcher(),
        extractor=DocumentExtractor(),
        chunker=SemanticChunker(),
        uow=_FakeUoW(),  # type: ignore[arg-type]
    )

    if outcome == "success":
        result = await ingestor.execute(source_id=created.id, user_id=user_id)
        assert result.ingestion_status is KnowledgeIngestionStatus.INDEXED
    elif outcome == "cancelled":
        with pytest.raises(asyncio.CancelledError):
            await ingestor.execute(source_id=created.id, user_id=user_id)
    else:
        with pytest.raises((RuntimeError, TimeoutError)):
            await ingestor.execute(source_id=created.id, user_id=user_id)
        persisted = source_repo.sources[created.id]
        assert persisted.ingestion_status is KnowledgeIngestionStatus.FAILED
        # Internal IP/host must NEVER leak into persisted error_detail
        assert persisted.error_detail is not None
        assert "10.0.1.55" not in persisted.error_detail

    # Temp file MUST be deleted in all 4 outcomes!
    assert not temp_path.exists()


# ---------------------------------------------------------------------------
# 7. URL Ingestion Content-Type Allowlist & Sanitized Error Messages
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_content_type",
    [
        "application/octet-stream",
        "application/x-msdownload",
        "application/x-executable",
        "image/png",
        "video/mp4",
    ],
)
async def test_safe_url_fetcher_rejects_disallowed_content_types(
    monkeypatch: pytest.MonkeyPatch,
    bad_content_type: str,
) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, port, *a, **kw: _addrinfo_for(["93.184.216.34"], int(port)),
    )
    transport = _RecordingTransport(
        lambda req: httpx.Response(
            200,
            headers={"content-type": bad_content_type},
            content=b"binary data",
            request=req,
        )
    )
    fetcher = SafeUrlFetcher(transport=transport)

    with pytest.raises(UnsafeUrlError):
        await fetcher.fetch("https://docs.example.test/download")


@pytest.mark.asyncio
async def test_safe_url_fetcher_sanitizes_http_and_connection_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, port, *a, **kw: _addrinfo_for(["93.184.216.34"], int(port)),
    )

    # HTTP 502 error must NOT leak pinned IP 93.184.216.34
    transport_502 = _RecordingTransport(
        lambda req: httpx.Response(502, content=b"bad gateway", request=req)
    )
    fetcher_502 = SafeUrlFetcher(transport=transport_502)
    with pytest.raises(SafeUrlFetchError) as exc_502:
        await fetcher_502.fetch("https://docs.example.test/page")
    assert "93.184.216.34" not in str(exc_502.value)
    assert "docs.example.test" not in str(exc_502.value)

    # Socket/ConnectError must NOT leak internal proxy/socket details
    def _raise_connect(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused to 93.184.216.34:443 via /var/run/proxy.sock")

    fetcher_conn = SafeUrlFetcher(transport=_RecordingTransport(_raise_connect))
    with pytest.raises(SafeUrlFetchError) as exc_conn:
        await fetcher_conn.fetch("https://docs.example.test/page")
    assert "93.184.216.34" not in str(exc_conn.value)
    assert "/var/run/proxy.sock" not in str(exc_conn.value)


# ---------------------------------------------------------------------------
# 8. No Raw Document Content Logged
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_raw_document_content_is_logged(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret_sentinel = "TOP_SECRET_LEARNER_DOCUMENT_PAYLOAD_987654321"
    user_id = uuid7()
    goal_id = uuid7()
    store = LocalKnowledgeFileStore(str(tmp_path / "uploads"))
    source_repo = _FakeSourceRepo()

    creator = CreateKnowledgeSourceUseCase(
        goal_repository=_FakeGoalRepo({(goal_id, user_id): _make_goal(user_id, goal_id)}),  # type: ignore[arg-type]
        source_repository=source_repo,  # type: ignore[arg-type]
        file_store=store,
        uow=_FakeUoW(),  # type: ignore[arg-type]
        max_file_bytes=1024 * 1024,
    )
    ingestor = IngestKnowledgeSourceUseCase(
        source_repository=source_repo,  # type: ignore[arg-type]
        file_store=store,
        embedding_provider=_FakeEmbeddingProvider(),  # type: ignore[arg-type]
        url_fetcher=SafeUrlFetcher(),
        extractor=DocumentExtractor(),
        chunker=SemanticChunker(),
        uow=_FakeUoW(),  # type: ignore[arg-type]
    )

    with caplog.at_level(logging.DEBUG):
        created = await creator.create_file(
            user_id=user_id,
            goal_id=goal_id,
            title="Private Study Notes",
            filename="notes.txt",
            content=secret_sentinel.encode("utf-8"),
            content_type="text/plain",
        )
        await ingestor.execute(source_id=created.id, user_id=user_id)

    assert secret_sentinel not in caplog.text
