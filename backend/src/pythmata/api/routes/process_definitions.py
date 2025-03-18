from datetime import datetime, timezone
from typing import Optional, Tuple

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pythmata.api.dependencies import get_session
from pythmata.api.schemas import (
    ApiResponse,
    PaginatedResponse,
    ProcessDefinitionCreate,
    ProcessDefinitionResponse,
    ProcessDefinitionUpdate,
)
from pythmata.core.services.versioning.manager import VersionManager
from pythmata.models.process import ProcessDefinition as ProcessDefinitionModel
from pythmata.models.process import ProcessInstance as ProcessInstanceModel
from pythmata.models.process import ProcessStatus, BranchType
from pythmata.utils.logger import get_logger, log_error

logger = get_logger(__name__)

router = APIRouter(prefix="/processes", tags=["processes"])


async def get_process_stats(
    session: AsyncSession, process_id: Optional[str] = None
) -> list[Tuple[ProcessDefinitionModel, int, int]]:
    """
    Get process definition(s) with their instance statistics.

    Args:
        session: The database session
        process_id: Optional process definition ID to filter by

    Returns:
        List of tuples containing (process_definition, active_instances, total_instances)
    """
    query = (
        select(
            ProcessDefinitionModel,
            func.count(
                case((ProcessInstanceModel.status == ProcessStatus.RUNNING, 1))
            ).label("active_instances"),
            func.count(ProcessInstanceModel.id).label("total_instances"),
        )
        .outerjoin(
            ProcessInstanceModel,
            ProcessDefinitionModel.id == ProcessInstanceModel.definition_id,
        )
        .group_by(ProcessDefinitionModel.id)
    )

    if process_id:
        query = query.filter(ProcessDefinitionModel.id == process_id)
    else:
        query = query.order_by(ProcessDefinitionModel.created_at.desc())

    result = await session.execute(query)
    return result.all()


@router.get(
    "",
    response_model=ApiResponse[PaginatedResponse[ProcessDefinitionResponse]],
)
async def get_processes(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_session)
):
    """Get all process definitions with their instance statistics."""
    processes = await get_process_stats(session)
    
    # Apply pagination
    total = len(processes)
    total_pages = (total + page_size - 1) // page_size
    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, total)
    page_processes = processes[start_idx:end_idx]

    return {
        "data": {
            "items": [
                ProcessDefinitionResponse.model_validate(
                    {
                        k: v
                        for k, v in process[0].__dict__.items()
                        if k != "_sa_instance_state"
                    }
                    | {"active_instances": process[1], "total_instances": process[2]}
                )
                for process in page_processes
            ],
            "total": total,
            "page": page,
            "pageSize": page_size,
            "totalPages": total_pages,
        }
    }


@router.get(
    "/{process_id}",
    response_model=ApiResponse[ProcessDefinitionResponse],
)
async def get_process(process_id: str, session: AsyncSession = Depends(get_session)):
    """Get a specific process definition with its instance statistics."""
    processes = await get_process_stats(session, process_id)

    if not processes:
        raise HTTPException(status_code=404, detail="Process not found")

    process, active_instances, total_instances = processes[0]
    return {
        "data": ProcessDefinitionResponse.model_validate(
            {k: v for k, v in process.__dict__.items() if k != "_sa_instance_state"}
            | {"active_instances": active_instances, "total_instances": total_instances}
        )
    }


@router.post("", response_model=ApiResponse[ProcessDefinitionResponse])
@log_error(logger)
async def create_process(
    data: ProcessDefinitionCreate = Body(...),
    session: AsyncSession = Depends(get_session),
):
    """Create a new process definition."""
    try:
        # Check if process with same name exists and get max version
        result = await session.execute(
            select(ProcessDefinitionModel.version)
            .filter(ProcessDefinitionModel.name == data.name)
            .order_by(ProcessDefinitionModel.version.desc())
        )
        existing_version = result.scalar_one_or_none()

        # If process exists, increment version
        version = (existing_version or 0) + 1 if data.version is None else data.version

        # Log variable definitions for debugging
        logger.info(
            f"Creating process with {len(data.variable_definitions or [])} variable definitions"
        )
        if data.variable_definitions:
            logger.debug(f"Variable definitions: {data.variable_definitions}")

        process = ProcessDefinitionModel(
            name=data.name,
            bpmn_xml=data.bpmn_xml,
            version=version,
            variable_definitions=[
                definition.dict() for definition in data.variable_definitions or []
            ],
        )
        session.add(process)
        await session.commit()
        await session.refresh(process)
        
        # Create initial version for the new process
        try:
            version_manager = VersionManager(session)
            await version_manager.create_initial_version(
                process_definition_id=process.id,
                author="system",  # Could be improved to capture actual user
                commit_message="Initial process creation",
                branch_type=BranchType.MAIN,
                branch_name="main",
            )
            logger.info(f"Created initial version for new process: {process.id}")
        except Exception as version_error:
            # Log error but don't fail the process creation if version creation fails
            logger.error(f"Failed to create initial version for process: {str(version_error)}", exc_info=True)
            
        return {"data": process}
    except Exception as e:
        await session.rollback()
        logger.error(f"Error updating process: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/{process_id}",
    response_model=ApiResponse[ProcessDefinitionResponse],
)
async def update_process(
    process_id: str,
    data: ProcessDefinitionUpdate = Body(...),
    session: AsyncSession = Depends(get_session),
):
    """Update a process definition."""
    try:
        result = await session.execute(
            select(ProcessDefinitionModel).filter(
                ProcessDefinitionModel.id == process_id
            )
        )
        process = result.scalar_one_or_none()
        if not process:
            raise HTTPException(status_code=404, detail="Process not found")

        # Store original state for version tracking
        old_bpmn_xml = process.bpmn_xml
        old_variable_definitions = process.variable_definitions
        old_version = process.version

        if data.name is not None:
            process.name = data.name
        if data.bpmn_xml is not None:
            process.bpmn_xml = data.bpmn_xml
        if data.version is not None:
            process.version = data.version
        else:
            process.version += 1  # Auto-increment version if not specified
        if data.variable_definitions is not None:
            logger.info(
                f"Updating process with {len(data.variable_definitions)} variable definitions"
            )
            logger.debug(f"Variable definitions: {data.variable_definitions}")
            process.variable_definitions = [
                definition.model_dump() for definition in data.variable_definitions
            ]
        process.updated_at = datetime.now(timezone.utc)

        # Create version record for this update
        try:
            # Initialize version manager and create version record
            version_manager = VersionManager(session)
            
            # Determine if this is a bpmn or variable definitions change
            changes_description = []
            if data.bpmn_xml is not None and data.bpmn_xml != old_bpmn_xml:
                changes_description.append("BPMN diagram")
            if data.variable_definitions is not None and process.variable_definitions != old_variable_definitions:
                changes_description.append("variable definitions")
            
            # Default commit message based on what changed
            commit_message = f"Updated {', '.join(changes_description)}" if changes_description else "Updated process"
            
            # Create new version
            await version_manager.create_new_version(
                process_definition_id=process.id,
                author="system",  # Could be improved to get the actual user
                bpmn_xml=process.bpmn_xml,
                variable_definitions=process.variable_definitions,
                commit_message=commit_message,
                version_increment="patch",  # Using patch for regular updates
                branch_type=BranchType.MAIN,  # Default to main branch
                branch_name="main",
            )
            
            logger.info(f"Created version for process update: {process.id}")
        except Exception as version_error:
            # Log error but don't fail the update if version creation fails
            logger.error(f"Failed to create version for process update: {str(version_error)}", exc_info=True)

        await session.commit()
        await session.refresh(process)
        return {"data": process}
    except Exception as e:
        await session.rollback()
        logger.error(f"Error updating process: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{process_id}")
@log_error(logger)
async def delete_process(process_id: str, session: AsyncSession = Depends(get_session)):
    """Delete a process definition and all its related instances."""
    result = await session.execute(
        select(ProcessDefinitionModel).filter(ProcessDefinitionModel.id == process_id)
    )
    process = result.scalar_one_or_none()
    if not process:
        raise HTTPException(status_code=404, detail="Process not found")

    await session.delete(process)
    await session.commit()
    return {"message": "Process deleted successfully"}
