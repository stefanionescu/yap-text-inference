"""WebSocket message receiving loop.

Each class/function in this package is defined in its own module for modularity.
"""

import asyncio
import contextlib

from server.config import settings
from server.streaming.ws.message_parser import MessageParser


async def message_receiver(
    ws,
    queue: asyncio.Queue,
    cancel_event: asyncio.Event | None = None,
    touch_activity=None,
) -> None:
    """Receive and parse WebSocket messages, putting structured results in queue.

    If a cancel message is received, set the provided cancel_event immediately
    so ongoing synthesis can stop without waiting for the queue consumer.
    """
    parser = MessageParser()

    while True:
        try:
            msg = await ws.receive_text()
            if callable(touch_activity):
                with contextlib.suppress(Exception):
                    touch_activity()
            parsed = parser.parse_message(msg)

            if parsed is None:
                continue

            # Trigger cancellation immediately for low-latency stop
            if parsed.get(settings.ws_key_type) == settings.ws_type_cancel and cancel_event is not None:
                cancel_event.set()
            await queue.put(parsed)

            if parsed.get(settings.ws_key_type) == settings.ws_type_end:
                break

        except ValueError:
            # Voice validation error - send end signal to close connection
            await queue.put({settings.ws_key_type: settings.ws_type_end, "error": "invalid_voice"})
            break
        except Exception:
            await queue.put({settings.ws_key_type: settings.ws_type_end})
            break
