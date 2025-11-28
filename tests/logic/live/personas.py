from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any

from tests.common.prompt import normalize_gender

PERSONA_MODULE = "tests.prompts.live"
DEFAULT_PERSONA_NAME = "anna_flirty"


@dataclass(frozen=True)
class PersonaDefinition:
    name: str
    gender: str
    personality: str
    prompt: str


class PersonaRegistry:
    """Reloadable registry backed by `tests/prompts/live.py`."""

    def __init__(self, module_name: str = PERSONA_MODULE) -> None:
        self._module_name = module_name
        self._module = None

    def _reload(self):
        if self._module is None:
            module = importlib.import_module(self._module_name)
        else:
            module = importlib.reload(self._module)
        self._module = module
        return module

    def _load_raw_personalities(self) -> dict[str, Any]:
        module = self._reload()
        personalities = getattr(module, "PERSONALITIES", None)
        if not isinstance(personalities, dict):
            raise RuntimeError(f"{self._module_name}.PERSONALITIES must be a dict, got {type(personalities)!r}")
        return personalities

    def load_all(self) -> dict[str, PersonaDefinition]:
        raw = self._load_raw_personalities()
        resolved: dict[str, PersonaDefinition] = {}
        for name, payload in raw.items():
            if not isinstance(payload, dict):
                raise RuntimeError(f"Persona '{name}' must map to a dict, got {type(payload)!r}")
            try:
                raw_gender = str(payload["gender"]).strip()
                raw_personality = str(payload["personality"]).strip()
                prompt = str(payload["prompt"])
            except KeyError as err:
                raise RuntimeError(f"Persona '{name}' missing required field: {err.args[0]}") from err
            gender = normalize_gender(raw_gender) or raw_gender
            resolved[name.lower()] = PersonaDefinition(
                name=name,
                gender=gender,
                personality=raw_personality or str(payload["personality"]),
                prompt=str(prompt),
            )
        return resolved

    def require(self, name: str) -> PersonaDefinition:
        lookup = name.strip().lower()
        if not lookup:
            raise ValueError("persona name must be non-empty")
        resolved = self.load_all()
        try:
            return resolved[lookup]
        except KeyError as err:
            available = ", ".join(sorted(resolved))
            raise ValueError(f"unknown persona '{name}'. Available: {available}") from err

    def available_names(self) -> list[str]:
        personas = self.load_all().values()
        return sorted({persona.name for persona in personas})


__all__ = ["DEFAULT_PERSONA_NAME", "PersonaDefinition", "PersonaRegistry", "PERSONA_MODULE"]


