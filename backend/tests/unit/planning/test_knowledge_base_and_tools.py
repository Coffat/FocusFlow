import asyncio

import pytest

from src.planning.application.ports.knowledge_base_port import KnowledgeBasePort
from src.planning.application.services.knowledge_tool_dispatcher import (
    KnowledgeToolDispatcher,
    RoadmapPipelineStage,
)
from src.planning.domain.exceptions.planning_exceptions import (
    ToolCallLimitExceededError,
    ToolInputValidationError,
    UnauthorizedToolCallError,
)
from src.planning.domain.models.knowledge_concept import (
    ConceptPrerequisiteGraph,
    ConceptVerificationStatus,
    LearningConcept,
    LearningResource,
)
from src.planning.infrastructure.repositories.sqlalchemy_knowledge_base_repository import (
    VERIFIED_SEED_CONCEPTS,
    VERIFIED_SEED_EDGES,
    InMemoryKnowledgeBaseRepository,
)


@pytest.mark.asyncio
async def test_knowledge_base_search_strictly_filters_verified_and_normalizes_scores() -> None:
    unverified_concept = LearningConcept(
        concept_id="unverified-hyperscale-secret",
        title="Kiến trúc Hyperscale Chưa Xác Thực",
        summary="Khái niệm thử nghiệm chưa qua kiểm duyệt.",
        domain="backend",
        difficulty_level="ADVANCED",
        estimated_effort_minutes=120,
        keywords=("fastapi", "python", "hyperscale"),
        learning_outcomes=("Chưa kiểm chứng",),
        verification_status=ConceptVerificationStatus.UNVERIFIED,
    )
    deprecated_concept = LearningConcept(
        concept_id="deprecated-python2",
        title="Python 2.7 Legacy",
        summary="Ngôn ngữ Python 2 đã ngừng hỗ trợ.",
        domain="python",
        difficulty_level="BEGINNER",
        estimated_effort_minutes=60,
        keywords=("python", "legacy"),
        learning_outcomes=("Không sử dụng",),
        verification_status=ConceptVerificationStatus.DEPRECATED,
    )

    repo = InMemoryKnowledgeBaseRepository(
        concepts=[*VERIFIED_SEED_CONCEPTS, unverified_concept, deprecated_concept],
        edges=list(VERIFIED_SEED_EDGES),
    )

    results = await repo.search_concepts("python fastapi", limit=10)
    assert len(results) >= 2
    returned_ids = {c.concept_id for c in results}
    assert "unverified-hyperscale-secret" not in returned_ids
    assert "deprecated-python2" not in returned_ids
    for c in results:
        assert c.verification_status == ConceptVerificationStatus.VERIFIED
        assert 0.0 < c.search_score <= 1.0


@pytest.mark.asyncio
async def test_knowledge_base_prerequisite_graph_multi_hop_and_unresolved_ids() -> None:
    repo = InMemoryKnowledgeBaseRepository()
    graph = await repo.get_prerequisite_graph(
        concept_ids=["sqlalchemy-async-alembic", "non-existent-concept-xyz"],
        max_depth=3,
    )

    node_ids = {n.concept_id for n in graph.nodes}
    assert "sqlalchemy-async-alembic" in node_ids
    assert "fastapi-routing-pydantic" in node_ids
    assert "sql-relational-modeling" in node_ids
    assert "py-async-concurrency" in node_ids
    assert "py-oop-dataclasses" in node_ids
    assert "non-existent-concept-xyz" in graph.unresolved_ids
    assert len(graph.edges) >= 4
    assert all(1 <= e.depth <= 3 for e in graph.edges)


@pytest.mark.asyncio
async def test_tool_dispatcher_stage_allowlist_validation_quota_and_timeout() -> None:
    repo = InMemoryKnowledgeBaseRepository()

    # 1. Stage GOAL_CLARIFICATION and PEDAGOGICAL_JUDGE forbid all tools
    for forbidden_stage in (
        RoadmapPipelineStage.GOAL_CLARIFICATION,
        RoadmapPipelineStage.PEDAGOGICAL_JUDGE,
    ):
        dispatcher_forbidden = KnowledgeToolDispatcher(repo, stage=forbidden_stage)
        assert dispatcher_forbidden.get_allowed_tool_declarations() == []
        with pytest.raises(UnauthorizedToolCallError):
            await dispatcher_forbidden.dispatch("search_learning_concepts", {"query": "python"})

    # 2. Stage MILESTONE_PLANNING allows both read-only tools and validates inputs
    dispatcher = KnowledgeToolDispatcher(
        repo,
        stage=RoadmapPipelineStage.MILESTONE_PLANNING,
        max_tool_calls=4,
    )
    assert len(dispatcher.get_allowed_tool_declarations()) == 2

    with pytest.raises(UnauthorizedToolCallError):
        await dispatcher.dispatch("delete_all_concepts", {"query": "python"})

    with pytest.raises(ToolInputValidationError):
        await dispatcher.dispatch("search_learning_concepts", {"query": "   "})

    with pytest.raises(ToolInputValidationError):
        await dispatcher.dispatch("search_learning_concepts", {"query": "a" * 205})

    with pytest.raises(ToolInputValidationError):
        await dispatcher.dispatch("get_concept_prerequisite_graph", {"concept_ids": []})

    with pytest.raises(ToolInputValidationError):
        await dispatcher.dispatch(
            "get_concept_prerequisite_graph",
            {"concept_ids": [f"c-{i}" for i in range(16)]},
        )

    # 3. Execute 4 valid calls, then verify 5th call raises ToolCallLimitExceededError
    for idx in range(4):
        out = await dispatcher.dispatch(
            "search_learning_concepts", {"query": f"python {idx}", "limit": 3}
        )
        assert out["count"] >= 1

    assert dispatcher.call_count == 4
    with pytest.raises(ToolCallLimitExceededError):
        await dispatcher.dispatch("search_learning_concepts", {"query": "fastapi"})


@pytest.mark.asyncio
async def test_tool_dispatcher_enforces_timeout() -> None:
    class _SlowKnowledgeBase(KnowledgeBasePort):
        async def search_concepts(
            self,
            query: str,
            *,
            domain: str | None = None,
            learner_level: str | None = None,
            limit: int = 10,
        ) -> list[LearningConcept]:
            _ = (query, domain, learner_level, limit)
            await asyncio.sleep(0.3)
            return []

        async def get_prerequisite_graph(
            self,
            concept_ids: list[str],
            *,
            max_depth: int = 3,
        ) -> ConceptPrerequisiteGraph:
            _ = (concept_ids, max_depth)
            await asyncio.sleep(0.3)
            return ConceptPrerequisiteGraph(
                requested_concept_ids=(),
                nodes=(),
                edges=(),
                unresolved_ids=(),
                max_depth_traversed=1,
            )

        async def get_learning_resources_and_guidance(
            self,
            *,
            query: str | None = None,
            domain: str | None = None,
            concept_ids: list[str] = (),
            task_type: str | None = None,
            limit: int = 10,
        ) -> list[LearningResource]:
            _ = (query, domain, concept_ids, task_type, limit)
            await asyncio.sleep(0.3)
            return []

    slow_dispatcher = KnowledgeToolDispatcher(
        _SlowKnowledgeBase(),
        stage=RoadmapPipelineStage.TASK_DECOMPOSITION,
        timeout_seconds=0.1,
    )
    with pytest.raises(TimeoutError):
        await slow_dispatcher.dispatch("search_learning_concepts", {"query": "python"})


@pytest.mark.asyncio
async def test_get_learning_resources_and_guidance_tool_execution() -> None:
    repo = InMemoryKnowledgeBaseRepository()
    dispatcher = KnowledgeToolDispatcher(
        repo,
        stage=RoadmapPipelineStage.TASK_DECOMPOSITION,
        max_tool_calls=4,
    )
    allowed_tools = {decl.name for decl in dispatcher.get_allowed_tool_declarations()}
    assert "get_learning_resources_and_guidance" in allowed_tools

    res = await dispatcher.dispatch(
        "get_learning_resources_and_guidance",
        {
            "query": "FastAPI Pydantic",
            "domain": "backend",
            "concept_ids": ["fastapi-routing-pydantic"],
            "task_type": "PRACTICE",
            "limit": 3,
        },
    )
    assert res["count"] >= 1
    assert any(
        "fastapi" in r["title"].lower() or "fastapi" in r["url"].lower() for r in res["resources"]
    )
    assert len(dispatcher.collected_resources) >= 1
