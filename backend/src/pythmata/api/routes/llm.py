"""API routes for LLM interactions."""

import uuid
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pythmata.api.dependencies import get_session
from pythmata.api.schemas.llm import (
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
    ChatSessionCreate,
    ChatSessionResponse,
    XmlGenerationRequest,
    XmlModificationRequest,
    XmlResponse,
)
from pythmata.core.llm.prompts import BPMN_SYSTEM_PROMPT
from pythmata.core.llm.service import LlmService
from pythmata.models.chat import ChatMessage, ChatSession
from pythmata.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/llm", tags=["llm"])


@router.post("/chat", response_model=ChatResponse)
async def chat_completion(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """
    Generate a chat completion response for BPMN assistance.

    Args:
        request: Chat request with messages and context
        background_tasks: FastAPI background tasks
        db: Database session

    Returns:
        Response from the LLM with optional XML
    """
    try:
        llm_service = LlmService()

        # Get model from request or use default
        model = request.model or "anthropic:claude-3-7-sonnet-latest"

        # Prepare messages
        messages = []

        # Add system prompt as the first message
        messages.append({"role": "system", "content": BPMN_SYSTEM_PROMPT})

        # Add context about the current XML if provided
        if request.current_xml:
            # Append to the system prompt instead of adding a separate system message
            xml_context = f"\nThe user is working with the following BPMN XML. Use this as context for your responses:\n\n```{request.current_xml}```"
            messages[0]["content"] += xml_context

        # If session_id is provided, retrieve previous messages to include conversation history
        if request.session_id:
            try:
                # Get previous messages from the database
                previous_messages = await _get_chat_messages(str(request.session_id), db)
                
                # Add previous messages to maintain conversation history
                for msg in previous_messages:
                    messages.append({"role": msg["role"], "content": msg["content"]})
                
                logger.info(f"Added {len(previous_messages)} previous messages from session {request.session_id}")
            except Exception as e:
                logger.warning(f"Failed to retrieve previous messages: {str(e)}")
                # Continue with the request even if retrieving previous messages fails
        
        # Add user messages from the current request
        for m in request.messages:
            messages.append({"role": m.role, "content": m.content})

        # Call LLM service
        response = await llm_service.chat_completion(messages=messages, model=model)

        # Extract XML if present in the response
        content = response["content"]
        xml = None

        # Simple extraction of XML from markdown code blocks
        if "```xml" in content and "```" in content.split("```xml", 1)[1]:
            xml = content.split("```xml", 1)[1].split("```", 1)[0].strip()
        elif "```" in content and "```" in content.split("```", 1)[1]:
            # Try without language specifier
            potential_xml = content.split("```", 1)[1].split("```", 1)[0].strip()
            if potential_xml.startswith("<?xml") or potential_xml.startswith("<bpmn:"):
                xml = potential_xml

        session_id = request.session_id

        # Store conversation in background if process_id is provided
        if request.process_id:
            if not session_id:
                # Create a new session if none exists
                session = ChatSession(
                    id=uuid.uuid4(),
                    process_definition_id=request.process_id,
                    title=f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                )
                db.add(session)
                await db.commit()
                await db.refresh(session)
                session_id = session.id

            # Store user message
            user_message = ChatMessage(
                id=uuid.uuid4(),
                session_id=session_id,
                role="user",
                content=request.messages[-1].content,
            )
            db.add(user_message)

            # Store assistant message
            assistant_message = ChatMessage(
                id=uuid.uuid4(),
                session_id=session_id,
                role="assistant",
                content=response["content"],
                xml_content=xml,
                model=model,
                tokens_used=response.get("usage", {}).get("total_tokens"),
            )
            db.add(assistant_message)
            await db.commit()

        return {
            "message": response["content"],
            "xml": xml,
            "model": model,
            "session_id": str(session_id) if session_id else None,
        }
    except Exception as e:
        logger.error(f"Chat completion failed: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to generate response: {str(e)}"
        )


@router.post("/generate-xml", response_model=XmlResponse)
async def generate_xml(
    request: XmlGenerationRequest, db: AsyncSession = Depends(get_session)
):
    """
    Generate BPMN XML from a natural language description.

    Args:
        request: XML generation request
        db: Database session

    Returns:
        Generated XML and explanation
    """
    try:
        llm_service = LlmService()

        response = await llm_service.generate_xml(
            description=request.description,
            model=request.model or "anthropic:claude-3-7-sonnet-latest",
        )

        if not response["xml"]:
            raise ValueError("Failed to generate valid XML")

        return {"xml": response["xml"], "explanation": response["explanation"]}
    except Exception as e:
        logger.error(f"XML generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate XML: {str(e)}")


@router.post("/modify-xml", response_model=XmlResponse)
async def modify_xml(
    request: XmlModificationRequest, db: AsyncSession = Depends(get_session)
):
    """
    Modify existing BPMN XML based on a natural language request.

    Args:
        request: XML modification request
        db: Database session

    Returns:
        Modified XML and explanation
    """
    try:
        llm_service = LlmService()

        response = await llm_service.modify_xml(
            current_xml=request.current_xml,
            request=request.request,
            model=request.model or "anthropic:claude-3-7-sonnet-latest",
        )

        if not response["xml"]:
            raise ValueError("Failed to modify XML")

        return {"xml": response["xml"], "explanation": response["explanation"]}
    except Exception as e:
        logger.error(f"XML modification failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to modify XML: {str(e)}")


@router.post("/sessions", response_model=ChatSessionResponse)
async def create_chat_session(
    request: ChatSessionCreate, db: AsyncSession = Depends(get_session)
):
    """
    Create a new chat session for a process definition.

    Args:
        request: Chat session creation request
        db: Database session

    Returns:
        Created chat session
    """
    try:
        session_id = uuid.uuid4()
        chat_session = ChatSession(
            id=session_id,
            process_definition_id=request.process_definition_id,
            title=request.title,
        )
        db.add(chat_session)
        await db.commit()
        await db.refresh(chat_session)
        # Convert UUID fields to strings for response
        return {
            "id": str(chat_session.id),
            "process_definition_id": str(chat_session.process_definition_id),
            "title": chat_session.title,
            "created_at": chat_session.created_at,
            "updated_at": chat_session.updated_at,
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create chat session: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to create chat session: {str(e)}"
        )


@router.get("/sessions/{process_id}", response_model=List[ChatSessionResponse])
async def list_chat_sessions(process_id: str, db: AsyncSession = Depends(get_session)):
    """
    List all chat sessions for a process definition.

    Args:
        process_id: Process definition ID
        db: Database session

    Returns:
        List of chat sessions
    """
    try:
        result = await db.execute(
            select(ChatSession)
            .filter(ChatSession.process_definition_id == process_id)
            .order_by(ChatSession.updated_at.desc())
        )
        db_sessions = result.scalars().all()

        # Convert UUID fields to strings for response
        sessions = []
        for session in db_sessions:
            sessions.append(
                {
                    "id": str(session.id),
                    "process_definition_id": str(session.process_definition_id),
                    "title": session.title,
                    "created_at": session.created_at,
                    "updated_at": session.updated_at,
                }
            )
        return sessions
    except Exception as e:
        logger.error(f"Failed to list chat sessions: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to list chat sessions: {str(e)}"
        )


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
async def get_chat_messages_by_path(
    session_id: str, db: AsyncSession = Depends(get_session)
):
    """
    Get all messages for a chat session using path parameter.

    Args:
        session_id: Chat session ID
        db: Database session

    Returns:
        List of chat messages
    """
    return await _get_chat_messages(session_id, db)


@router.get("/messages", response_model=List[ChatMessageResponse])
async def get_chat_messages_by_query(
    session_id: str, db: AsyncSession = Depends(get_session)
):
    """
    Get all messages for a chat session using query parameter.

    Args:
        session_id: Chat session ID (query parameter)
        db: Database session

    Returns:
        List of chat messages
    """
    return await _get_chat_messages(session_id, db)


async def _get_chat_messages(session_id: str, db: AsyncSession) -> List[Dict[str, Any]]:
    """
    Helper function to get chat messages for a session.

    Args:
        session_id: Chat session ID
        db: Database session

    Returns:
        List of chat messages
    """
    try:
        logger.info(f"Fetching messages for session: {session_id}")
        result = await db.execute(
            select(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
        )
        db_messages = result.scalars().all()
        logger.info(f"Found {len(db_messages)} messages for session {session_id}")

        # Convert UUID fields to strings for response
        messages = []
        for message in db_messages:
            messages.append(
                {
                    "id": str(message.id),
                    "role": message.role,
                    "content": message.content,
                    "xml_content": message.xml_content,
                    "model": message.model,
                    "created_at": message.created_at,
                }
            )
        return messages
    except Exception as e:
        logger.error(f"Failed to get chat messages: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get chat messages: {str(e)}"
        )
