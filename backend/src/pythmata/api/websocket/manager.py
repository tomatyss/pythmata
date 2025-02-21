"""WebSocket connection manager for process instance updates."""

from typing import Dict, Set
from uuid import UUID

from fastapi import WebSocket
from pydantic import BaseModel

from pythmata.utils.logger import get_logger

logger = get_logger(__name__)


class WebSocketMessage(BaseModel):
    """WebSocket message format."""

    type: str
    payload: dict


class ConnectionManager:
    """Manages WebSocket connections for process instances."""

    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: Dict[UUID, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, instance_id: UUID) -> None:
        """
        Connect a WebSocket client to a process instance.

        Args:
            websocket: The WebSocket connection
            instance_id: ID of the process instance to subscribe to
        """
        await websocket.accept()
        if instance_id not in self.active_connections:
            self.active_connections[instance_id] = set()
        self.active_connections[instance_id].add(websocket)
        logger.info(f"WebSocket client connected to instance {instance_id}")

    def disconnect(self, websocket: WebSocket, instance_id: UUID) -> None:
        """
        Disconnect a WebSocket client.

        Args:
            websocket: The WebSocket connection to disconnect
            instance_id: ID of the process instance
        """
        if instance_id in self.active_connections:
            self.active_connections[instance_id].discard(websocket)
            if not self.active_connections[instance_id]:
                del self.active_connections[instance_id]
        logger.info(f"WebSocket client disconnected from instance {instance_id}")

    async def broadcast_to_instance(
        self, instance_id: UUID, message_type: str, data: dict
    ) -> None:
        """
        Broadcast a message to all clients subscribed to a process instance.

        Args:
            instance_id: ID of the process instance
            message_type: Type of message (ACTIVITY_COMPLETED, VARIABLE_UPDATED, etc.)
            data: Message payload
        """
        if instance_id not in self.active_connections:
            return

        message = WebSocketMessage(type=message_type, payload=data)
        disconnected = set()

        for connection in self.active_connections[instance_id]:
            try:
                await connection.send_json(message.model_dump())
            except Exception as e:
                logger.error(f"Error sending WebSocket message: {e}")
                disconnected.add(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection, instance_id)


# Global connection manager instance
manager = ConnectionManager()
