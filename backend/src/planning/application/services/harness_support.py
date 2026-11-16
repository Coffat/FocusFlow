import asyncio
import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from src.account.public_api import (
    ConceptMasterySnapshotDTO,
    LearnerMemoryItemSnapshotDTO,
    LearnerMemoryQueryPort,
)
from src.planning.application.knowledge.hybrid_retrieval import reciprocal_rank_fusion
from src.planning.application.ports.knowledge_source_repository_port import (
    KnowledgeSourceRepositoryPort,
)
from src.planning.domain.models.knowledge_source import KnowledgeChunk
from src.shared_kernel.application.embedding_port import EmbeddingProviderPort
from src.shared_kernel.application.harness.models import PromptTemplate
from src.shared_kernel.application.harness.prompt_registry import build_prompt_audit_metadata
from src.shared_kernel.config import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PlanningHarnessContextInputs:
    """Loaded learner memory and RAG chunk inputs for 5-layer planning ContextEngine."""

    memory_items: tuple[LearnerMemoryItemSnapshotDTO, ...] = ()
    concept_masteries: tuple[ConceptMasterySnapshotDTO, ...] = ()
    knowledge_chunks: tuple[KnowledgeChunk, ...] = ()


async def load_planning_harness_context_inputs(
    *,
    user_id: UUID,
    goal_id: UUID,
    query_text: str,
    learner_memory_port: LearnerMemoryQueryPort | None = None,
    knowledge_source_repo: KnowledgeSourceRepositoryPort | None = None,
    embedding_provider: EmbeddingProviderPort | None = None,
    rag_limit: int = 5,
    memory_limit: int = 8,
    mastery_limit: int = 12,
) -> PlanningHarnessContextInputs:
    """Fetch LearnerMemory/ConceptMastery and Hybrid RAG chunks when enabled by config."""
    settings = get_settings()
    memories: tuple[LearnerMemoryItemSnapshotDTO, ...] = ()
    masteries: tuple[ConceptMasterySnapshotDTO, ...] = ()
    chunks: tuple[KnowledgeChunk, ...] = ()

    if settings.learner_memory_enabled and learner_memory_port is not None:
        loaded_memories = await learner_memory_port.list_active_memory_items(
            user_id,
            limit=memory_limit,
        )
        loaded_masteries = await learner_memory_port.list_concept_masteries(user_id)
        memories = tuple(loaded_memories)
        masteries = tuple(loaded_masteries[:mastery_limit])

    clean_query = query_text.strip()
    if settings.knowledge_rag_enabled and knowledge_source_repo is not None and clean_query:
        has_sources = True
        list_sources_fn = getattr(knowledge_source_repo, "list_sources_for_goal", None)
        if callable(list_sources_fn):
            try:
                goal_sources = await list_sources_fn(goal_id, user_id)
                if isinstance(goal_sources, (list, tuple)):
                    has_sources = len(goal_sources) > 0
            except (ValueError, RuntimeError, OSError) as exc:
                logger.warning(
                    "harness_list_sources_failed",
                    extra={"goal_id": str(goal_id), "error_type": type(exc).__name__},
                )
                has_sources = True

        if has_sources:
            query_embedding: list[float] = [0.0] * 768
            if embedding_provider is not None:
                try:
                    vectors = await asyncio.wait_for(
                        embedding_provider.embed(
                            [clean_query[:1000]],
                            task_type="RETRIEVAL_QUERY",
                        ),
                        timeout=5.0,
                    )
                    if vectors and len(vectors[0]) == 768:
                        query_embedding = vectors[0]
                except (TimeoutError, ValueError, RuntimeError, OSError) as exc:
                    logger.warning(
                        "harness_query_embedding_fallback",
                        extra={"goal_id": str(goal_id), "error_type": type(exc).__name__},
                    )
            raw_chunks = await knowledge_source_repo.hybrid_search(
                goal_id=goal_id,
                query=clean_query[:300],
                query_embedding=query_embedding,
                limit=rag_limit,
            )
            if len(raw_chunks) > 1:
                # Fuse semantic & lexical ordering deterministically using shared RRF utility
                semantic_order = list(raw_chunks)
                lexical_order = sorted(
                    raw_chunks,
                    key=lambda c: sum(
                        1 for token in clean_query.lower().split() if token in c.content.lower()
                    ),
                    reverse=True,
                )
                fused_chunks = reciprocal_rank_fusion(
                    lexical_order,
                    semantic_order,
                    limit=rag_limit,
                )
                chunks = tuple(fused_chunks)
            else:
                chunks = tuple(raw_chunks[:rag_limit])

    return PlanningHarnessContextInputs(
        memory_items=memories,
        concept_masteries=masteries,
        knowledge_chunks=chunks,
    )


def compact_context_snapshot(
    *,
    goal_id: UUID,
    roadmap_id: UUID | None,
    stage: str,
    inputs: PlanningHarnessContextInputs,
    layer_tokens: dict[Any, int] | None = None,
    prompt_template: PromptTemplate | None = None,
) -> dict[str, Any]:
    """Build a PII-free workflow context snapshot for WorkflowRun auditing."""
    snapshot: dict[str, Any] = {
        "goal_id": str(goal_id),
        "roadmap_id": str(roadmap_id) if roadmap_id is not None else None,
        "stage": stage,
        "memory_items_count": len(inputs.memory_items),
        "concept_masteries_count": len(inputs.concept_masteries),
        "rag_chunks_count": len(inputs.knowledge_chunks),
        "layer_tokens": {
            getattr(k, "value", str(k)): int(v) for k, v in (layer_tokens or {}).items()
        },
    }
    if prompt_template is not None:
        snapshot.update(build_prompt_audit_metadata(prompt_template))
    return snapshot
