import re
from dataclasses import dataclass

from src.execution.domain.exceptions.execution_exceptions import TakeawayValidationFailedError

MIN_TAKEAWAY_CHARS: int = 30
MIN_DISTINCT_WORDS: int = 6
MAX_CONSECUTIVE_SAME_CHAR: int = 5
MAX_SOURCE_OVERLAP_RATIO: float = 0.85
MIN_UNIQUE_CHARS: int = 6
MIN_WORD_DIVERSITY_RATIO: float = 0.40

_WORD_RE = re.compile(r"[0-9A-Za-zÀ-ỹ]+", re.UNICODE)
_ALPHA_RE = re.compile(r"[A-Za-zÀ-ỹ]", re.UNICODE)
_CONSECUTIVE_REPEAT_RE = re.compile(r"(.)\1{" + str(MAX_CONSECUTIVE_SAME_CHAR) + r",}")


@dataclass(frozen=True, slots=True)
class TakeawayValidationResult:
    is_valid: bool
    reasons: tuple[str, ...] = ()
    token_overlap_ratio: float = 0.0
    distinct_word_count: int = 0


class TakeawayGuard:
    """Layer 1 Deterministic Anti-Gaming Guard for Key Takeaways (SRS FR-SESSION-002, 0 AI quota).

    Enforces:
    1. Length >= 30 characters (trimmed & whitespace-normalized).
    2. >= 6 distinct meaningful words.
    3. Anti-gibberish / anti-repetition:
       - No > 5 consecutive identical characters (e.g. 'aaaaaa').
       - Contains alphabetic characters (not pure digits/symbols).
       - Minimum character & word diversity to reject 'asdfasdf...' or 'ok ok ok ok ok ok'.
    4. Anti-copy-paste: normalized token overlap vs task title/description < 85%.
    """

    @classmethod
    def evaluate(
        cls,
        takeaway: str | None,
        *,
        task_title: str = "",
        task_description: str | None = None,
    ) -> TakeawayValidationResult:
        reasons: list[str] = []
        normalized = " ".join((takeaway or "").split())

        if len(normalized) < MIN_TAKEAWAY_CHARS:
            reasons.append(
                f"Độ dài Key Takeaway phải từ {MIN_TAKEAWAY_CHARS} ký tự trở lên (hiện có {len(normalized)} ký tự)."
            )

        if not _ALPHA_RE.search(normalized):
            reasons.append(
                "Key Takeaway phải chứa từ ngữ có nghĩa, không thể chỉ là số hoặc ký tự đặc biệt."
            )

        if _CONSECUTIVE_REPEAT_RE.search(normalized.lower()):
            reasons.append("Phát hiện chuỗi ký tự lặp lại vô nghĩa vượt quá 5 ký tự liên tiếp.")

        words = [w.lower() for w in _WORD_RE.findall(normalized)]
        distinct_words = set(words)
        if len(distinct_words) < MIN_DISTINCT_WORDS:
            reasons.append(
                f"Key Takeaway cần tối thiểu {MIN_DISTINCT_WORDS} từ riêng biệt có nghĩa (hiện có {len(distinct_words)} từ)."
            )

        non_space_chars = [c.lower() for c in normalized if not c.isspace()]
        if non_space_chars and len(set(non_space_chars)) < MIN_UNIQUE_CHARS:
            reasons.append("Nội dung Key Takeaway có độ đa dạng ký tự quá thấp (nghi ngờ gõ rác).")

        if (
            len(words) >= MIN_DISTINCT_WORDS
            and (len(distinct_words) / len(words)) < MIN_WORD_DIVERSITY_RATIO
        ):
            reasons.append("Nội dung Key Takeaway lặp lại quá nhiều từ giống nhau.")

        overlap_ratio = 0.0
        source_text = f"{task_title or ''} {task_description or ''}".strip()
        source_tokens = {w.lower() for w in _WORD_RE.findall(source_text)}
        if distinct_words and source_tokens:
            overlap_ratio = len(distinct_words & source_tokens) / len(distinct_words)
            if overlap_ratio >= MAX_SOURCE_OVERLAP_RATIO:
                reasons.append(
                    "Nội dung Key Takeaway trùng lặp quá cao (>= 85%) với tiêu đề/mô tả bài học. Hãy diễn đạt bằng lời của chính bạn."
                )

        return TakeawayValidationResult(
            is_valid=len(reasons) == 0,
            reasons=tuple(reasons),
            token_overlap_ratio=round(overlap_ratio, 4),
            distinct_word_count=len(distinct_words),
        )

    @classmethod
    def validate(
        cls,
        takeaway: str | None,
        *,
        task_title: str = "",
        task_description: str | None = None,
    ) -> TakeawayValidationResult:
        result = cls.evaluate(
            takeaway,
            task_title=task_title,
            task_description=task_description,
        )
        if not result.is_valid:
            raise TakeawayValidationFailedError(
                message=" ".join(result.reasons),
                reasons=list(result.reasons),
            )
        return result
