import hashlib
import json
import re
from collections.abc import Iterable

from .models import PromptTemplate

_SEMVER_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


class PromptRegistry:
    """Immutable, code-backed registry for versioned FocusFlow prompt contracts."""

    def __init__(self, templates: Iterable[PromptTemplate] = ()) -> None:
        self._templates: dict[tuple[str, str], PromptTemplate] = {}
        for template in templates:
            self.register(template)

    @staticmethod
    def checksum_for(
        *,
        prompt_id: str,
        version: str,
        workflow_type: str,
        skill_id: str,
        system_template: str,
        output_schema: dict[str, object],
    ) -> str:
        canonical = json.dumps(
            {
                "prompt_id": prompt_id,
                "version": version,
                "workflow_type": workflow_type,
                "skill_id": skill_id,
                "system_template": system_template,
                "output_schema": output_schema,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode()).hexdigest()

    def register(self, template: PromptTemplate) -> None:
        if not _SEMVER_PATTERN.fullmatch(template.version):
            raise ValueError(f"Invalid semantic version: {template.version}")
        expected = self.checksum_for(
            prompt_id=template.prompt_id,
            version=template.version,
            workflow_type=template.workflow_type,
            skill_id=template.skill_id,
            system_template=template.system_template,
            output_schema=template.output_schema,
        )
        if template.checksum != expected:
            raise ValueError(f"Checksum mismatch for {template.prompt_id}@{template.version}")
        key = (template.prompt_id, template.version)
        if key in self._templates:
            raise ValueError(f"Prompt already registered: {template.prompt_id}@{template.version}")
        self._templates[key] = template

    def get(self, prompt_id: str, version: str) -> PromptTemplate:
        try:
            return self._templates[(prompt_id, version)]
        except KeyError as exc:
            raise KeyError(f"Unknown prompt: {prompt_id}@{version}") from exc

    def latest(self, prompt_id: str) -> PromptTemplate:
        matches = [item for (item_id, _), item in self._templates.items() if item_id == prompt_id]
        if not matches:
            raise KeyError(f"Unknown prompt: {prompt_id}")
        return max(matches, key=lambda item: tuple(int(part) for part in item.version.split(".")))
