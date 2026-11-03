from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ConceptVerificationStatus(StrEnum):
    VERIFIED = "VERIFIED"
    AI_PROPOSED = "AI_PROPOSED"
    UNVERIFIED = "UNVERIFIED"
    DEPRECATED = "DEPRECATED"


class LearningResourceType(StrEnum):
    DOCS = "DOCS"
    TUTORIAL = "TUTORIAL"
    VIDEO = "VIDEO"
    BOOK = "BOOK"
    PRACTICE = "PRACTICE"


@dataclass(frozen=True, slots=True)
class LearningResource:
    """Curated learning resource & pedagogical guidance attached to tasks and concepts."""

    title: str
    url: str
    type: str = "DOCS"
    description: str = ""
    domain: str = ""
    concept_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "type": self.type,
            "description": self.description,
            "domain": self.domain,
            "concept_id": self.concept_id,
        }


class PrerequisiteRelationType(StrEnum):
    REQUIRES = "REQUIRES"
    RECOMMENDED_BEFORE = "RECOMMENDED_BEFORE"
    REQUIRED = "REQUIRES"
    RECOMMENDED = "RECOMMENDED_BEFORE"


@dataclass(frozen=True, slots=True)
class LearningConcept:
    """Verified learning concept entity in the Pedagogical Knowledge Base."""

    concept_id: str
    title: str
    summary: str
    domain: str
    difficulty_level: str
    estimated_effort_minutes: int = 60
    keywords: tuple[str, ...] = ()
    learning_outcomes: tuple[str, ...] = ()
    verification_status: ConceptVerificationStatus = ConceptVerificationStatus.VERIFIED
    version: str = "1.0.0"
    search_score: float = 1.0


@dataclass(frozen=True, slots=True)
class ConceptPrerequisiteEdge:
    """Directed edge in the Prerequisite Graph: source_concept_id -> prerequisite_concept_id."""

    source_concept_id: str
    prerequisite_concept_id: str
    relation_type: PrerequisiteRelationType = PrerequisiteRelationType.REQUIRES
    rationale: str = ""
    depth: int = 1


@dataclass(frozen=True, slots=True)
class ConceptPrerequisiteGraph:
    """Subgraph of verified learning concepts and their prerequisite edges."""

    requested_concept_ids: tuple[str, ...]
    nodes: tuple[LearningConcept, ...]
    edges: tuple[ConceptPrerequisiteEdge, ...]
    unresolved_ids: tuple[str, ...]
    max_depth_traversed: int = 3

    def to_dict(self) -> dict[str, Any]:
        return {
            "requested_concept_ids": list(self.requested_concept_ids),
            "nodes": [
                {
                    "concept_id": n.concept_id,
                    "title": n.title,
                    "summary": n.summary,
                    "domain": n.domain,
                    "difficulty_level": n.difficulty_level,
                    "estimated_effort_minutes": n.estimated_effort_minutes,
                    "keywords": list(n.keywords),
                    "learning_outcomes": list(n.learning_outcomes),
                    "verification_status": n.verification_status.value,
                    "version": n.version,
                    "search_score": n.search_score,
                }
                for n in self.nodes
            ],
            "edges": [
                {
                    "source_concept_id": e.source_concept_id,
                    "prerequisite_concept_id": e.prerequisite_concept_id,
                    "relation_type": e.relation_type.value,
                    "rationale": e.rationale,
                    "depth": e.depth,
                }
                for e in self.edges
            ],
            "unresolved_ids": list(self.unresolved_ids),
            "max_depth_traversed": self.max_depth_traversed,
        }
