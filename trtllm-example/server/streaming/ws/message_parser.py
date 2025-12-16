"""WebSocket message parsing utilities.

Each class in this package is defined in its own module for modularity.
"""

import json

from server.config import settings
from server.voices import resolve_voice


class MessageParser:
    """Handles parsing and routing of WebSocket messages."""

    @staticmethod
    def parse_message(msg: str) -> dict | None:  # noqa: PLR0911
        """Parse incoming WebSocket message into structured format."""
        msg = msg.strip()

        # Sentinel checks for plain messages
        if MessageParser._is_end_sentinel(msg):
            return {settings.ws_key_type: settings.ws_type_end}
        if MessageParser._is_cancel_sentinel(msg):
            return {settings.ws_key_type: settings.ws_type_cancel}

        # Try JSON parse, else treat as plain text
        obj = MessageParser._try_parse_json(msg)
        if obj is None:
            if msg:
                return {settings.ws_key_type: settings.ws_type_text, settings.ws_key_text: msg}
            return None

        if not isinstance(obj, dict):
            return None

        # End/Cancel flags in JSON
        if MessageParser._is_end_json(obj):
            return {settings.ws_key_type: settings.ws_type_end}
        if MessageParser._is_cancel_json(obj):
            cancel_msg = {settings.ws_key_type: settings.ws_type_cancel}
            req_id = obj.get(settings.ws_key_request_id)
            if req_id:
                cancel_msg[settings.ws_key_request_id] = str(req_id)
            return cancel_msg

        # Ping/Pong heartbeat messages
        try:
            typ = str(obj.get(settings.ws_key_type, "")).lower()
        except Exception:
            typ = ""
        if typ == settings.ws_type_ping:
            return {settings.ws_key_type: settings.ws_type_ping}
        if typ == settings.ws_type_pong:
            return {settings.ws_key_type: settings.ws_type_pong}

        # Metadata-only
        meta_msg = MessageParser._parse_meta_dict(obj)
        if meta_msg is not None:
            return meta_msg

        # Text message with optional overrides
        text_msg = MessageParser._build_text_message(obj)
        if text_msg is not None:
            return text_msg

        return None

    @staticmethod
    def _is_end_sentinel(msg: str) -> bool:
        return msg == settings.ws_end_sentinel

    @staticmethod
    def _is_cancel_sentinel(msg: str) -> bool:
        return msg == settings.ws_cancel_sentinel

    @staticmethod
    def _try_parse_json(msg: str):
        try:
            return json.loads(msg)
        except Exception:
            return None

    @staticmethod
    def _is_end_json(obj: dict) -> bool:
        return (
            obj.get(settings.ws_key_end) is True
            or str(obj.get(settings.ws_key_type, "")).lower() == settings.ws_type_end
        )

    @staticmethod
    def _is_cancel_json(obj: dict) -> bool:
        return (
            obj.get(settings.ws_key_cancel) is True
            or str(obj.get(settings.ws_key_type, "")).lower() == settings.ws_type_cancel
        )

    @staticmethod
    def _parse_meta_dict(obj: dict) -> dict | None:
        if (settings.ws_key_text not in obj) and (any(k in obj for k in settings.ws_meta_keys)):
            return {settings.ws_key_type: settings.ws_type_meta, "meta": obj}
        return None

    @staticmethod
    def _validate_voice_if_present(voice) -> None:
        if voice is None:
            return
        try:
            resolve_voice(str(voice))
        except ValueError as e:
            raise ValueError(f"Voice validation failed: {e}") from e

    @staticmethod
    def _validate_generation_params(temperature, top_p, repetition_penalty) -> None:
        if temperature is not None:
            try:
                temp_val = float(temperature)
                if not (settings.temperature_min <= temp_val <= settings.temperature_max):
                    raise ValueError(
                        "Temperature must be between "
                        f"{settings.temperature_min} and {settings.temperature_max}, got {temp_val}"
                    )
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid temperature parameter: {e}") from e

        if top_p is not None:
            try:
                top_p_val = float(top_p)
                if not (settings.top_p_min <= top_p_val <= settings.top_p_max):
                    raise ValueError(
                        f"top_p must be between {settings.top_p_min} and {settings.top_p_max}, got {top_p_val}"
                    )
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid top_p parameter: {e}") from e

        if repetition_penalty is not None:
            try:
                rep_val = float(repetition_penalty)
                if not (settings.repetition_penalty_min <= rep_val <= settings.repetition_penalty_max):
                    raise ValueError(
                        "repetition_penalty must be between "
                        f"{settings.repetition_penalty_min} and {settings.repetition_penalty_max}, "
                        f"got {rep_val}"
                    )
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid repetition_penalty parameter: {e}") from e

    @staticmethod
    def _build_text_message(obj: dict) -> dict | None:
        text = (obj.get(settings.ws_key_text) or "").strip()
        if not text:
            return None
        voice = obj.get(settings.ws_key_voice)
        trim_silence = obj.get(settings.ws_key_trim_silence)
        temperature = obj.get(settings.ws_key_temperature)
        top_p = obj.get(settings.ws_key_top_p)
        repetition_penalty = obj.get(settings.ws_key_repetition_penalty)

        # Validate optional fields
        MessageParser._validate_voice_if_present(voice)
        MessageParser._validate_generation_params(temperature, top_p, repetition_penalty)

        out = {
            settings.ws_key_type: settings.ws_type_text,
            settings.ws_key_text: text,
        }
        if voice is not None:
            out[settings.ws_key_voice] = voice
        if trim_silence is not None:
            out[settings.ws_key_trim_silence] = trim_silence
        if temperature is not None:
            out[settings.ws_key_temperature] = temperature
        if top_p is not None:
            out[settings.ws_key_top_p] = top_p
        if repetition_penalty is not None:
            out[settings.ws_key_repetition_penalty] = repetition_penalty
        request_id = obj.get(settings.ws_key_request_id)
        if request_id:
            out[settings.ws_key_request_id] = str(request_id)
        return out
