import asyncio
import logging
import time

from fastapi import WebSocket

from server.config import settings
from server.streaming.ws.utils import safe_ws_close

logger = logging.getLogger(__name__)


class SessionLifecycle:
    """Per-connection lifecycle tracking with TTL and idle enforcement."""

    def __init__(self, ws: WebSocket):
        self.ws = ws
        now = time.monotonic()
        self.start_ts: float = now
        self.last_activity_ts: float = now

    def touch(self) -> None:
        self.last_activity_ts = time.monotonic()

    async def watchdog(self) -> None:
        try:
            while True:
                await asyncio.sleep(float(settings.ws_watchdog_tick_s))
                now = time.monotonic()
                # TTL enforcement
                if (now - self.start_ts) >= float(settings.ws_session_ttl_s):
                    logger.info("WS close: TTL exceeded")
                    await safe_ws_close(self.ws)
                    break
                # Idle timeout enforcement
                if (now - self.last_activity_ts) >= float(settings.ws_idle_timeout_s):
                    logger.info("WS close: idle timeout")
                    await safe_ws_close(self.ws)
                    break
        except Exception as exc:  # pragma: no cover - watchdog best-effort
            logger.debug("Watchdog stopping: %s", exc)
