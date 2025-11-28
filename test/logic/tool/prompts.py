from __future__ import annotations

import importlib
from dataclasses import dataclass

TOOL_PROMPT_MODULE = "test.prompts.toolcall"
DEFAULT_TOOL_PROMPT_NAME = "base"


@dataclass(frozen=True)
class ToolPromptDefinition:
    name: str
    prompt: str


class ToolPromptRegistry:
    """Reloadable registry backed by `test/prompts/toolcall.py`."""

    def __init__(self, module_name: str = TOOL_PROMPT_MODULE) -> None:
        self._module_name = module_name
        self._module = None

    def _reload(self):
        if self._module is None:
            module = importlib.import_module(self._module_name)
        else:
            module = importlib.reload(self._module)
        self._module = module
        return module

    def _load_raw_prompts(self) -> dict[str, str]:
        module = self._reload()
        prompts = getattr(module, "TOOL_PROMPTS", None)
        if not isinstance(prompts, dict):
            raise RuntimeError(
                f"{self._module_name}.TOOL_PROMPTS must be a dict[str, str], got {type(prompts)!r}"
            )
        return prompts

    def load_all(self) -> dict[str, ToolPromptDefinition]:
        raw = self._load_raw_prompts()
        resolved: dict[str, ToolPromptDefinition] = {}
        for name, prompt in raw.items():
            if not isinstance(prompt, str):
                raise RuntimeError(
                    f"Tool prompt '{name}' must map to a string, got {type(prompt)!r}"
                )
            resolved[name.lower()] = ToolPromptDefinition(name=name, prompt=prompt)
        return resolved

    def require(self, name: str) -> ToolPromptDefinition:
        lookup = (name or "").strip().lower()
        if not lookup:
            raise ValueError("tool prompt name must be non-empty")
        resolved = self.load_all()
        try:
            return resolved[lookup]
        except KeyError as err:
            available = ", ".join(sorted(resolved))
            raise ValueError(f"unknown tool prompt '{name}'. Available: {available}") from err

    def available_names(self) -> list[str]:
        prompts = self.load_all().values()
        return sorted({prompt.name for prompt in prompts})


__all__ = [
    "DEFAULT_TOOL_PROMPT_NAME",
    "ToolPromptDefinition",
    "ToolPromptRegistry",
    "TOOL_PROMPT_MODULE",
]
