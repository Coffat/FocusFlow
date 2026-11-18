import re
from collections.abc import Iterable, Sequence

_NUMBER_RE = re.compile(r"(?<![A-Za-z0-9_.-])(-?\d+(?:\.\d+)?)(?![A-Za-z0-9_])")
_ORDINAL_PREFIX_RE = re.compile(
    r"(?:bước|tuần|chặng|tầng|mốc|v|uc-)\s*$",
    re.IGNORECASE,
)
_STRUCTURAL_NUMBERS: frozenset[float] = frozenset({0.0, 1.0, 2.0, 3.0, 7.0, 100.0})


class QuantitativeFaithfulnessValidator:
    """Pure-Python validator ensuring Weekly Review / Prove Mode prose cites only computed numbers."""

    @staticmethod
    def extract_claim_numbers(narrative: str) -> list[float]:
        """Extract quantitative claim numbers while ignoring structural ordinals (e.g. '1.', 'Bước 2')."""
        numbers: list[float] = []
        for match in _NUMBER_RE.finditer(narrative):
            start, end = match.span(1)
            prefix = narrative[max(0, start - 10) : start]
            suffix = narrative[end : min(len(narrative), end + 2)]
            if suffix.startswith(".") and (end + 1 == len(narrative) or narrative[end + 1] == " "):
                # List ordinal marker like "1. "
                continue
            if _ORDINAL_PREFIX_RE.search(prefix):
                continue
            numbers.append(float(match.group(1)))
        return numbers

    @classmethod
    def score_faithfulness(
        cls,
        narrative: str,
        allowed_numbers: Iterable[int | float],
    ) -> tuple[int, int]:
        """Return `(matched_claims, total_claims)` for numeric claims inside `narrative`."""
        allowed = {float(v) for v in allowed_numbers} | _STRUCTURAL_NUMBERS
        claims = cls.extract_claim_numbers(narrative)
        if not claims:
            return 0, 0
        matched = sum(1 for val in claims if any(abs(val - ref) <= 1e-3 for ref in allowed))
        return matched, len(claims)

    @classmethod
    def compute_raw_faithfulness(
        cls,
        narratives: Sequence[str],
        allowed_numbers: Iterable[int | float],
    ) -> float:
        """Compute matched/total numeric claim ratio across all summary sections."""
        allowed_list = list(allowed_numbers)
        total_matched = 0
        total_claims = 0
        for text in narratives:
            matched, total = cls.score_faithfulness(text, allowed_list)
            total_matched += matched
            total_claims += total
        if total_claims == 0:
            return 1.0
        return round(total_matched / total_claims, 4)

    @classmethod
    def validate_or_sanitize(
        cls,
        narrative: str,
        allowed_numbers: Iterable[int | float],
        fallback_narrative: str,
    ) -> tuple[str, float]:
        """Return `(narrative, ratio)` if all claims are faithful, else `(fallback_narrative, 1.0)`."""
        matched, total = cls.score_faithfulness(narrative, allowed_numbers)
        if total == 0 or matched == total:
            return narrative, 1.0
        return fallback_narrative, 1.0


__all__ = ["QuantitativeFaithfulnessValidator"]
