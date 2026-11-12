from collections.abc import Hashable, Sequence


def reciprocal_rank_fusion[T: Hashable](
    lexical: Sequence[T], semantic: Sequence[T], *, limit: int, rank_constant: int = 60
) -> list[T]:
    scores: dict[T, float] = {}
    first_seen: dict[T, int] = {}
    order = 0
    for ranked in (lexical, semantic):
        for rank, item in enumerate(ranked, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (rank_constant + rank)
            first_seen.setdefault(item, order)
            order += 1
    return sorted(scores, key=lambda item: (-scores[item], first_seen[item]))[: max(0, limit)]
