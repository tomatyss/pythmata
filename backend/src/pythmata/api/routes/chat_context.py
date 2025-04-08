"""API routes for chat context management."""

import uuid
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pythmata.api.dependencies import get_current_user, get_db
from pythmata.api.schemas.llm import ChatSessionResponse
from pythmata.models.chat import ChatSession
from pythmata.models.project import Project, ProjectMember, ProjectRole
from pythmata.models.user import User
from pythmata.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["chat-context"])


@router.put(
    "/chat/sessions/{session_id}/switch-project/{project_id}",
    response_model=ChatSessionResponse,
)
async def switch_chat_session_project(
    session_id: uuid.UUID,
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Switch the project context of a chat session.

    Args:
        session_id: Chat session ID
        project_id: Project ID to switch to
        db: Database session
        current_user: Current authenticated user

    Returns:
        Updated chat session
    """
    # Check if chat session exists
    session_query = select(ChatSession).where(ChatSession.id == session_id)
    session_result = await db.execute(session_query)
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found",
        )

    # Check if user has access to the project
    member_query = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == current_user.id,
    )
    member_result = await db.execute(member_query)
    member = member_result.scalar_one_or_none()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or you don't have access",
        )

    # Get project details
    project_query = select(Project).where(Project.id == project_id)
    project_result = await db.execute(project_query)
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Update chat session with new project context
    session.project_id = project_id
    
    # Add context information about the project switch
    context = f"Switched to project: {project.name}"
    if project.description:
        context += f"\nDescription: {project.description}"
    
    # If there's existing context, append to it
    if session.context:
        session.context += f"\n\n{context}"
    else:
        session.context = context
    
    await db.commit()
    await db.refresh(session)
    
    # Log the action
    logger.info(
        f"Chat session {session_id} switched to project {project_id} by user {current_user.id}"
    )
    
    # Prepare response
    response = {
        "id": str(session.id),
        "title": session.title,
        "context": session.context,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
    }
    
    if session.process_definition_id:
        response["process_definition_id"] = str(session.process_definition_id)
        
    if session.project_id:
        response["project_id"] = str(session.project_id)
        
    return response


@router.put(
    "/chat/sessions/{session_id}/clear-project",
    response_model=ChatSessionResponse,
)
async def clear_chat_session_project(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Clear the project context from a chat session.

    Args:
        session_id: Chat session ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        Updated chat session
    """
    # Check if chat session exists
    session_query = select(ChatSession).where(ChatSession.id == session_id)
    session_result = await db.execute(session_query)
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found",
        )

    # Clear project context
    session.project_id = None
    
    # Add context information about clearing the project
    context = "Project context cleared from chat session."
    
    # If there's existing context, append to it
    if session.context:
        session.context += f"\n\n{context}"
    else:
        session.context = context
    
    await db.commit()
    await db.refresh(session)
    
    # Log the action
    logger.info(
        f"Project context cleared from chat session {session_id} by user {current_user.id}"
    )
    
    # Prepare response
    response = {
        "id": str(session.id),
        "title": session.title,
        "context": session.context,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
    }
    
    if session.process_definition_id:
        response["process_definition_id"] = str(session.process_definition_id)
        
    return response
