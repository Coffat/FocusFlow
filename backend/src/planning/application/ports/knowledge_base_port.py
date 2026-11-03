from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from src.planning.domain.models.knowledge_concept import (
    ConceptPrerequisiteGraph,
    LearningConcept,
    LearningResource,
)


@runtime_checkable
class KnowledgeBasePort(Protocol):
    """Read-only Output Port for querying the verified Pedagogical Knowledge Base."""

    async def search_concepts(
        self,
        query: str,
        *,
        domain: str | None = None,
        learner_level: str | None = None,
        limit: int = 10,
    ) -> list[LearningConcept]:
        """Search verified learning concepts by keyword/domain with deterministic backend scoring."""
        ...

    async def get_prerequisite_graph(
        self,
        concept_ids: Sequence[str],
        *,
        max_depth: int = 3,
    ) -> ConceptPrerequisiteGraph:
        """Traverse the verified prerequisite DAG up to max_depth and report unresolved_ids."""
        ...

    async def get_learning_resources_and_guidance(
        self,
        *,
        query: str | None = None,
        domain: str | None = None,
        concept_ids: Sequence[str] = (),
        task_type: str | None = None,
        limit: int = 10,
    ) -> list[LearningResource]:
        """Retrieve curated verified learning resources and pedagogical guidance for task decomposition."""
        ...
