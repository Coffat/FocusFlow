"""Live opt-in verification for Google AI Studio embedding (Nhóm 3)."""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from src.shared_kernel.config import Settings
from src.shared_kernel.infrastructure.external_ai.embedding_adapter import (
    LiteLLMEmbeddingAdapter,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT_PATH = REPO_ROOT / "docs" / "experiments" / "group3_embedding_verification.json"

_DOCS: list[dict[str, str]] = [
    {
        "id": "doc_asyncio",
        "topic": "python_asyncio",
        "text": (
            "Python asyncio uses a single-threaded event loop to schedule coroutines, tasks, "
            "and non-blocking I/O operations via async def and await."
        ),
    },
    {
        "id": "doc_postgres_index",
        "topic": "postgresql_indexing",
        "text": (
            "PostgreSQL B-Tree indexes speed up equality and range filters, while GIN indexes "
            "accelerate JSONB containment and full-text tsvector search queries."
        ),
    },
    {
        "id": "doc_hexagonal",
        "topic": "hexagonal_architecture",
        "text": (
            "Hexagonal architecture isolates pure domain entities and application use cases "
            "behind explicit ports, keeping FastAPI routers and SQLAlchemy repositories in outer adapters."
        ),
    },
    {
        "id": "doc_angular_signals",
        "topic": "angular_signals",
        "text": (
            "Angular Signals provide fine-grained reactive primitives using signal, computed, "
            "and effect for zoneless change detection with OnPush standalone components."
        ),
    },
    {
        "id": "doc_spaced_repetition",
        "topic": "learning_science",
        "text": (
            "Spaced repetition combined with active recall schedules review intervals just before "
            "forgetting occurs, strengthening long-term memory retention."
        ),
    },
    {
        "id": "doc_docker_multistage",
        "topic": "docker_containers",
        "text": (
            "Docker multi-stage builds separate compile-time build toolchains from minimal runtime "
            "images, reducing container image size and attack surface in production."
        ),
    },
]

_QUERIES: list[dict[str, str]] = [
    {
        "id": "q1",
        "query": "Làm sao tối ưu truy vấn tìm kiếm JSONB và full-text search trong PostgreSQL?",
        "expected_doc_id": "doc_postgres_index",
    },
    {
        "id": "q2",
        "query": "How do I keep domain business logic independent from FastAPI and SQLAlchemy?",
        "expected_doc_id": "doc_hexagonal",
    },
    {
        "id": "q3",
        "query": "Cách quản lý state reactive không cần Zone.js trong Angular hiện đại",
        "expected_doc_id": "doc_angular_signals",
    },
    {
        "id": "q4",
        "query": "Kỹ thuật ôn tập ngắt quãng để ghi nhớ kiến thức lâu dài",
        "expected_doc_id": "doc_spaced_repetition",
    },
    {
        "id": "q5",
        "query": "How does an event loop coordinate non-blocking coroutines in Python?",
        "expected_doc_id": "doc_asyncio",
    },
]


def _l2_norm(vec: list[float]) -> float:
    return math.sqrt(sum(v * v for v in vec))


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = _l2_norm(a)
    nb = _l2_norm(b)
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return dot / (na * nb)


@pytest.mark.asyncio
@pytest.mark.live_embedding
async def test_live_google_ai_studio_embedding_and_mini_retrieval() -> None:
    """Verify live 768d L2-normalized Google AI Studio embeddings and >= 4/5 mini retrieval."""
    settings = Settings()
    if not (settings.embedding_api_key or "").strip():
        pytest.skip("Missing EMBEDDING_API_KEY / GEMINI_API_KEY in environment or .env")

    adapter = LiteLLMEmbeddingAdapter()

    # 1. Verify RETRIEVAL_DOCUMENT and RETRIEVAL_QUERY individually
    doc_texts = [d["text"] for d in _DOCS]
    query_texts = [q["query"] for q in _QUERIES]

    doc_vecs_typed = await adapter.embed(doc_texts, task_type="RETRIEVAL_DOCUMENT")
    query_vecs_typed = await adapter.embed(query_texts, task_type="RETRIEVAL_QUERY")

    assert len(doc_vecs_typed) == len(_DOCS)
    assert len(query_vecs_typed) == len(_QUERIES)
    for vec in [*doc_vecs_typed, *query_vecs_typed]:
        assert len(vec) == 768
        norm = _l2_norm(vec)
        assert 0.999 <= norm <= 1.001

    # 2. Baseline without task_type
    doc_vecs_baseline = await adapter.embed(doc_texts, task_type=None)
    query_vecs_baseline = await adapter.embed(query_texts, task_type=None)
    for vec in [*doc_vecs_baseline, *query_vecs_baseline]:
        assert len(vec) == 768
        norm = _l2_norm(vec)
        assert 0.999 <= norm <= 1.001

    def _evaluate(
        q_vecs: list[list[float]],
        d_vecs: list[list[float]],
    ) -> dict[str, Any]:
        correct = 0
        details: list[dict[str, Any]] = []
        for q_idx, q_item in enumerate(_QUERIES):
            scored = [
                (_DOCS[d_idx]["id"], _cosine_similarity(q_vecs[q_idx], d_vecs[d_idx]))
                for d_idx in range(len(_DOCS))
            ]
            scored.sort(key=lambda pair: pair[1], reverse=True)
            top1_id, top1_score = scored[0]
            top2_id, top2_score = scored[1]
            is_correct = top1_id == q_item["expected_doc_id"]
            if is_correct:
                correct += 1
            details.append(
                {
                    "query_id": q_item["id"],
                    "expected_doc_id": q_item["expected_doc_id"],
                    "predicted_top1_doc_id": top1_id,
                    "top1_score": round(top1_score, 6),
                    "top2_doc_id": top2_id,
                    "top2_score": round(top2_score, 6),
                    "margin": round(top1_score - top2_score, 6),
                    "correct": is_correct,
                }
            )
        return {
            "top1_correct": correct,
            "total_queries": len(_QUERIES),
            "accuracy": round(correct / len(_QUERIES), 4),
            "details": details,
        }

    typed_eval = _evaluate(query_vecs_typed, doc_vecs_typed)
    baseline_eval = _evaluate(query_vecs_baseline, doc_vecs_baseline)

    report = {
        "timestamp": datetime.now(UTC).isoformat(),
        "provider": settings.embedding_provider,
        "model": adapter.model_name,
        "dimensions": adapter.dimensions,
        "base_url": settings.embedding_base_url or "google_ai_studio_default",
        "docs_count": len(_DOCS),
        "queries_count": len(_QUERIES),
        "doc_norms_range": [
            round(min(_l2_norm(v) for v in doc_vecs_typed), 6),
            round(max(_l2_norm(v) for v in doc_vecs_typed), 6),
        ],
        "query_norms_range": [
            round(min(_l2_norm(v) for v in query_vecs_typed), 6),
            round(max(_l2_norm(v) for v in query_vecs_typed), 6),
        ],
        "with_task_type": typed_eval,
        "baseline_no_task_type": baseline_eval,
    }

    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(
        f"[live_embedding] model={adapter.model_name} dim={adapter.dimensions} "
        f"with_task_type={typed_eval['top1_correct']}/{typed_eval['total_queries']} "
        f"baseline={baseline_eval['top1_correct']}/{baseline_eval['total_queries']}"
    )
    assert typed_eval["top1_correct"] >= 4
