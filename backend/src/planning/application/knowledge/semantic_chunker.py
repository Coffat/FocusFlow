from dataclasses import dataclass

from .document_extractor import ExtractedSection


@dataclass(frozen=True, slots=True)
class SemanticChunk:
    content: str
    token_count: int
    section_title: str | None
    page_number: int | None


class SemanticChunker:
    """Deterministic 300-600 token chunker with ~13% overlap."""

    def __init__(self, *, target_tokens: int = 450, overlap_tokens: int = 60) -> None:
        if not 300 <= target_tokens <= 600:
            raise ValueError("target_tokens must be between 300 and 600")
        if not 30 <= overlap_tokens <= 90:
            raise ValueError("overlap_tokens must be between 30 and 90")
        self._target = target_tokens
        self._overlap = overlap_tokens

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return text.split()

    def chunk(self, sections: list[ExtractedSection]) -> list[SemanticChunk]:
        result: list[SemanticChunk] = []
        for section in sections:
            words = self._tokens(section.text)
            cursor = 0
            while cursor < len(words):
                end = min(len(words), cursor + self._target)
                part = words[cursor:end]
                if part:
                    result.append(
                        SemanticChunk(
                            content=" ".join(part),
                            token_count=len(part),
                            section_title=section.section_title,
                            page_number=section.page_number,
                        )
                    )
                if end >= len(words):
                    break
                cursor = max(cursor + 1, end - self._overlap)
        return result
