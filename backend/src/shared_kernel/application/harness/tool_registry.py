from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from typing import Any

from src.shared_kernel.application.llm_port import LLMToolDeclarationDTO

from .models import ToolResultEnvelope

ToolHandler = Callable[[dict[str, Any]], Awaitable[ToolResultEnvelope]]


@dataclass(frozen=True, slots=True)
class RegisteredTool:
    declaration: LLMToolDeclarationDTO
    allowed_stages: frozenset[str]
    handler: ToolHandler


class ToolRegistry:
    """Contract-bound registry with explicit workflow-stage permissions."""

    def __init__(self, tools: Iterable[RegisteredTool] = ()) -> None:
        self._tools: dict[str, RegisteredTool] = {}
        for tool in tools:
            self.register(tool)

    def register(self, tool: RegisteredTool) -> None:
        name = tool.declaration.name
        if name in self._tools:
            raise ValueError(f"Tool already registered: {name}")
        if not tool.allowed_stages:
            raise ValueError(f"Tool must declare at least one allowed stage: {name}")
        self._tools[name] = tool

    def declarations_for(self, stage: str) -> list[LLMToolDeclarationDTO]:
        return [tool.declaration for tool in self._tools.values() if stage in tool.allowed_stages]

    async def dispatch(
        self,
        *,
        stage: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        tool = self._tools.get(tool_name)
        if tool is None or stage not in tool.allowed_stages:
            raise PermissionError(f"Tool {tool_name!r} is not allowed in stage {stage!r}")
        if not isinstance(arguments, dict):
            raise TypeError("Tool arguments must be a JSON object")
        result = await tool.handler(arguments)
        if result.status not in {"success", "warning", "error"}:
            raise ValueError(f"Invalid tool result status: {result.status}")
        return result.as_dict()
