"""API routes for project management."""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from pythmata.api.dependencies import get_db
from pythmata.api.schemas.project import (
    ProjectCreate,
    ProjectDescriptionCreate,
    ProjectDescriptionResponse,
    ProjectDetailResponse,
    ProjectMemberCreate,
    ProjectMemberResponse,
    ProjectMemberUpdate,
    ProjectResponse,
    ProjectRoleCreate,
    ProjectRoleResponse,
    ProjectRoleUpdate,
    ProjectUpdate,
    TagCreate,
    TagResponse,
    TagUpdate,
)
from pythmata.core.auth import get_current_user
from pythmata.models.audit import log_permission_change
from pythmata.models.process import ProcessDefinition
from pythmata.models.project import (
    Project,
    ProjectDescription,
    ProjectMember,
    ProjectRole,
    ProjectStatus,
    Tag,
)
from pythmata.models.user import User

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new project.

    Args:
        project_data: Project data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Created project
    """
    # Create project
    project = Project(
        name=project_data.name,
        description=project_data.description,
        status=ProjectStatus(project_data.status),
        owner_id=current_user.id,
    )
    db.add(project)
    await db.flush()

    # Create owner role if it doesn't exist
    owner_role = await db.execute(
        select(ProjectRole).where(ProjectRole.name == "Owner")
    )
    owner_role = owner_role.scalar_one_or_none()
    if not owner_role:
        owner_role = ProjectRole(
            name="Owner",
            permissions={
                "manage_project": True,
                "manage_members": True,
                "manage_processes": True,
                "view_processes": True,
                "execute_processes": True,
            },
        )
        db.add(owner_role)
        await db.flush()

    # Add current user as project owner
    project_member = ProjectMember(
        project_id=project.id,
        user_id=current_user.id,
        role_id=owner_role.id,
    )
    db.add(project_member)
    await db.commit()
    await db.refresh(project)

    # Load relationships for response
    await db.refresh(project, ["owner", "members"])
    for member in project.members:
        await db.refresh(member, ["user", "role"])

    return project


@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List projects the current user has access to.

    Args:
        skip: Number of projects to skip
        limit: Maximum number of projects to return
        status: Filter by project status
        db: Database session
        current_user: Current authenticated user

    Returns:
        List of projects
    """
    # Build query
    query = (
        select(Project)
        .join(ProjectMember, Project.id == ProjectMember.project_id)
        .where(ProjectMember.user_id == current_user.id)
        .options(
            joinedload(Project.owner),
            selectinload(Project.members).joinedload(ProjectMember.user),
            selectinload(Project.members).joinedload(ProjectMember.role),
        )
    )

    # Apply status filter if provided
    if status:
        query = query.where(Project.status == ProjectStatus(status))

    # Apply pagination
    query = query.offset(skip).limit(limit)

    # Execute query
    result = await db.execute(query)
    projects = result.unique().scalars().all()

    # Get current description for each project
    for project in projects:
        current_description_query = (
            select(ProjectDescription)
            .where(
                ProjectDescription.project_id == project.id,
                ProjectDescription.is_current == True,
            )
            .options(selectinload(ProjectDescription.tags))
        )
        current_description = await db.execute(current_description_query)
        project.current_description = current_description.scalar_one_or_none()

    return projects


@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a project by ID.

    Args:
        project_id: Project ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        Project details
    """
    # Check if user has access to the project
    member_query = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == current_user.id,
    )
    member = await db.execute(member_query)
    if not member.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Get project with relationships
    query = (
        select(Project)
        .where(Project.id == project_id)
        .options(
            joinedload(Project.owner),
            selectinload(Project.members).joinedload(ProjectMember.user),
            selectinload(Project.members).joinedload(ProjectMember.role),
            selectinload(Project.descriptions).selectinload(ProjectDescription.tags),
        )
    )
    result = await db.execute(query)
    project = result.unique().scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Get current description
    for description in project.descriptions:
        if description.is_current:
            project.current_description = description
            break

    # Count process definitions
    process_count_query = select(func.count(ProcessDefinition.id)).where(
        ProcessDefinition.project_id == project_id
    )
    process_count = await db.execute(process_count_query)
    project.process_count = process_count.scalar_one()

    return project


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    project_data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a project.

    Args:
        project_id: Project ID
        project_data: Project data to update
        db: Database session
        current_user: Current authenticated user

    Returns:
        Updated project
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

    # Check if user has permission to update the project
    role_query = select(ProjectRole).where(ProjectRole.id == member.role_id)
    role_result = await db.execute(role_query)
    role = role_result.scalar_one_or_none()
    if not role or not role.permissions.get("manage_project", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this project",
        )

    # Get project
    query = select(Project).where(Project.id == project_id)
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Update project
    if project_data.name is not None:
        project.name = project_data.name
    if project_data.description is not None:
        project.description = project_data.description
    if project_data.status is not None:
        project.status = ProjectStatus(project_data.status)

    await db.commit()
    await db.refresh(project)

    # Load relationships for response
    await db.refresh(project, ["owner", "members"])
    for member in project.members:
        await db.refresh(member, ["user", "role"])

    # Get current description
    current_description_query = (
        select(ProjectDescription)
        .where(
            ProjectDescription.project_id == project_id,
            ProjectDescription.is_current == True,
        )
        .options(selectinload(ProjectDescription.tags))
    )
    current_description = await db.execute(current_description_query)
    project.current_description = current_description.scalar_one_or_none()

    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a project.

    Args:
        project_id: Project ID
        db: Database session
        current_user: Current authenticated user
    """
    # Check if user is the project owner
    project_query = select(Project).where(
        Project.id == project_id,
        Project.owner_id == current_user.id,
    )
    project_result = await db.execute(project_query)
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or you are not the owner",
        )

    # Delete project
    await db.delete(project)
    await db.commit()


# Project Members API


@router.get("/{project_id}/members", response_model=List[ProjectMemberResponse])
async def list_project_members(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List project members.

    Args:
        project_id: Project ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        List of project members
    """
    # Check if user has access to the project
    member_query = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == current_user.id,
    )
    member = await db.execute(member_query)
    if not member.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Get project members
    query = (
        select(ProjectMember)
        .where(ProjectMember.project_id == project_id)
        .options(
            joinedload(ProjectMember.user),
            joinedload(ProjectMember.role),
        )
    )
    result = await db.execute(query)
    members = result.unique().scalars().all()

    return members


@router.post(
    "/{project_id}/members",
    response_model=ProjectMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_project_member(
    project_id: uuid.UUID,
    member_data: ProjectMemberCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Add a member to a project.

    Args:
        project_id: Project ID
        member_data: Member data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Added project member
    """
    # Check if user has permission to add members
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

    role_query = select(ProjectRole).where(ProjectRole.id == member.role_id)
    role_result = await db.execute(role_query)
    role = role_result.scalar_one_or_none()
    if not role or not role.permissions.get("manage_members", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to add members to this project",
        )

    # Check if user exists
    user_query = select(User).where(User.id == member_data.user_id)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Check if role exists
    role_query = select(ProjectRole).where(ProjectRole.id == member_data.role_id)
    role_result = await db.execute(role_query)
    role = role_result.scalar_one_or_none()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    # Check if user is already a member
    existing_member_query = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == member_data.user_id,
    )
    existing_member_result = await db.execute(existing_member_query)
    existing_member = existing_member_result.scalar_one_or_none()
    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this project",
        )

    # Add member
    project_member = ProjectMember(
        project_id=project_id,
        user_id=member_data.user_id,
        role_id=member_data.role_id,
    )
    db.add(project_member)

    # Log the permission change
    await log_permission_change(
        db=db,
        user_id=current_user.id,
        target_user_id=member_data.user_id,
        project_id=project_id,
        old_role_id=None,
        new_role_id=member_data.role_id,
        ip_address=request.client.host if request.client else None,
    )

    await db.commit()
    await db.refresh(project_member)

    # Load relationships for response
    await db.refresh(project_member, ["user", "role"])

    return project_member


@router.put("/{project_id}/members/{user_id}", response_model=ProjectMemberResponse)
async def update_project_member(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    member_data: ProjectMemberUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a project member's role.

    Args:
        project_id: Project ID
        user_id: User ID of the member to update
        member_data: Member data to update
        db: Database session
        current_user: Current authenticated user

    Returns:
        Updated project member
    """
    # Check if user has permission to update members
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

    role_query = select(ProjectRole).where(ProjectRole.id == member.role_id)
    role_result = await db.execute(role_query)
    role = role_result.scalar_one_or_none()
    if not role or not role.permissions.get("manage_members", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update members in this project",
        )

    # Get member to update
    target_member_query = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id,
    )
    target_member_result = await db.execute(target_member_query)
    target_member = target_member_result.scalar_one_or_none()
    if not target_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    # Check if role exists
    role_query = select(ProjectRole).where(ProjectRole.id == member_data.role_id)
    role_result = await db.execute(role_query)
    role = role_result.scalar_one_or_none()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    # Store old role ID for audit log
    old_role_id = target_member.role_id

    # Update member
    target_member.role_id = member_data.role_id

    # Log the role change
    await log_permission_change(
        db=db,
        user_id=current_user.id,
        target_user_id=user_id,
        project_id=project_id,
        old_role_id=old_role_id,
        new_role_id=member_data.role_id,
        ip_address=request.client.host if request.client else None,
    )

    await db.commit()
    await db.refresh(target_member)

    # Load relationships for response
    await db.refresh(target_member, ["user", "role"])

    return target_member


@router.delete(
    "/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_project_member(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Remove a member from a project.

    Args:
        project_id: Project ID
        user_id: User ID of the member to remove
        db: Database session
        current_user: Current authenticated user
    """
    # Check if user has permission to remove members
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

    # Cannot remove project owner
    project_query = select(Project).where(Project.id == project_id)
    project_result = await db.execute(project_query)
    project = project_result.scalar_one_or_none()
    if project and project.owner_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove project owner",
        )

    # Check permissions if not removing self
    if current_user.id != user_id:
        role_query = select(ProjectRole).where(ProjectRole.id == member.role_id)
        role_result = await db.execute(role_query)
        role = role_result.scalar_one_or_none()
        if not role or not role.permissions.get("manage_members", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to remove members from this project",
            )

    # Get member to remove
    target_member_query = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id,
    )
    target_member_result = await db.execute(target_member_query)
    target_member = target_member_result.scalar_one_or_none()
    if not target_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    # Store role ID for audit log
    role_id = target_member.role_id

    # Remove member
    await db.delete(target_member)

    # Log the permission change
    from pythmata.models.audit import AuditActionType, log_audit_event

    await log_audit_event(
        db=db,
        user_id=current_user.id,
        action_type=AuditActionType.PERMISSION_CHANGE,
        resource_type="project_member",
        resource_id=str(project_id),
        details={
            "action": "remove",
            "target_user_id": str(user_id),
            "project_id": str(project_id),
            "role_id": str(role_id),
        },
        ip_address=request.client.host if request.client else None,
    )

    await db.commit()


# Project Descriptions API


@router.get(
    "/{project_id}/descriptions", response_model=List[ProjectDescriptionResponse]
)
async def list_project_descriptions(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List project descriptions.

    Args:
        project_id: Project ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        List of project descriptions
    """
    # Check if user has access to the project
    member_query = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == current_user.id,
    )
    member = await db.execute(member_query)
    if not member.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Get project descriptions
    query = (
        select(ProjectDescription)
        .where(ProjectDescription.project_id == project_id)
        .options(selectinload(ProjectDescription.tags))
        .order_by(ProjectDescription.version.desc())
    )
    result = await db.execute(query)
    descriptions = result.unique().scalars().all()

    return descriptions


@router.post(
    "/{project_id}/descriptions",
    response_model=ProjectDescriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project_description(
    project_id: uuid.UUID,
    description_data: ProjectDescriptionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new project description.

    Args:
        project_id: Project ID
        description_data: Description data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Created project description
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

    # Check if user has permission to create descriptions
    role_query = select(ProjectRole).where(ProjectRole.id == member.role_id)
    role_result = await db.execute(role_query)
    role = role_result.scalar_one_or_none()
    if not role or not role.permissions.get("edit_description", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to create descriptions for this project",
        )

    # Get latest version
    version_query = select(func.max(ProjectDescription.version)).where(
        ProjectDescription.project_id == project_id
    )
    version_result = await db.execute(version_query)
    latest_version = version_result.scalar_one_or_none() or 0

    # Set all existing descriptions to not current
    update_query = select(ProjectDescription).where(
        ProjectDescription.project_id == project_id,
        ProjectDescription.is_current == True,
    )
    update_result = await db.execute(update_query)
    for description in update_result.scalars().all():
        description.is_current = False

    # Create description
    description = ProjectDescription(
        project_id=project_id,
        content=description_data.content,
        version=latest_version + 1,
        is_current=True,
    )
    db.add(description)
    await db.flush()

    # Add tags
    if description_data.tag_ids:
        for tag_id in description_data.tag_ids:
            tag_query = select(Tag).where(Tag.id == tag_id)
            tag_result = await db.execute(tag_query)
            tag = tag_result.scalar_one_or_none()
            if tag:
                description.tags.append(tag)

    await db.commit()
    await db.refresh(description)
    await db.refresh(description, ["tags"])

    return description


@router.get(
    "/{project_id}/descriptions/{description_id}",
    response_model=ProjectDescriptionResponse,
)
async def get_project_description(
    project_id: uuid.UUID,
    description_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a project description by ID.

    Args:
        project_id: Project ID
        description_id: Description ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        Project description
    """
    # Check if user has access to the project
    member_query = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == current_user.id,
    )
    member = await db.execute(member_query)
    if not member.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Get description
    query = (
        select(ProjectDescription)
        .where(
            ProjectDescription.project_id == project_id,
            ProjectDescription.id == description_id,
        )
        .options(selectinload(ProjectDescription.tags))
    )
    result = await db.execute(query)
    description = result.unique().scalar_one_or_none()
    if not description:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Description not found",
        )

    return description


@router.put(
    "/{project_id}/descriptions/{description_id}/set-current",
    response_model=ProjectDescriptionResponse,
)
async def set_current_description(
    project_id: uuid.UUID,
    description_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Set a description as the current version.

    Args:
        project_id: Project ID
        description_id: Description ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        Updated project description
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

    # Check if user has permission to update descriptions
    role_query = select(ProjectRole).where(ProjectRole.id == member.role_id)
    role_result = await db.execute(role_query)
    role = role_result.scalar_one_or_none()
    if not role or not role.permissions.get("edit_description", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update descriptions for this project",
        )

    # Set all descriptions to not current
    update_query = select(ProjectDescription).where(
        ProjectDescription.project_id == project_id,
        ProjectDescription.is_current == True,
    )
    update_result = await db.execute(update_query)
    for description in update_result.scalars().all():
        description.is_current = False

    # Set target description to current
    target_query = (
        select(ProjectDescription)
        .where(
            ProjectDescription.project_id == project_id,
            ProjectDescription.id == description_id,
        )
        .options(selectinload(ProjectDescription.tags))
    )
    target_result = await db.execute(target_query)
    target_description = target_result.unique().scalar_one_or_none()
    if not target_description:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Description not found",
        )

    target_description.is_current = True
    await db.commit()
    await db.refresh(target_description)

    return target_description


# Project Roles API


@router.get("/{project_id}/roles", response_model=List[ProjectRoleResponse])
async def list_project_roles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all project roles.

    Args:
        db: Database session
        current_user: Current authenticated user

    Returns:
        List of project roles
    """
    query = select(ProjectRole)
    result = await db.execute(query)
    roles = result.scalars().all()

    return roles


@router.post(
    "/roles", response_model=ProjectRoleResponse, status_code=status.HTTP_201_CREATED
)
async def create_project_role(
    role_data: ProjectRoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new project role.

    Args:
        role_data: Role data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Created project role
    """
    # Check if role with same name already exists
    existing_role_query = select(ProjectRole).where(ProjectRole.name == role_data.name)
    existing_role_result = await db.execute(existing_role_query)
    existing_role = existing_role_result.scalar_one_or_none()
    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role with this name already exists",
        )

    # Create role
    role = ProjectRole(
        name=role_data.name,
        permissions=role_data.permissions,
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)

    return role


@router.put("/roles/{role_id}", response_model=ProjectRoleResponse)
async def update_project_role(
    role_id: uuid.UUID,
    role_data: ProjectRoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a project role.

    Args:
        role_id: Role ID
        role_data: Role data to update
        db: Database session
        current_user: Current authenticated user

    Returns:
        Updated project role
    """
    # Get role
    query = select(ProjectRole).where(ProjectRole.id == role_id)
    result = await db.execute(query)
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    # Update role
    if role_data.name is not None:
        # Check if role with same name already exists
        if role_data.name != role.name:
            existing_role_query = select(ProjectRole).where(
                ProjectRole.name == role_data.name
            )
            existing_role_result = await db.execute(existing_role_query)
            existing_role = existing_role_result.scalar_one_or_none()
            if existing_role:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Role with this name already exists",
                )
        role.name = role_data.name

    if role_data.permissions is not None:
        role.permissions = role_data.permissions

    await db.commit()
    await db.refresh(role)

    return role


# Tags API


@router.get("/tags", response_model=List[TagResponse])
async def list_tags(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all tags.

    Args:
        db: Database session
        current_user: Current authenticated user

    Returns:
        List of tags
    """
    query = select(Tag)
    result = await db.execute(query)
    tags = result.scalars().all()

    return tags


@router.post("/tags", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def create_tag(
    tag_data: TagCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new tag.

    Args:
        tag_data: Tag data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Created tag
    """
    # Check if tag with same name already exists
    existing_tag_query = select(Tag).where(Tag.name == tag_data.name)
    existing_tag_result = await db.execute(existing_tag_query)
    existing_tag = existing_tag_result.scalar_one_or_none()
    if existing_tag:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tag with this name already exists",
        )

    # Create tag
    tag = Tag(
        name=tag_data.name,
        color=tag_data.color,
    )
    db.add(tag)
    await db.commit()
    await db.refresh(tag)

    return tag


@router.put("/tags/{tag_id}", response_model=TagResponse)
async def update_tag(
    tag_id: uuid.UUID,
    tag_data: TagUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a tag.

    Args:
        tag_id: Tag ID
        tag_data: Tag data to update
        db: Database session
        current_user: Current authenticated user

    Returns:
        Updated tag
    """
    # Get tag
    query = select(Tag).where(Tag.id == tag_id)
    result = await db.execute(query)
    tag = result.scalar_one_or_none()
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )

    # Update tag
    if tag_data.name is not None:
        # Check if tag with same name already exists
        if tag_data.name != tag.name:
            existing_tag_query = select(Tag).where(Tag.name == tag_data.name)
            existing_tag_result = await db.execute(existing_tag_query)
            existing_tag = existing_tag_result.scalar_one_or_none()
            if existing_tag:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Tag with this name already exists",
                )
        tag.name = tag_data.name

    if tag_data.color is not None:
        tag.color = tag_data.color

    await db.commit()
    await db.refresh(tag)

    return tag


@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a tag.

    Args:
        tag_id: Tag ID
        db: Database session
        current_user: Current authenticated user
    """
    # Get tag
    query = select(Tag).where(Tag.id == tag_id)
    result = await db.execute(query)
    tag = result.scalar_one_or_none()
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )

    # Delete tag
    await db.delete(tag)
    await db.commit()
