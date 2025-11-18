"""Synthesis loop for WebSocket connections."""

import asyncio
import contextlib
import logging
import uuid

from fastapi import WebSocket

from server.config import settings
from server.streaming.pipeline.streaming_pipeline import StreamingPipeline
from server.streaming.ws.connection_state import ConnectionState, InvalidMetaError
from server.streaming.ws.utils import (
    apply_sampling_overrides,
    parse_prespeech_pad_override,
    parse_trim_silence_override,
    purge_text_messages,
    safe_ws_close,
)
from server.streaming.ws.voice import VoiceValidationError, VoiceValidator

logger = logging.getLogger(__name__)
VOICE_VALIDATOR = VoiceValidator()


async def synthesis_handler(  # noqa: PLR0915
    ws: WebSocket,
    message_queue: asyncio.Queue,
    cancel_event: asyncio.Event,
    connection_state: ConnectionState,
    streaming_pipeline: StreamingPipeline,
    touch_activity=None,
) -> None:
    """Main synthesis loop: handles meta/cancel/end/text messages."""
    generating = False

    async def handle_session_end(_: dict | None) -> bool:
        cancel_event.set()
        await purge_text_messages(message_queue)
        with contextlib.suppress(Exception):
            await ws.send_json({settings.ws_key_type: settings.ws_type_audio_end})
        await safe_ws_close(ws)
        return False

    async def handle_ping(_: dict) -> bool:
        with contextlib.suppress(Exception):
            await ws.send_json({settings.ws_key_type: settings.ws_type_pong})
        return True

    async def handle_meta(message: dict) -> bool:
        try:
            connection_state.update_from_meta(message.get("meta", {}))
            return True
        except InvalidMetaError:
            await safe_ws_close(ws, settings.ws_close_unauthorized_code)
            return False

    async def handle_cancel(_: dict) -> bool:
        if not generating and cancel_event.is_set():
            cancel_event.clear()
        return True

    async def handle_text(message: dict) -> bool:
        nonlocal generating
        text = message.get(settings.ws_key_text, "").strip()

        if not text:
            await safe_ws_close(ws)
            return False

        try:
            VOICE_VALIDATOR.ensure_voice(message, connection_state)
        except VoiceValidationError:
            await safe_ws_close(ws, settings.ws_close_unauthorized_code)
            return False

        try:
            base_sampling = connection_state.get_sampling_kwargs()
        except InvalidMetaError:
            await safe_ws_close(ws, settings.ws_close_unauthorized_code)
            return False

        sampling_kwargs = apply_sampling_overrides(base_sampling, message)
        trim_flag = parse_trim_silence_override(message, connection_state.trim_silence)
        default_prepad = (
            float(connection_state.prespeech_pad_ms)
            if connection_state.prespeech_pad_ms is not None
            else float(settings.silence_prespeech_pad_ms)
        )
        prepad_ms = parse_prespeech_pad_override(message, default_prepad)
        request_id = str(uuid.uuid4())

        generating = True
        try:
            await streaming_pipeline.stream_text(
                text,
                connection_state.voice,
                sampling_kwargs,
                ws,
                trim_silence=trim_flag,
                prepad_ms=prepad_ms,
                request_id=request_id,
                cancel_event=cancel_event,
            )
        finally:
            generating = False
            if cancel_event.is_set():
                cancel_event.clear()

        return True

    handlers = {
        settings.ws_type_ping: handle_ping,
        settings.ws_type_meta: handle_meta,
        settings.ws_type_cancel: handle_cancel,
        settings.ws_type_text: handle_text,
    }

    try:
        while True:
            message = await message_queue.get()
            if callable(touch_activity):
                with contextlib.suppress(Exception):
                    touch_activity()

            msg_type = None if message is None else message.get(settings.ws_key_type)

            if message is None or msg_type == settings.ws_type_end:
                if not await handle_session_end(message):
                    break
                continue

            handler = handlers.get(msg_type)
            if handler is None:
                continue

            should_continue = await handler(message)
            if not should_continue:
                break
    except Exception:
        await safe_ws_close(ws, settings.ws_close_internal_code)
        raise
