"""Connection handler for WebSocket concurrency limiting.

This module manages the pool of active WebSocket connections and enforces
the MAX_CONCURRENT_CONNECTIONS limit. It provides:

- Connection admission control (semaphore-based)
- Active connection tracking
- Capacity metrics for health checks
- Thread-safe connection add/remove operations

The connection handler uses a two-stage approach:
1. Semaphore acquisition (with timeout) to reserve a slot
2. Lock-protected set addition to track the connection

This prevents both over-admission (too many connections) and race
conditions during connection/disconnection.

Example:
    handler = ConnectionHandler(max_connections=100)
    
    async def handle_websocket(ws: WebSocket):
        if not await handler.connect(ws):
            await ws.close(code=1013)  # Try again later
            return
        try:
            # Handle messages...
        finally:
            await handler.disconnect(ws)
"""

import asyncio
import logging

from fastapi import WebSocket

from ..config import MAX_CONCURRENT_CONNECTIONS
from ..config.websocket import WS_HANDSHAKE_ACQUIRE_TIMEOUT_S

logger = logging.getLogger(__name__)


class ConnectionHandler:
    """Handles WebSocket connections and enforces concurrency limits.
    
    This class manages the lifecycle of WebSocket connections with:
    - Maximum connection limit enforcement
    - Timeout-based connection admission
    - Atomic connect/disconnect operations
    
    Attributes:
        max_connections: Maximum allowed concurrent connections.
        acquire_timeout: Max seconds to wait for a connection slot.
        active_connections: Set of currently connected WebSocket instances.
    """

    def __init__(
        self,
        max_connections: int | None = None,
        acquire_timeout: float = WS_HANDSHAKE_ACQUIRE_TIMEOUT_S,
    ):
        """Initialize the connection handler.
        
        Args:
            max_connections: Maximum concurrent connections to allow.
                Defaults to MAX_CONCURRENT_CONNECTIONS from config.
            acquire_timeout: Seconds to wait when server is at capacity.
        """
        if max_connections is None:
            if MAX_CONCURRENT_CONNECTIONS is None:
                raise RuntimeError("MAX_CONCURRENT_CONNECTIONS not configured")
            max_connections = MAX_CONCURRENT_CONNECTIONS
        self.max_connections = max_connections
        self.acquire_timeout = acquire_timeout
        self.active_connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()  # Protects active_connections set
        self._semaphore = asyncio.Semaphore(max_connections)  # Limits concurrency

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
