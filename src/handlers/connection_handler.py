"""Connection handler for WebSocket concurrency limiting."""

import asyncio
import logging
from typing import Set
from fastapi import WebSocket

from ..config import MAX_CONCURRENT_CONNECTIONS

logger = logging.getLogger(__name__)


class ConnectionHandler:
    """Handles WebSocket connections and enforces concurrency limits."""

    def __init__(self, max_connections: int = MAX_CONCURRENT_CONNECTIONS):
        self.max_connections = max_connections
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> bool:
        """Attempt to add a new WebSocket connection.

        Args:
            websocket: WebSocket connection to add

        Returns:
            True if connection was accepted, False if at capacity
        """
        async with self._lock:
            if len(self.active_connections) >= self.max_connections:
                logger.warning(
                    f"Connection rejected: at capacity ({len(self.active_connections)}/{self.max_connections})"
                )
                return False

            self.active_connections.add(websocket)
            logger.info(
                f"Connection accepted: {len(self.active_connections)}/{self.max_connections} active"
            )
            return True

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection.

        Args:
            websocket: WebSocket connection to remove
        """
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
                logger.info(
                    f"Connection removed: {len(self.active_connections)}/{self.max_connections} active"
                )

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


