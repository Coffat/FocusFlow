"""Unit tests for isolated Google AI Studio embedding adapter and RAG task_type propagation."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest

from src.planning.application.knowledge import (
    DocumentExtractor,
    SafeUrlFetcher,
    SemanticChunker,
)
from src.planning.application.services.harness_support import (
    load_planning_harness_context_inputs,
)
from src.planning.application.use_cases.knowledge_source_use_cases import (
    IngestKnowledgeSourceUseCase,
)
from src.planning.domain.models.knowledge_source import (
    KnowledgeChunk,
    KnowledgeIngestionStatus,
    KnowledgeSource,
    KnowledgeSourceType,
)
from src.shared_kernel.config import Settings
from src.shared_kernel.infrastructure.external_ai.embedding_adapter import (
    LiteLLMEmbeddingAdapter,
)
from src.shared_kernel.infrastructure.external_ai.litellm_adapter import LiteLLMAdapter


def _make_settings(**overrides: Any) -> Settings:
    defaults: dict[str, Any] = {
        "_env_file": None,
        "llm_provider": "gemini",
        "llm_api_key": "cobhub-proxy-key",
        "llm_base_url": "http://127.0.0.1:8045",
        "embedding_provider": "google_ai_studio",
        "embedding_api_key": "studio-test-secret-key-123",
        "embedding_model": "gemini/gemini-embedding-2",
        "embedding_base_url": "",
        "embedding_dimensions": 768,
    }
    defaults.update(overrides)
    return Settings(**defaults)


@pytest.mark.asyncio
async def test_embedding_adapter_fail_closed_and_never_leaks_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import litellm

    secret_key = "AIzaSySecretKeyShouldNeverLeakInErrors"
    adapter = LiteLLMEmbeddingAdapter()

    # 1. Missing or placeholder embedding_api_key
    for bad_key in ("", "   ", "mock-key", "your-api-key", "your_google_ai_studio_api_key_here"):
        adapter._settings = _make_settings(embedding_api_key=bad_key)
        with pytest.raises(RuntimeError, match="AI_EMBEDDING_PROVIDER_NOT_CONFIGURED"):
            await adapter.embed(["hello"])

    # 2. Invalid embedding_provider
    for bad_provider in ("", "mock", "local_mock", "cobhub", "openai"):
        adapter._settings = _make_settings(embedding_provider=bad_provider)
        with pytest.raises(RuntimeError, match="AI_EMBEDDING_PROVIDER_NOT_CONFIGURED"):
            await adapter.embed(["hello"])

    # 3. Empty embedding_model
    adapter._settings = _make_settings(embedding_model="   ")
    with pytest.raises(RuntimeError, match="AI_EMBEDDING_PROVIDER_NOT_CONFIGURED"):
        await adapter.embed(["hello"])

    # 4. Dimension mismatch (e.g. 3072 != 768) must fail closed without silent truncation
    async def fake_aembedding_wrong_dim(**kwargs: Any) -> Any:
        del kwargs
        return SimpleNamespace(data=[{"embedding": [0.1] * 3072}])

    monkeypatch.setattr(litellm, "aembedding", fake_aembedding_wrong_dim)
    adapter._settings = _make_settings(embedding_api_key=secret_key)
    with pytest.raises(RuntimeError, match="AI_EMBEDDING_DIMENSION_MISMATCH") as dim_exc:
        await adapter.embed(["hello"])
    assert secret_key not in str(dim_exc.value)

    # 5. Upstream error must not leak API key even if included in underlying exception text
    async def fake_aembedding_leaky_error(**kwargs: Any) -> Any:
        del kwargs
        raise RuntimeError(
            f"HTTP 403 at https://generativelanguage.googleapis.com/v1beta?key={secret_key}"
        )

    monkeypatch.setattr(litellm, "aembedding", fake_aembedding_leaky_error)
    with pytest.raises(RuntimeError, match="AI_EMBEDDING_FAILED") as err_exc:
        await adapter.embed(["hello"])
    assert secret_key not in str(err_exc.value)


@pytest.mark.asyncio
async def test_embedding_and_llm_configs_are_completely_isolated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import litellm

    # Env alias check: GEMINI_API_KEY populates embedding_api_key ONLY, never llm_api_key
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_KEY", raising=False)
    monkeypatch.delenv("EMBEDDING_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "studio-only-env-key")
    env_settings = Settings(_env_file=None)
    assert env_settings.embedding_api_key == "studio-only-env-key"
    assert env_settings.llm_api_key == ""

    captured_embed_calls: list[dict[str, Any]] = []

    async def fake_aembedding(**kwargs: Any) -> Any:
        captured_embed_calls.append(dict(kwargs))
        vec = [0.0] * 768
        vec[0] = 1.0
        return SimpleNamespace(data=[{"embedding": vec}])

    monkeypatch.setattr(litellm, "aembedding", fake_aembedding)
    monkeypatch.setenv("RUNNING_IN_DOCKER", "1")

    emb = LiteLLMEmbeddingAdapter()
    emb._settings = _make_settings(
        llm_base_url="http://127.0.0.1:9999",
        llm_api_key="cobhub-key-A",
        embedding_base_url="",
        embedding_api_key="studio-key-A",
    )
    await emb.embed(["doc 1"], task_type="RETRIEVAL_DOCUMENT")

    # Mutate LLM_BASE_URL and LLM_API_KEY: embedding adapter calls remain identical
    emb._settings = _make_settings(
        llm_base_url="http://127.0.0.1:7777",
        llm_api_key="cobhub-key-B",
        embedding_base_url="",
        embedding_api_key="studio-key-A",
    )
    await emb.embed(["doc 1"], task_type="RETRIEVAL_DOCUMENT")

    assert len(captured_embed_calls) == 2
    for call in captured_embed_calls:
        assert call["model"] == "gemini/gemini-embedding-2"
        assert call["api_key"] == "studio-key-A"
        assert call["api_base"] is None
        assert call["dimensions"] == 768
        assert call["task_type"] == "RETRIEVAL_DOCUMENT"

    # Explicit embedding_base_url is never rewritten to host.docker.internal
    emb._settings = _make_settings(embedding_base_url="http://127.0.0.1:8123")
    await emb.embed(["doc 2"])
    assert captured_embed_calls[-1]["api_base"] == "http://127.0.0.1:8123"

    # Mutating embedding_base_url and embedding_api_key does not affect LiteLLMAdapter
    llm_adapter = LiteLLMAdapter()
    llm_adapter._settings = _make_settings(
        llm_base_url="http://127.0.0.1:8045",
        llm_api_key="cobhub-key-final",
        embedding_base_url="https://custom-embedding.invalid",
        embedding_api_key="studio-key-different",
    )
    assert llm_adapter._resolve_base_url() == "http://host.docker.internal:8045"
    assert llm_adapter._settings.llm_api_key == "cobhub-key-final"


@pytest.mark.asyncio
async def test_embedding_adapter_l2_normalizes_unnormalized_vectors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import litellm

    # Unnormalized vector (all 0.5 across 768 dims -> norm = sqrt(768 * 0.25) = sqrt(192) != 1.0)
    raw_vec = [0.5] * 768

    async def fake_aembedding(**kwargs: Any) -> Any:
        del kwargs
        return SimpleNamespace(data=[{"embedding": list(raw_vec)}])

    monkeypatch.setattr(litellm, "aembedding", fake_aembedding)
    emb = LiteLLMEmbeddingAdapter()
    emb._settings = _make_settings()

    result = await emb.embed(["normalize me"])
    assert len(result) == 1
    assert len(result[0]) == 768
    norm = math.sqrt(sum(v * v for v in result[0]))
    assert abs(norm - 1.0) < 1e-6

    # Zero vector must fail closed
    async def fake_zero_embedding(**kwargs: Any) -> Any:
        del kwargs
        return SimpleNamespace(data=[{"embedding": [0.0] * 768}])

    monkeypatch.setattr(litellm, "aembedding", fake_zero_embedding)
    with pytest.raises(RuntimeError, match="AI_EMBEDDING_INVALID_NORM"):
        await emb.embed(["zero vector"])


@pytest.mark.asyncio
async def test_rag_ingest_and_query_use_distinct_task_types_and_store_provenance() -> None:
    user_id = uuid4()
    goal_id = uuid4()
    source_id = uuid4()
    now = datetime.now(UTC)

    source = KnowledgeSource(
        id=source_id,
        user_id=user_id,
        goal_id=goal_id,
        source_type=KnowledgeSourceType.TXT,
        title="Asyncio Notes",
        source_uri="memory://notes.txt",
        content_hash="a" * 64,
        ingestion_status=KnowledgeIngestionStatus.PENDING,
        chunk_count=0,
        provenance_metadata={"original_filename": "notes.txt"},
        error_detail=None,
        created_at=now,
        updated_at=now,
    )

    recorded_calls: list[tuple[list[str], str | None]] = []
    saved_chunks: list[KnowledgeChunk] = []

    class RecordingEmbeddingProvider:
        model_name = "gemini/gemini-embedding-2"
        dimensions = 768

        async def embed(
            self,
            texts: list[str],
            *,
            task_type: str | None = None,
        ) -> list[list[float]]:
            recorded_calls.append((list(texts), task_type))
            unit = [0.0] * 768
            unit[0] = 1.0
            return [list(unit) for _ in texts]

    class FakeSourceRepo:
        async def save_source(self, src: KnowledgeSource) -> KnowledgeSource:
            return src

        async def get_source_for_user(self, sid: UUID, uid: UUID) -> KnowledgeSource | None:
            return source if sid == source_id and uid == user_id else None

        async def list_sources_for_goal(self, gid: UUID, uid: UUID) -> list[KnowledgeSource]:
            del gid, uid
            return [source]

        async def replace_chunks(self, sid: UUID, chunks: list[KnowledgeChunk]) -> None:
            del sid
            saved_chunks.clear()
            saved_chunks.extend(chunks)

        async def hybrid_search(
            self,
            *,
            goal_id: UUID,
            query: str,
            query_embedding: list[float],
            limit: int,
        ) -> list[KnowledgeChunk]:
            del goal_id, query, query_embedding
            return saved_chunks[:limit]

    class FakeFileStore:
        async def save(self, sid: UUID, suffix: str, content: bytes) -> str:
            del sid, suffix, content
            return "memory://notes.txt"

        async def read(self, uri: str) -> bytes:
            del uri
            return b"Python asyncio event loop coordinates coroutines with await."

        async def delete(self, uri: str) -> None:
            del uri

    class FakeUoW:
        async def __aenter__(self) -> FakeUoW:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def commit(self) -> None:
            return None

        async def rollback(self) -> None:
            return None

    provider = RecordingEmbeddingProvider()
    repo = FakeSourceRepo()
    ingest_uc = IngestKnowledgeSourceUseCase(
        source_repository=repo,  # type: ignore[arg-type]
        file_store=FakeFileStore(),  # type: ignore[arg-type]
        embedding_provider=provider,
        url_fetcher=SafeUrlFetcher(),
        extractor=DocumentExtractor(),
        chunker=SemanticChunker(),
        uow=FakeUoW(),  # type: ignore[arg-type]
    )

    indexed = await ingest_uc.execute(source_id=source_id, user_id=user_id)
    assert indexed.ingestion_status is KnowledgeIngestionStatus.INDEXED
    assert len(saved_chunks) >= 1
    assert recorded_calls[0][1] == "RETRIEVAL_DOCUMENT"
    for chunk in saved_chunks:
        assert chunk.provenance_json["embedding_model"] == "gemini/gemini-embedding-2"
        assert chunk.provenance_json["embedding_dimensions"] == 768
        assert chunk.provenance_json["embedding_task_type"] == "RETRIEVAL_DOCUMENT"

    inputs = await load_planning_harness_context_inputs(
        user_id=user_id,
        goal_id=goal_id,
        query_text="How does Python asyncio event loop work?",
        knowledge_source_repo=repo,  # type: ignore[arg-type]
        embedding_provider=provider,
    )
    assert recorded_calls[1][1] == "RETRIEVAL_QUERY"
    assert len(inputs.knowledge_chunks) >= 1
