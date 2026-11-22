from __future__ import annotations

import asyncio
import io
import os
import re
import zipfile
import zlib
from dataclasses import dataclass
from pathlib import PurePosixPath

from docx import Document
from pypdf import PdfReader

from src.planning.domain.models.knowledge_source import KnowledgeSourceType

_PDF_MAGIC = b"%PDF-"
_ZIP_MAGIC = b"PK\x03\x04"

_ALLOWED_UPLOAD_MIMES: dict[KnowledgeSourceType, frozenset[str]] = {
    KnowledgeSourceType.PDF: frozenset({"application/pdf", "application/x-pdf"}),
    KnowledgeSourceType.DOCX: frozenset(
        {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/zip",
            "application/x-zip-compressed",
        }
    ),
    KnowledgeSourceType.TXT: frozenset(
        {
            "text/plain",
            "text/markdown",
            "text/x-markdown",
            "text/csv",
            "text/html",
            "application/json",
            "application/xhtml+xml",
        }
    ),
}

_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")
_DISALLOWED_TEXT_CONTROL_RE = re.compile(r"[\x00-\x08\x0e-\x1f\x7f]")


class InvalidDocumentError(ValueError):
    code = "INVALID_KNOWLEDGE_SOURCE"


def sanitize_filename(filename: str) -> str:
    """Strip path traversal segments, null bytes, and control chars from a filename."""
    cleaned = _CONTROL_CHAR_RE.sub("", filename or "")
    normalized = cleaned.replace("\\", "/")
    base = os.path.basename(normalized).strip()
    # Strip leading dots/spaces and any residual '..' traversal tokens
    while ".." in base:
        base = base.replace("..", "")
    base = base.lstrip(". ").strip()
    if len(base) > 200:
        stem, dot, ext = base.rpartition(".")
        if dot and ext and len(ext) <= 10:
            base = f"{stem[: 200 - len(ext) - 1]}.{ext}"
        else:
            base = base[:200]
    return base or "knowledge"


def _validate_mime_consistency(
    source_type: KnowledgeSourceType,
    content_type: str | None,
) -> None:
    if not content_type:
        return
    media_type = content_type.split(";", 1)[0].strip().lower()
    if not media_type or media_type == "application/octet-stream":
        return
    allowed = _ALLOWED_UPLOAD_MIMES.get(source_type)
    if allowed is not None and media_type not in allowed:
        raise InvalidDocumentError("Loại MIME của tệp không khớp với định dạng tài liệu")


def _validate_zip_archive_safety(
    content: bytes,
    *,
    max_entries: int,
    max_uncompressed_bytes: int,
    max_compression_ratio: float,
) -> None:
    if not content.startswith(_ZIP_MAGIC):
        raise InvalidDocumentError("Tệp DOCX không có chữ ký định dạng hợp lệ")
    try:
        with zipfile.ZipFile(io.BytesIO(content), "r") as zf:
            infos = zf.infolist()
            if not infos:
                raise InvalidDocumentError("Tệp DOCX rỗng hoặc bị hỏng")
            if len(infos) > max_entries:
                raise InvalidDocumentError("Tệp DOCX chứa quá nhiều thành phần bên trong")

            total_uncompressed = 0
            total_compressed = 0
            names: set[str] = set()

            for info in infos:
                name = info.filename
                if "\x00" in name or name.startswith("/") or name.startswith("\\"):
                    raise InvalidDocumentError("Tệp DOCX chứa đường dẫn nội bộ không hợp lệ")
                normalized = name.replace("\\", "/")
                parts = PurePosixPath(normalized).parts
                if ".." in parts:
                    raise InvalidDocumentError("Tệp DOCX chứa đường dẫn nội bộ không hợp lệ")
                first_segment = normalized.split("/", 1)[0]
                if ":" in first_segment:
                    raise InvalidDocumentError("Tệp DOCX chứa đường dẫn nội bộ không hợp lệ")

                if info.file_size < 0 or info.compress_size < 0:
                    raise InvalidDocumentError("Tệp DOCX bị hỏng hoặc không hợp lệ")

                total_uncompressed += info.file_size
                total_compressed += info.compress_size

                if total_uncompressed > max_uncompressed_bytes:
                    raise InvalidDocumentError(
                        "Tệp DOCX vượt quá giới hạn dung lượng giải nén cho phép"
                    )

                if info.file_size > 0:
                    if info.compress_size == 0 and info.compress_type != zipfile.ZIP_STORED:
                        raise InvalidDocumentError("Tệp DOCX có tỷ lệ nén bất thường")
                    if info.compress_size > 0 and (
                        info.file_size / info.compress_size > max_compression_ratio
                    ):
                        raise InvalidDocumentError("Tệp DOCX có tỷ lệ nén vượt quá ngưỡng an toàn")

                names.add(normalized)

            if total_compressed > 0 and (
                total_uncompressed / total_compressed > max_compression_ratio
            ):
                raise InvalidDocumentError("Tệp DOCX có tỷ lệ nén vượt quá ngưỡng an toàn")

            if "word/document.xml" not in names or "[Content_Types].xml" not in names:
                raise InvalidDocumentError("Tệp DOCX thiếu cấu trúc tài liệu Word hợp lệ")
    except InvalidDocumentError:
        raise
    except (zipfile.BadZipFile, zipfile.LargeZipFile, zlib.error, OSError, ValueError) as exc:
        raise InvalidDocumentError("Tệp DOCX bị hỏng hoặc không đúng định dạng hợp lệ") from exc


def validate_uploaded_document(
    content: bytes,
    source_type: KnowledgeSourceType,
    *,
    content_type: str | None = None,
    max_bytes: int = 20 * 1024 * 1024,
    docx_max_entries: int = 500,
    docx_max_uncompressed_bytes: int = 50 * 1024 * 1024,
    docx_max_compression_ratio: float = 100.0,
) -> None:
    """Validate uploaded/fetched document size, MIME consistency, magic bytes, and archive safety."""
    if not content or len(content) > max_bytes:
        raise InvalidDocumentError("Tệp học liệu phải có dung lượng từ 1 byte đến 20 MB")

    _validate_mime_consistency(source_type, content_type)

    if source_type is KnowledgeSourceType.PDF:
        if not content.startswith(_PDF_MAGIC):
            raise InvalidDocumentError("Tệp PDF không có chữ ký định dạng hợp lệ")
        return

    if source_type is KnowledgeSourceType.DOCX:
        _validate_zip_archive_safety(
            content,
            max_entries=docx_max_entries,
            max_uncompressed_bytes=docx_max_uncompressed_bytes,
            max_compression_ratio=docx_max_compression_ratio,
        )
        return

    if source_type is KnowledgeSourceType.TXT:
        if b"\x00" in content:
            raise InvalidDocumentError("Tệp văn bản không được chứa dữ liệu nhị phân")
        try:
            decoded = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise InvalidDocumentError("Tệp văn bản phải sử dụng mã hóa UTF-8 hợp lệ") from exc
        if _DISALLOWED_TEXT_CONTROL_RE.search(decoded):
            raise InvalidDocumentError("Tệp văn bản chứa ký tự điều khiển nhị phân không hợp lệ")
        return

    raise InvalidDocumentError("Chỉ hỗ trợ tệp PDF, DOCX hoặc TXT")


@dataclass(frozen=True, slots=True)
class ExtractedSection:
    text: str
    section_title: str | None = None
    page_number: int | None = None


class DocumentExtractor:
    def __init__(
        self,
        *,
        max_file_bytes: int = 20 * 1024 * 1024,
        max_extracted_chars: int = 500_000,
        pdf_max_pages: int = 500,
        docx_max_entries: int = 500,
        docx_max_uncompressed_bytes: int = 50 * 1024 * 1024,
        docx_max_compression_ratio: float = 100.0,
    ) -> None:
        self._max_file_bytes = max_file_bytes
        self._max_extracted_chars = max_extracted_chars
        self._pdf_max_pages = pdf_max_pages
        self._docx_max_entries = docx_max_entries
        self._docx_max_uncompressed_bytes = docx_max_uncompressed_bytes
        self._docx_max_compression_ratio = docx_max_compression_ratio

    async def extract(
        self, content: bytes, source_type: KnowledgeSourceType
    ) -> list[ExtractedSection]:
        return await asyncio.to_thread(self._extract_sync, content, source_type)

    def _extract_sync(
        self, content: bytes, source_type: KnowledgeSourceType
    ) -> list[ExtractedSection]:
        validate_uploaded_document(
            content,
            source_type,
            max_bytes=self._max_file_bytes,
            docx_max_entries=self._docx_max_entries,
            docx_max_uncompressed_bytes=self._docx_max_uncompressed_bytes,
            docx_max_compression_ratio=self._docx_max_compression_ratio,
        )

        if source_type is KnowledgeSourceType.TXT:
            text = content.decode("utf-8").strip()
            if len(text) > self._max_extracted_chars:
                raise InvalidDocumentError("Nội dung trích xuất từ tài liệu vượt quá giới hạn")
            return [ExtractedSection(text=text)] if text else []

        if source_type is KnowledgeSourceType.PDF:
            try:
                reader = PdfReader(io.BytesIO(content))
                if len(reader.pages) > self._pdf_max_pages:
                    raise InvalidDocumentError("Tệp PDF vượt quá số trang tối đa cho phép")
                pdf_sections: list[ExtractedSection] = []
                total_chars = 0
                for index, page in enumerate(reader.pages, start=1):
                    text = (page.extract_text() or "").strip()
                    if text:
                        total_chars += len(text)
                        if total_chars > self._max_extracted_chars:
                            raise InvalidDocumentError(
                                "Nội dung trích xuất từ tài liệu vượt quá giới hạn"
                            )
                        pdf_sections.append(ExtractedSection(text=text, page_number=index))
                return pdf_sections
            except InvalidDocumentError:
                raise
            except Exception as exc:
                raise InvalidDocumentError(
                    "Tệp PDF bị hỏng hoặc không đúng định dạng hợp lệ"
                ) from exc

        if source_type is KnowledgeSourceType.DOCX:
            try:
                document = Document(io.BytesIO(content))
                docx_sections: list[ExtractedSection] = []
                heading: str | None = None
                buffer: list[str] = []
                total_chars = 0
                for paragraph in document.paragraphs:
                    text = paragraph.text.strip()
                    if not text:
                        continue
                    total_chars += len(text)
                    if total_chars > self._max_extracted_chars:
                        raise InvalidDocumentError(
                            "Nội dung trích xuất từ tài liệu vượt quá giới hạn"
                        )
                    if (
                        paragraph.style
                        and paragraph.style.name
                        and paragraph.style.name.startswith("Heading")
                    ):
                        if buffer:
                            docx_sections.append(ExtractedSection("\n".join(buffer), heading))
                            buffer = []
                        heading = text
                    else:
                        buffer.append(text)
                if buffer:
                    docx_sections.append(ExtractedSection("\n".join(buffer), heading))
                return docx_sections
            except InvalidDocumentError:
                raise
            except Exception as exc:
                raise InvalidDocumentError(
                    "Tệp DOCX bị hỏng hoặc không đúng định dạng hợp lệ"
                ) from exc

        raise InvalidDocumentError("Chỉ hỗ trợ tệp PDF, DOCX hoặc TXT")
