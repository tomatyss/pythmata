"""WebSocket connection manager for chat functionality."""

from datetime import datetime
from typing import Dict, Set, Optional, Any
from uuid import UUID

from fastapi import WebSocket
from pydantic import BaseModel

from pythmata.utils.logger import get_logger

logger = get_logger(__name__)


class ChatWebSocketMessage(BaseModel):
    """
    WebSocket message format for chat.
    
    Attributes:
        type: Message type (token, message_received, etc.)
        content: Message content as a dictionary
    """
    type: str
    content: Dict[str, Any]


class ChatConnectionManager:
    """
    Manages WebSocket connections for chat sessions.
    
    This manager handles client connections, session associations,
    and message routing for the chat functionality.
    
    Attributes:
        active_connections: Dictionary mapping client IDs to WebSocket connections
        session_clients: Dictionary mapping session IDs to sets of client IDs
        client_sessions: Dictionary mapping client IDs to session IDs
    """

    def __init__(self):
        """Initialize chat connection manager."""
        self.active_connections: Dict[str, WebSocket] = {}  # client_id -> WebSocket
        self.session_clients: Dict[UUID, Set[str]] = {}  # session_id -> Set[client_id]
        self.client_sessions: Dict[str, UUID] = {}  # client_id -> session_id

    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """
        Connect a WebSocket client.
        
        Args:
            websocket: The WebSocket connection
            client_id: Unique identifier for the client
        """
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Chat WebSocket client {client_id} connected")

    def disconnect(self, client_id: str) -> None:
        """
        Disconnect a WebSocket client.
        
        Args:
            client_id: Unique identifier for the client
        """
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            
        # Remove from session if associated
        if client_id in self.client_sessions:
            session_id = self.client_sessions[client_id]
            if session_id in self.session_clients:
                self.session_clients[session_id].discard(client_id)
                if not self.session_clients[session_id]:
                    del self.session_clients[session_id]
            del self.client_sessions[client_id]
            
        logger.info(f"Chat WebSocket client {client_id} disconnected")

    async def join_session(self, client_id: str, session_id: UUID) -> None:
        """
        Associate a client with a chat session.
        
        Args:
            client_id: Unique identifier for the client
            session_id: UUID of the chat session
        """
        if session_id not in self.session_clients:
            self.session_clients[session_id] = set()
        self.session_clients[session_id].add(client_id)
        self.client_sessions[client_id] = session_id
        logger.info(f"Client {client_id} joined session {session_id}")
        
        # Notify other clients in the session that a new client has joined
        await self.broadcast_to_session(
            session_id,
            "client_joined",
            {
                "clientId": client_id,
                "timestamp": datetime.now().isoformat()
            },
            exclude_client=client_id
        )

    async def leave_session(self, client_id: str) -> None:
        """
        Remove a client from its current session.
        
        Args:
            client_id: Unique identifier for the client
        """
        if client_id in self.client_sessions:
            session_id = self.client_sessions[client_id]
            if session_id in self.session_clients:
                self.session_clients[session_id].discard(client_id)
                
                # Notify other clients that this client has left
                await self.broadcast_to_session(
                    session_id,
                    "client_left",
                    {
                        "clientId": client_id,
                        "timestamp": datetime.now().isoformat()
                    },
                    exclude_client=client_id
                )
                
                if not self.session_clients[session_id]:
                    del self.session_clients[session_id]
            del self.client_sessions[client_id]
            logger.info(f"Client {client_id} left session {session_id}")

    async def send_personal_message(self, client_id: str, message_type: str, content: Dict[str, Any]) -> None:
        """
        Send a message to a specific client.
        
        Args:
            client_id: Unique identifier for the client
            message_type: Type of message (token, message_received, etc.)
            content: Message payload
        """
        if client_id not in self.active_connections:
            logger.warning(f"Attempted to send message to inactive client {client_id}")
            return

        message = ChatWebSocketMessage(type=message_type, content=content)
        try:
            await self.active_connections[client_id].send_json(message.model_dump())
        except Exception as e:
            logger.error(f"Error sending message to client {client_id}: {e}")
            # Handle disconnection
            self.disconnect(client_id)

    async def broadcast_to_session(
        self, 
        session_id: UUID, 
        message_type: str, 
        content: Dict[str, Any],
        exclude_client: Optional[str] = None
    ) -> None:
        """
        Broadcast a message to all clients in a session.
        
        Args:
            session_id: UUID of the chat session
            message_type: Type of message (chat_message, typing_indicator, etc.)
            content: Message payload
            exclude_client: Optional client ID to exclude from broadcast
        """
        if session_id not in self.session_clients:
            logger.warning(f"Attempted to broadcast to inactive session {session_id}")
            return

        message = ChatWebSocketMessage(type=message_type, content=content)
        disconnected = set()

        for client_id in self.session_clients[session_id]:
            if exclude_client and client_id == exclude_client:
                continue
                
            if client_id in self.active_connections:
                try:
                    await self.active_connections[client_id].send_json(message.model_dump())
                except Exception as e:
                    logger.error(f"Error broadcasting to client {client_id}: {e}")
                    disconnected.add(client_id)
            else:
                disconnected.add(client_id)

        # Clean up disconnected clients
        for client_id in disconnected:
            self.disconnect(client_id)


# Global chat connection manager instance
chat_manager = ChatConnectionManager()
