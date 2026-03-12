"""Client payload parsing and schema validation for the WebSocket handler.

All client messages must be flat JSON objects with:
    {"type": "...", "v": <protocol_version>, ...fields}

Validation is strict:
- Unknown fields are rejected
- Message schemas are type-specific
- History payload limits are enforced
- Protocol version must match server configuration
"""

from __future__ import annotations

import json
from typing import Any, Literal, Annotated
from pydantic import Field, BaseModel, ConfigDict, TypeAdapter, ValidationError, field_validator, model_validator
from ...config.websocket import (
    WS_PROTOCOL_VERSION,
    WS_HISTORY_MAX_ITEMS,
    WS_MAX_MESSAGE_BYTES,
    WS_HISTORY_ITEM_MAX_CHARS,
    WS_HISTORY_TOTAL_MAX_CHARS,
)


class _VersionedMessage(BaseModel):
    """Base client message that enforces protocol version and strict fields."""

    model_config = ConfigDict(extra="forbid")
    v: int

    @field_validator("v")
    @classmethod
    def _validate_protocol_version(cls, value: int) -> int:
        if value != WS_PROTOCOL_VERSION:
            raise ValueError(f"unsupported protocol version: {value} (expected {WS_PROTOCOL_VERSION})")
        return value


class _HistoryItem(BaseModel):
    """One history message item in start payloads."""

    model_config = ConfigDict(extra="forbid")
    role: str
    content: str

    @field_validator("role", mode="before")
    @classmethod
    def _normalize_role(cls, value: Any) -> str:
        normalized = str(value).strip().lower()
        return normalized

    @field_validator("role")
    @classmethod
    def _validate_role(cls, value: str) -> str:
        if value not in {"user", "assistant"}:
            raise ValueError("history role must be 'user' or 'assistant'")
        return value

    @field_validator("content")
    @classmethod
    def _validate_content_len(cls, value: str) -> str:
        if len(value) > WS_HISTORY_ITEM_MAX_CHARS:
            raise ValueError(f"history item exceeds max chars ({WS_HISTORY_ITEM_MAX_CHARS})")
        return value


class _StartMessage(_VersionedMessage):
    """Strict schema for start messages."""

    type: Literal["start"]
    gender: str | None = None
    personality: str | None = None
    history: list[_HistoryItem] = Field(default_factory=list)
    chat_prompt: str | None = None
    sampling: dict[str, Any] | None = None
    sampling_params: dict[str, Any] | None = None
    temperature: Any | None = None
    top_p: Any | None = None
    top_k: Any | None = None
    min_p: Any | None = None
    repetition_penalty: Any | None = None
    presence_penalty: Any | None = None
    frequency_penalty: Any | None = None
    sanitize_output: Any | None = None
    check_screen_prefix: str | None = None
    screen_checked_prefix: str | None = None

    @model_validator(mode="after")
    def _validate_history_budget(self) -> _StartMessage:
        if len(self.history) > WS_HISTORY_MAX_ITEMS:
            raise ValueError(f"history exceeds max item count ({WS_HISTORY_MAX_ITEMS})")
        total_chars = sum(len(item.content) for item in self.history)
        if total_chars > WS_HISTORY_TOTAL_MAX_CHARS:
            raise ValueError(f"history exceeds total char limit ({WS_HISTORY_TOTAL_MAX_CHARS})")
        return self


class _MessageMessage(_VersionedMessage):
    """Strict schema for message turn payloads."""

    type: Literal["message"]
    user_utterance: str | None = None
    sampling: dict[str, Any] | None = None
    sampling_params: dict[str, Any] | None = None
    temperature: Any | None = None
    top_p: Any | None = None
    top_k: Any | None = None
    min_p: Any | None = None
    repetition_penalty: Any | None = None
    presence_penalty: Any | None = None
    frequency_penalty: Any | None = None
    sanitize_output: Any | None = None


class _CancelMessage(_VersionedMessage):
    """Strict schema for cancel payloads."""

    type: Literal["cancel"]


class _PingMessage(_VersionedMessage):
    """Strict schema for ping payloads."""

    type: Literal["ping"]


class _PongMessage(_VersionedMessage):
    """Strict schema for pong payloads."""

    type: Literal["pong"]


class _EndMessage(_VersionedMessage):
    """Strict schema for end payloads."""

    type: Literal["end"]


_ClientMessage = Annotated[
    _StartMessage | _MessageMessage | _CancelMessage | _PingMessage | _PongMessage | _EndMessage,
    Field(discriminator="type"),
]
_CLIENT_MESSAGE_ADAPTER = TypeAdapter(_ClientMessage)


def _format_validation_error(exc: ValidationError) -> str:
    """Convert a Pydantic validation error into a concise parser error."""
    errors = exc.errors()
    if not errors:
        return "Message payload failed validation."
    first = errors[0]
    location = ".".join(str(part) for part in first.get("loc", [])) or "payload"
    message = first.get("msg", "invalid value")
    return f"Invalid payload field '{location}': {message}"


def parse_client_message(raw: str) -> dict[str, Any]:
    """Parse and normalize a client WebSocket message.

    Args:
        raw: Raw message string from WebSocket.

    Returns:
        Normalized message dict with 'type' lowercased.

    Raises:
        ValueError: If message is empty, invalid JSON, or missing type.
    """
    raw_text = raw or ""
    raw_size = len(raw_text.encode("utf-8"))
    if raw_size > WS_MAX_MESSAGE_BYTES:
        raise ValueError(f"Message exceeds max size ({WS_MAX_MESSAGE_BYTES} bytes).")

    text = raw_text.strip()
    if not text:
        raise ValueError("Empty message.")

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Message must be valid JSON.") from exc

    if not isinstance(data, dict):
        raise ValueError("Message must be a JSON object.")

    msg_type = data.get("type")
    if not msg_type:
        raise ValueError("Missing 'type' in message.")

    data["type"] = str(msg_type).strip().lower()
    try:
        validated = _CLIENT_MESSAGE_ADAPTER.validate_python(data)
    except ValidationError as exc:
        raise ValueError(_format_validation_error(exc)) from exc
    return validated.model_dump(exclude_none=True)
