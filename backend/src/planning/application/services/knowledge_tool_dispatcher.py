import asyncio
from enum import StrEnum
from typing import Any

from src.planning.application.ports.knowledge_base_port import KnowledgeBasePort
from src.planning.domain.exceptions.planning_exceptions import (
    ToolCallLimitExceededError,
    ToolInputValidationError,
    UnauthorizedToolCallError,
)
from src.planning.domain.models.knowledge_concept import (
    ConceptPrerequisiteGraph,
    LearningConcept,
    LearningResource,
)
from src.shared_kernel.application.llm_port import (
    LLMToolCallResultDTO,
    LLMToolDeclarationDTO,
)


class RoadmapPipelineStage(StrEnum):
    """Pipeline stages in the AI Learning Roadmap Generation Engine."""

    GOAL_CLARIFICATION = "GOAL_CLARIFICATION"
    MILESTONE_PLANNING = "MILESTONE_PLANNING"
    TASK_DECOMPOSITION = "TASK_DECOMPOSITION"
    PEDAGOGICAL_JUDGE = "PEDAGOGICAL_JUDGE"


STAGE_ALLOWED_TOOLS: dict[RoadmapPipelineStage, frozenset[str]] = {
    RoadmapPipelineStage.GOAL_CLARIFICATION: frozenset(),
    RoadmapPipelineStage.MILESTONE_PLANNING: frozenset(
        {"search_learning_concepts", "get_concept_prerequisite_graph"}
    ),
    RoadmapPipelineStage.TASK_DECOMPOSITION: frozenset(
        {
            "search_learning_concepts",
            "get_concept_prerequisite_graph",
            "get_learning_resources_and_guidance",
        }
    ),
    RoadmapPipelineStage.PEDAGOGICAL_JUDGE: frozenset(),
}

SEARCH_LEARNING_CONCEPTS_TOOL_DECL = LLMToolDeclarationDTO(
    name="search_learning_concepts",
    description=(
        "Tìm kiếm các khái niệm học thuật đã được xác thực (VERIFIED) trong Knowledge Base "
        "theo từ khóa, miền kiến thức và trình độ người học."
    ),
    parameters_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Từ khóa tìm kiếm khái niệm học tập (1..200 ký tự).",
            },
            "domain": {
                "type": "string",
                "description": "Miền kiến thức tùy chọn (ví dụ: python, backend, dsa, frontend, system-design, machine-learning).",
            },
            "learner_level": {
                "type": "string",
                "description": "Trình độ người học (BEGINNER, INTERMEDIATE, ADVANCED).",
            },
            "limit": {
                "type": "integer",
                "description": "Số lượng kết quả tối đa (1..10, mặc định 10).",
            },
        },
        "required": ["query"],
    },
)

GET_PREREQUISITE_GRAPH_TOOL_DECL = LLMToolDeclarationDTO(
    name="get_concept_prerequisite_graph",
    description=(
        "Truy vấn đồ thị tiên quyết có hướng (DAG) giữa các khái niệm học thuật đã xác thực "
        "tối đa đến độ sâu max_depth (1..5)."
    ),
    parameters_schema={
        "type": "object",
        "properties": {
            "concept_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Danh sách mã khái niệm cần tra cứu tiên quyết (1..15 phần tử).",
            },
            "max_depth": {
                "type": "integer",
                "description": "Độ sâu duyệt đồ thị tiên quyết tối đa (1..5, mặc định 3).",
            },
        },
        "required": ["concept_ids"],
    },
)

GET_LEARNING_RESOURCES_AND_GUIDANCE_TOOL_DECL = LLMToolDeclarationDTO(
    name="get_learning_resources_and_guidance",
    description=(
        "Tra cứu danh sách nguồn học liệu chuẩn hóa (DOCS, TUTORIAL, VIDEO, BOOK, PRACTICE) "
        "và hướng dẫn sư phạm từ Knowledge Base để đính kèm vào các nhiệm vụ học tập theo chủ đề, miền hoặc loại task."
    ),
    parameters_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Từ khóa tìm kiếm tài liệu học tập hoặc tiêu đề nhiệm vụ (tùy chọn, 1..200 ký tự).",
            },
            "domain": {
                "type": "string",
                "description": "Miền kiến thức tùy chọn (ví dụ: python, backend, dsa, frontend, system-design).",
            },
            "concept_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Danh sách mã khái niệm liên quan đến nhiệm vụ (tối đa 15).",
            },
            "task_type": {
                "type": "string",
                "enum": ["THEORY", "PRACTICE", "REVIEW", "PROJECT"],
                "description": "Loại nhiệm vụ học tập để hệ thống ưu tiên định dạng tài liệu phù hợp.",
            },
            "limit": {
                "type": "integer",
                "description": "Số lượng tài liệu học tập tối đa (1..10, mặc định 5).",
            },
        },
    },
)

ALL_KNOWLEDGE_TOOL_DECLARATIONS: dict[str, LLMToolDeclarationDTO] = {
    SEARCH_LEARNING_CONCEPTS_TOOL_DECL.name: SEARCH_LEARNING_CONCEPTS_TOOL_DECL,
    GET_PREREQUISITE_GRAPH_TOOL_DECL.name: GET_PREREQUISITE_GRAPH_TOOL_DECL,
    GET_LEARNING_RESOURCES_AND_GUIDANCE_TOOL_DECL.name: GET_LEARNING_RESOURCES_AND_GUIDANCE_TOOL_DECL,
}


class KnowledgeToolDispatcher:
    """Read-only tool dispatcher with stage allowlist, input validation, call quota & timeout."""

    def __init__(
        self,
        knowledge_base: KnowledgeBasePort,
        *,
        stage: RoadmapPipelineStage,
        max_tool_calls: int = 4,
        timeout_seconds: float = 5.0,
    ) -> None:
        self._kb = knowledge_base
        self._stage = stage
        self._max_tool_calls = max(0, max_tool_calls)
        self._timeout_seconds = max(0.1, timeout_seconds)
        self._call_count = 0
        self._call_history: list[LLMToolCallResultDTO] = []
        self._collected_concepts: dict[str, LearningConcept] = {}
        self._collected_graphs: list[ConceptPrerequisiteGraph] = []
        self._collected_resources: list[LearningResource] = []

    @property
    def stage(self) -> RoadmapPipelineStage:
        return self._stage

    @property
    def call_count(self) -> int:
        return self._call_count

    @property
    def max_tool_calls(self) -> int:
        return self._max_tool_calls

    @property
    def call_history(self) -> tuple[LLMToolCallResultDTO, ...]:
        return tuple(self._call_history)

    @property
    def collected_concepts(self) -> tuple[LearningConcept, ...]:
        return tuple(self._collected_concepts.values())

    @property
    def collected_graphs(self) -> tuple[ConceptPrerequisiteGraph, ...]:
        return tuple(self._collected_graphs)

    @property
    def collected_resources(self) -> tuple[LearningResource, ...]:
        return tuple(self._collected_resources)

    def get_allowed_tool_declarations(self) -> list[LLMToolDeclarationDTO]:
        allowed_names = STAGE_ALLOWED_TOOLS.get(self._stage, frozenset())
        return [
            decl for name, decl in ALL_KNOWLEDGE_TOOL_DECLARATIONS.items() if name in allowed_names
        ]

    async def dispatch(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Validate tool permission, call limit, and input arguments, then execute with timeout."""
        allowed = STAGE_ALLOWED_TOOLS.get(self._stage, frozenset())
        if tool_name not in allowed:
            raise UnauthorizedToolCallError(tool_name=tool_name, stage=self._stage.value)

        if self._call_count >= self._max_tool_calls:
            raise ToolCallLimitExceededError(
                max_calls=self._max_tool_calls,
                stage=self._stage.value,
            )

        if not isinstance(arguments, dict):
            raise ToolInputValidationError(
                tool_name=tool_name,
                reason="arguments phải là một JSON object (dict).",
            )

        if tool_name == "search_learning_concepts":
            output = await self._execute_search_learning_concepts(arguments)
        elif tool_name == "get_concept_prerequisite_graph":
            output = await self._execute_get_prerequisite_graph(arguments)
        elif tool_name == "get_learning_resources_and_guidance":
            output = await self._execute_get_learning_resources_and_guidance(arguments)
        else:
            raise UnauthorizedToolCallError(tool_name=tool_name, stage=self._stage.value)

        self._call_count += 1
        self._call_history.append(
            LLMToolCallResultDTO(
                tool_name=tool_name,
                arguments=dict(arguments),
                output=output,
            )
        )
        return output

    async def _execute_search_learning_concepts(self, arguments: dict[str, Any]) -> dict[str, Any]:
        raw_query = arguments.get("query")
        if not isinstance(raw_query, str) or not raw_query.strip():
            raise ToolInputValidationError(
                tool_name="search_learning_concepts",
                reason="Tham số 'query' bắt buộc là chuỗi không rỗng.",
            )
        query = raw_query.strip()
        if len(query) > 200:
            raise ToolInputValidationError(
                tool_name="search_learning_concepts",
                reason="Tham số 'query' không được vượt quá 200 ký tự.",
            )

        raw_domain = arguments.get("domain")
        domain: str | None = None
        if raw_domain is not None:
            if not isinstance(raw_domain, str):
                raise ToolInputValidationError(
                    tool_name="search_learning_concepts",
                    reason="Tham số 'domain' phải là chuỗi.",
                )
            domain = raw_domain.strip()[:100] or None

        raw_level = arguments.get("learner_level")
        learner_level: str | None = None
        if raw_level is not None:
            if not isinstance(raw_level, str):
                raise ToolInputValidationError(
                    tool_name="search_learning_concepts",
                    reason="Tham số 'learner_level' phải là chuỗi.",
                )
            learner_level = raw_level.strip()[:50] or None

        raw_limit = arguments.get("limit", 10)
        if isinstance(raw_limit, bool) or not isinstance(raw_limit, int):
            raise ToolInputValidationError(
                tool_name="search_learning_concepts",
                reason="Tham số 'limit' phải là số nguyên.",
            )
        limit = max(1, min(10, raw_limit))

        concepts = await asyncio.wait_for(
            self._kb.search_concepts(
                query=query,
                domain=domain,
                learner_level=learner_level,
                limit=limit,
            ),
            timeout=self._timeout_seconds,
        )
        for c in concepts:
            self._collected_concepts[c.concept_id] = c

        return {
            "query": query,
            "count": len(concepts),
            "concepts": [
                {
                    "concept_id": c.concept_id,
                    "title": c.title,
                    "summary": c.summary,
                    "domain": c.domain,
                    "difficulty_level": c.difficulty_level,
                    "estimated_effort_minutes": c.estimated_effort_minutes,
                    "keywords": list(c.keywords),
                    "learning_outcomes": list(c.learning_outcomes),
                    "verification_status": c.verification_status.value,
                    "search_score": c.search_score,
                }
                for c in concepts
            ],
        }

    async def _execute_get_prerequisite_graph(self, arguments: dict[str, Any]) -> dict[str, Any]:
        raw_ids = arguments.get("concept_ids")
        if not isinstance(raw_ids, list) or len(raw_ids) == 0:
            raise ToolInputValidationError(
                tool_name="get_concept_prerequisite_graph",
                reason="Tham số 'concept_ids' bắt buộc là danh sách không rỗng (1..15 mã khái niệm).",
            )
        if len(raw_ids) > 15:
            raise ToolInputValidationError(
                tool_name="get_concept_prerequisite_graph",
                reason="Tham số 'concept_ids' không được vượt quá 15 phần tử.",
            )

        clean_ids: list[str] = []
        for item in raw_ids:
            if not isinstance(item, str) or not item.strip():
                raise ToolInputValidationError(
                    tool_name="get_concept_prerequisite_graph",
                    reason="Mỗi phần tử trong 'concept_ids' phải là chuỗi không rỗng.",
                )
            cid = item.strip()
            if len(cid) > 120:
                raise ToolInputValidationError(
                    tool_name="get_concept_prerequisite_graph",
                    reason="Mã khái niệm trong 'concept_ids' không được vượt quá 120 ký tự.",
                )
            if cid not in clean_ids:
                clean_ids.append(cid)

        raw_depth = arguments.get("max_depth", 3)
        if isinstance(raw_depth, bool) or not isinstance(raw_depth, int):
            raise ToolInputValidationError(
                tool_name="get_concept_prerequisite_graph",
                reason="Tham số 'max_depth' phải là số nguyên.",
            )
        max_depth = max(1, min(5, raw_depth))

        graph = await asyncio.wait_for(
            self._kb.get_prerequisite_graph(
                concept_ids=clean_ids,
                max_depth=max_depth,
            ),
            timeout=self._timeout_seconds,
        )
        self._collected_graphs.append(graph)
        for node in graph.nodes:
            self._collected_concepts.setdefault(node.concept_id, node)

        return graph.to_dict()

    async def _execute_get_learning_resources_and_guidance(
        self, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        raw_query = arguments.get("query")
        query: str | None = None
        if raw_query is not None:
            if not isinstance(raw_query, str):
                raise ToolInputValidationError(
                    tool_name="get_learning_resources_and_guidance",
                    reason="Tham số 'query' nếu cung cấp phải là chuỗi.",
                )
            query = raw_query.strip()[:200] or None

        raw_domain = arguments.get("domain")
        domain: str | None = None
        if raw_domain is not None:
            if not isinstance(raw_domain, str):
                raise ToolInputValidationError(
                    tool_name="get_learning_resources_and_guidance",
                    reason="Tham số 'domain' phải là chuỗi.",
                )
            domain = raw_domain.strip()[:100] or None

        raw_task_type = arguments.get("task_type")
        task_type: str | None = None
        if raw_task_type is not None:
            if not isinstance(raw_task_type, str):
                raise ToolInputValidationError(
                    tool_name="get_learning_resources_and_guidance",
                    reason="Tham số 'task_type' phải là chuỗi.",
                )
            task_type = raw_task_type.strip().upper() or None

        clean_cids: list[str] = []
        raw_cids = arguments.get("concept_ids")
        if raw_cids is not None:
            if not isinstance(raw_cids, list):
                raise ToolInputValidationError(
                    tool_name="get_learning_resources_and_guidance",
                    reason="Tham số 'concept_ids' phải là danh sách các chuỗi mã khái niệm.",
                )
            if len(raw_cids) > 15:
                raise ToolInputValidationError(
                    tool_name="get_learning_resources_and_guidance",
                    reason="Tham số 'concept_ids' không được vượt quá 15 phần tử.",
                )
            for item in raw_cids:
                if isinstance(item, str) and item.strip():
                    cid = item.strip()[:120]
                    if cid not in clean_cids:
                        clean_cids.append(cid)

        raw_limit = arguments.get("limit", 5)
        if isinstance(raw_limit, bool) or not isinstance(raw_limit, int):
            raise ToolInputValidationError(
                tool_name="get_learning_resources_and_guidance",
                reason="Tham số 'limit' phải là số nguyên.",
            )
        limit = max(1, min(10, raw_limit))

        resources = await asyncio.wait_for(
            self._kb.get_learning_resources_and_guidance(
                query=query,
                domain=domain,
                concept_ids=clean_cids,
                task_type=task_type,
                limit=limit,
            ),
            timeout=self._timeout_seconds,
        )
        for res in resources:
            if res not in self._collected_resources:
                self._collected_resources.append(res)

        return {
            "count": len(resources),
            "resources": [r.to_dict() for r in resources],
        }
