"""WebSocket routes for real-time chat functionality."""

import uuid
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from pythmata.api.dependencies import get_session
from pythmata.core.llm.prompts import BPMN_SYSTEM_PROMPT
from pythmata.core.llm.service import LlmService
from pythmata.core.websockets.chat_manager import chat_manager
from pythmata.models.chat import ChatMessage, ChatSession
from pythmata.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/ws", tags=["websockets"])


@router.websocket("/chat/{client_id}")
async def chat_websocket(
    websocket: WebSocket, client_id: str, db: AsyncSession = Depends(get_session)
):
    """
    WebSocket endpoint for chat functionality.

    Handles real-time communication for the chat interface, including
    message streaming, typing indicators, and session management.

    Args:
        websocket: The WebSocket connection
        client_id: Unique identifier for the client
        db: Database session
    """
    await chat_manager.connect(websocket, client_id)

    try:
        while True:
            # Receive and process messages
            data = await websocket.receive_json()
            await process_chat_message(client_id, data, db)
    except WebSocketDisconnect:
        chat_manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        chat_manager.disconnect(client_id)


async def process_chat_message(client_id: str, data: Dict[str, Any], db: AsyncSession):
    """
    Process incoming WebSocket messages.

    Routes messages to appropriate handlers based on message type.

    Args:
        client_id: Unique identifier for the client
        data: Message data
        db: Database session
    """
    message_type = data.get("type")
    content = data.get("content", {})

    if message_type == "chat_message":
        await handle_chat_message(client_id, content, db)
    elif message_type == "join_session":
        await handle_join_session(client_id, content)
    elif message_type == "leave_session":
        await handle_leave_session(client_id)
    elif message_type == "typing_indicator":
        await handle_typing_indicator(client_id, content)
    else:
        logger.warning(f"Unknown message type: {message_type}")


async def handle_chat_message(client_id: str, data: Dict[str, Any], db: AsyncSession):
    """
    Handle chat message from client.

    Processes the message, sends it to the LLM, and streams the response.

    Args:
        client_id: Unique identifier for the client
        data: Message data
        db: Database session
    """
    content = data.get("content")
    session_id = data.get("sessionId")
    process_id = data.get("processId")
    current_xml = data.get("currentXml", "")
    model = data.get("model", "anthropic:claude-3-7-sonnet-latest")

    if not content:
        return

    # Create LLM service
    llm_service = LlmService()

    # Get or create session
    if not session_id:
        if process_id:
            # Create new session with process ID
            session = ChatSession(
                id=uuid.uuid4(),
                process_definition_id=process_id,
                title=f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            )
        else:
            # Create new session without process ID
            session = ChatSession(
                id=uuid.uuid4(),
                title=f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            )

        db.add(session)
        await db.commit()
        await db.refresh(session)
        session_id = session.id

        # Associate client with session
        await chat_manager.join_session(client_id, session_id)
        logger.info(f"Created new chat session {session_id} for client {client_id}")
    elif isinstance(session_id, str):
        # Convert string to UUID if needed
        session_id = uuid.UUID(session_id)

    # Store user message
    user_message = ChatMessage(
        id=uuid.uuid4(),
        session_id=session_id,  # Now session_id is guaranteed to be set
        role="user",
        content=content,
    )
    db.add(user_message)
    await db.commit()

    # Prepare messages for LLM
    messages = []

    # Add system prompt as the first message
    messages.append({"role": "system", "content": BPMN_SYSTEM_PROMPT})

    # Add context about the current XML if provided
    if current_xml:
        # Append to the system prompt instead of adding a separate system message
        xml_context = f"\nThe user is working with the following BPMN XML. Use this as context for your responses:\n\n{current_xml}"
        messages[0]["content"] += xml_context

    # Get previous messages if in a session
    if session_id:
        # Get previous messages from the database
        stmt = (
            ChatMessage.__table__.select()
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
        )
        result = await db.execute(stmt)
        previous_messages = result.fetchall()

        # Add previous messages to the context
        for msg in previous_messages:
            if msg.role != "system":  # Skip system messages
                messages.append({"role": msg.role, "content": msg.content})
    else:
        # Just add the current user message
        messages.append({"role": "user", "content": content})

    # Send acknowledgment to client
    await chat_manager.send_personal_message(
        client_id,
        "message_received",
        {
            "messageId": str(user_message.id),
            "timestamp": user_message.created_at.isoformat(),
        },
    )

    # Get response from LLM (non-streaming approach)
    try:
        # Notify client that assistant is typing
        await chat_manager.send_personal_message(
            client_id, "assistant_typing", {"status": "started"}
        )

        # Call LLM without streaming
        response = await llm_service.chat_completion(
            messages=messages, model=model, temperature=0.5, max_tokens=8192
        )

        # Get response content
        response_content = response["content"]

        # Extract XML if present in the response
        xml = None
        content = response_content

        # Simple extraction of XML from markdown code blocks
        if "```xml" in content and "```" in content.split("```xml", 1)[1]:
            xml = content.split("```xml", 1)[1].split("```", 1)[0].strip()
        elif "```" in content and "```" in content.split("```", 1)[1]:
            # Try without language specifier
            potential_xml = content.split("```", 1)[1].split("```", 1)[0].strip()
            if potential_xml.startswith("<?xml") or potential_xml.startswith("<bpmn:"):
                xml = potential_xml

        # Store assistant message
        assistant_message = ChatMessage(
            id=uuid.uuid4(),
            session_id=session_id,
            role="assistant",
            content=response_content,
            xml_content=xml,
            model=model,
        )
        db.add(assistant_message)
        await db.commit()

        # Send the message content to the original client
        await chat_manager.send_personal_message(
            client_id,
            "new_message",
            {
                "messageId": str(assistant_message.id),
                "role": "assistant",
                "content": response_content,
                "xml": xml,
                "timestamp": assistant_message.created_at.isoformat(),
            },
        )

        # Send completion notification
        await chat_manager.send_personal_message(
            client_id,
            "message_complete",
            {
                "messageId": str(assistant_message.id),
                "timestamp": assistant_message.created_at.isoformat(),
                "xml": xml,
            },
        )

        # If this is a session, broadcast to other clients
        if session_id and session_id in chat_manager.session_clients:
            await chat_manager.broadcast_to_session(
                session_id,
                "new_message",
                {
                    "messageId": str(assistant_message.id),
                    "role": "assistant",
                    "content": response_content,
                    "xml": xml,
                    "timestamp": assistant_message.created_at.isoformat(),
                },
                exclude_client=client_id,
            )

    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        await chat_manager.send_personal_message(
            client_id, "error", {"message": f"Failed to process message: {str(e)}"}
        )


async def handle_join_session(client_id: str, data: Dict[str, Any]):
    """
    Handle client joining a chat session.

    Args:
        client_id: Unique identifier for the client
        data: Message data containing session ID
    """
    session_id = data.get("sessionId")
    if session_id:
        try:
            # Convert string to UUID if needed
            if isinstance(session_id, str):
                session_id = uuid.UUID(session_id)
            await chat_manager.join_session(client_id, session_id)
        except ValueError as e:
            logger.error(f"Invalid session ID: {e}")
            await chat_manager.send_personal_message(
                client_id, "error", {"message": f"Invalid session ID: {str(e)}"}
            )


async def handle_leave_session(client_id: str):
    """
    Handle client leaving a chat session.

    Args:
        client_id: Unique identifier for the client
    """
    await chat_manager.leave_session(client_id)


async def handle_typing_indicator(client_id: str, data: Dict[str, Any]):
    """
    Handle typing indicator updates.

    Args:
        client_id: Unique identifier for the client
        data: Message data containing typing status and session ID
    """
    session_id = data.get("sessionId")
    is_typing = data.get("isTyping", False)

    if session_id:
        try:
            # Convert string to UUID if needed
            if isinstance(session_id, str):
                session_id = uuid.UUID(session_id)

            # Broadcast typing status to all clients in session except sender
            await chat_manager.broadcast_to_session(
                session_id,
                "typing_indicator",
                {
                    "clientId": client_id,
                    "isTyping": is_typing,
                    "timestamp": datetime.now().isoformat(),
                },
                exclude_client=client_id,
            )
        except ValueError as e:
            logger.error(f"Invalid session ID in typing indicator: {e}")
