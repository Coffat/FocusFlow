import asyncio
import io
from dataclasses import dataclass

from docx import Document
from pypdf import PdfReader

from src.planning.domain.models.knowledge_source import KnowledgeSourceType


@dataclass(frozen=True, slots=True)
class ExtractedSection:
    text: str
    section_title: str | None = None
    page_number: int | None = None


class DocumentExtractor:
    async def extract(
        self, content: bytes, source_type: KnowledgeSourceType
    ) -> list[ExtractedSection]:
        return await asyncio.to_thread(self._extract_sync, content, source_type)

    @staticmethod
    def _extract_sync(content: bytes, source_type: KnowledgeSourceType) -> list[ExtractedSection]:
        if source_type is KnowledgeSourceType.TXT:
            text = content.decode("utf-8", errors="replace").strip()
            return [ExtractedSection(text=text)] if text else []
        if source_type is KnowledgeSourceType.PDF:
            reader = PdfReader(io.BytesIO(content))
            pdf_sections: list[ExtractedSection] = []
            for index, page in enumerate(reader.pages, start=1):
                text = (page.extract_text() or "").strip()
                if text:
                    pdf_sections.append(ExtractedSection(text=text, page_number=index))
            return pdf_sections
        if source_type is KnowledgeSourceType.DOCX:
            document = Document(io.BytesIO(content))
            docx_sections: list[ExtractedSection] = []
            heading: str | None = None
            buffer: list[str] = []
            for paragraph in document.paragraphs:
                text = paragraph.text.strip()
                if not text:
                    continue
                if paragraph.style and paragraph.style.name.startswith("Heading"):
                    if buffer:
                        docx_sections.append(ExtractedSection("\n".join(buffer), heading))
                        buffer = []
                    heading = text
                else:
                    buffer.append(text)
            if buffer:
                docx_sections.append(ExtractedSection("\n".join(buffer), heading))
            return docx_sections
        raise ValueError(f"Unsupported document type: {source_type}")
