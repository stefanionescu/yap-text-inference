"""Live client dataclasses."""

from __future__ import annotations

from dataclasses import field, dataclass

from tests.helpers.errors import ServerError, RateLimitError
from tests.helpers.websocket import (
    build_start_payload as build_ws_start_payload,
    build_message_payload as build_ws_message_payload,
)

from .metrics import SessionContext


@dataclass(frozen=True)
class PersonaDefinition:
    """Immutable representation of a persona configuration."""

    name: str
    gender: str
    personality: str
    prompt: str


@dataclass
class LiveSession:
    """Live test session state."""

    session_id: str
    persona: PersonaDefinition
    history: list[dict[str, str]] = field(default_factory=list)
    sampling: dict[str, float | int] | None = None
    _started: bool = False

    def build_start_payload(self, user_text: str) -> dict[str, object]:
        """Build the start message payload for a conversation turn."""
        ctx = SessionContext(
            session_id=self.session_id,
            gender=self.persona.gender,
            personality=self.persona.personality,
            chat_prompt=self.persona.prompt,
            sampling=self.sampling,
        )
        payload = build_ws_start_payload(ctx, user_text, history=self.history)
        self._started = True
        return payload

    def build_message_payload(self, user_text: str) -> dict[str, object]:
        """Build the message payload for subsequent conversation turns."""
        return build_ws_message_payload(
            self.session_id,
            user_text,
            sampling=self.sampling,
        )

    def append_exchange(self, user_text: str, assistant_text: str) -> None:
        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": assistant_text})


@dataclass
class StreamResult:
    """Result of a streaming message exchange."""

    text: str
    ok: bool = True
    error: ServerError | None = None
    cancelled: bool = False

    @property
    def is_rate_limited(self) -> bool:
        return isinstance(self.error, RateLimitError)

    @property
    def is_recoverable(self) -> bool:
        if self.error is None:
            return True
        return self.error.is_recoverable()

    def format_error(self) -> str:
        if self.error is None:
            return ""
        return self.error.format_for_user()


__all__ = [
    "LiveSession",
    "PersonaDefinition",
    "StreamResult",
]
