"""API routes for project process management."""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from pythmata.api.dependencies import get_current_user, get_db
from pythmata.api.schemas.process import ProcessDefinitionResponse
from pythmata.models.process import ProcessDefinition
from pythmata.models.project import Project, ProjectMember, ProjectRole
from pythmata.models.user import User
from pythmata.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["project-processes"])


@router.get(
    "/projects/{project_id}/processes",
    response_model=List[ProcessDefinitionResponse],
)
async def list_project_processes(
    project_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all process definitions for a project.

    Args:
        project_id: Project ID
        skip: Number of processes to skip
        limit: Maximum number of processes to return
        db: Database session
        current_user: Current authenticated user

    Returns:
        List of process definitions
    """
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
            detail="Project not found",
        )

    # Check if user has permission to view processes
    role_query = select(ProjectRole).where(ProjectRole.id == member.role_id)
    role_result = await db.execute(role_query)
    role = role_result.scalar_one_or_none()
    if not role or not role.permissions.get("view_processes", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view processes in this project",
        )

    # Get processes for the project
    query = (
        select(ProcessDefinition)
        .where(ProcessDefinition.project_id == project_id)
        .order_by(ProcessDefinition.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    processes = result.scalars().all()

    return processes


@router.post(
    "/projects/{project_id}/processes/{process_id}",
    status_code=status.HTTP_200_OK,
)
async def attach_process_to_project(
    project_id: uuid.UUID,
    process_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Attach an existing process definition to a project.

    Args:
        project_id: Project ID
        process_id: Process definition ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        Success message
    """
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
            detail="Project not found",
        )

    # Check if user has permission to manage processes
    role_query = select(ProjectRole).where(ProjectRole.id == member.role_id)
    role_result = await db.execute(role_query)
    role = role_result.scalar_one_or_none()
    if not role or not role.permissions.get("manage_processes", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to manage processes in this project",
        )

    # Check if project exists
    project_query = select(Project).where(Project.id == project_id)
    project_result = await db.execute(project_query)
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Check if process exists
    process_query = select(ProcessDefinition).where(ProcessDefinition.id == process_id)
    process_result = await db.execute(process_query)
    process = process_result.scalar_one_or_none()
    if not process:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Process definition not found",
        )

    # Attach process to project
    process.project_id = project_id
    await db.commit()
    await db.refresh(process)

    # Log the action
    logger.info(
        f"Process {process_id} attached to project {project_id} by user {current_user.id}"
    )

    return {"message": "Process attached to project successfully"}


@router.delete(
    "/projects/{project_id}/processes/{process_id}",
    status_code=status.HTTP_200_OK,
)
async def detach_process_from_project(
    project_id: uuid.UUID,
    process_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Detach a process definition from a project.

    Args:
        project_id: Project ID
        process_id: Process definition ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        Success message
    """
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
            detail="Project not found",
        )

    # Check if user has permission to manage processes
    role_query = select(ProjectRole).where(ProjectRole.id == member.role_id)
    role_result = await db.execute(role_query)
    role = role_result.scalar_one_or_none()
    if not role or not role.permissions.get("manage_processes", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to manage processes in this project",
        )

    # Check if process exists and belongs to the project
    process_query = select(ProcessDefinition).where(
        ProcessDefinition.id == process_id,
        ProcessDefinition.project_id == project_id,
    )
    process_result = await db.execute(process_query)
    process = process_result.scalar_one_or_none()
    if not process:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Process definition not found in this project",
        )

    # Detach process from project
    process.project_id = None
    await db.commit()
    await db.refresh(process)

    # Log the action
    logger.info(
        f"Process {process_id} detached from project {project_id} by user {current_user.id}"
    )

    return {"message": "Process detached from project successfully"}
