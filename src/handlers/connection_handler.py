"""Connection handler for WebSocket concurrency limiting."""

import asyncio
import logging
from typing import Set

from fastapi import WebSocket

from ..config import MAX_CONCURRENT_CONNECTIONS
from ..config.websocket import WS_HANDSHAKE_ACQUIRE_TIMEOUT_S

logger = logging.getLogger(__name__)


class ConnectionHandler:
    """Handles WebSocket connections and enforces concurrency limits."""

    def __init__(
        self,
        max_connections: int = MAX_CONCURRENT_CONNECTIONS,
        acquire_timeout: float = WS_HANDSHAKE_ACQUIRE_TIMEOUT_S,
    ):
        self.max_connections = max_connections
        self.acquire_timeout = acquire_timeout
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(max_connections)

    async def connect(self, websocket: WebSocket) -> bool:
        """Attempt to add a new WebSocket connection.

        Args:
            websocket: WebSocket connection to add

        Returns:
            True if connection was accepted, False if at capacity
        """
        try:
            await asyncio.wait_for(self._semaphore.acquire(), timeout=self.acquire_timeout)
        except asyncio.TimeoutError:
                logger.warning(
                "Connection rejected: at capacity (%s/%s)",
                len(self.active_connections),
                self.max_connections,
                )
                return False

        try:
            async with self._lock:
            self.active_connections.add(websocket)
            logger.info(
                    "Connection accepted: %s/%s active",
                    len(self.active_connections),
                    self.max_connections,
            )
            return True
        except Exception:
            self._semaphore.release()
            raise

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection.

        Args:
            websocket: WebSocket connection to remove
        """
        should_release = False
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
                should_release = True
                logger.info(
                    "Connection removed: %s/%s active",
                    len(self.active_connections),
                    self.max_connections,
                )
        if should_release:
            self._semaphore.release()

    def get_connection_count(self) -> int:
        """Get current number of active connections.

        Returns:
            Number of active connections
        """
        return len(self.active_connections)

    def get_capacity_info(self) -> dict:
        """Get capacity information.

        Returns:
            Dict with active, max, and available connection counts
        """
        active = len(self.active_connections)
        return {
            "active": active,
            "max": self.max_connections,
            "available": self.max_connections - active,
            "at_capacity": active >= self.max_connections,
        }


# Global connection handler instance
connection_handler = ConnectionHandler()


