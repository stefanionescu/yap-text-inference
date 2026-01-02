from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tests.config import DEFAULT_PERSONALITIES

from .personas import PersonaDefinition


@dataclass
class LiveSession:
    """Live test session state.
    
    Note: chat_prompt is always required - the server requires a system prompt
    when DEPLOY_CHAT is enabled.
    """
    
    session_id: str
    persona: PersonaDefinition
    history: list[dict[str, str]] = field(default_factory=list)
    sampling: dict[str, float | int] | None = None

    def build_start_payload(self, user_text: str) -> dict[str, Any]:
        """Build the start message payload for a conversation turn."""
        if not self.persona.prompt:
            raise ValueError(
                "chat_prompt is required. "
                "Use select_chat_prompt(gender) to get a valid prompt."
            )
        
        payload: dict[str, Any] = {
            "type": "start",
            "session_id": self.session_id,
            "gender": self.persona.gender,
            "personality": self.persona.personality,
            "personalities": DEFAULT_PERSONALITIES,
            "chat_prompt": self.persona.prompt,
            "history": self.history,
            "user_utterance": user_text,
        }
        if self.sampling:
            payload["sampling"] = self.sampling
        return payload

    def build_persona_payload(self, persona: PersonaDefinition) -> dict[str, Any]:
        """Build a chat_prompt update payload for mid-session persona changes."""
        return {
            "type": "chat_prompt",
            "session_id": self.session_id,
            "gender": persona.gender,
            "personality": persona.personality,
            "chat_prompt": persona.prompt,
        }

    def append_exchange(self, user_text: str, assistant_text: str) -> None:
        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": assistant_text})

    def replace_persona(self, persona: PersonaDefinition) -> None:
        self.persona = persona


__all__ = ["LiveSession"]


