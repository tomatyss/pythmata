from datetime import datetime, timezone
from typing import Optional, Tuple

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pythmata.api.dependencies import get_session
from pythmata.api.schemas import (
    ApiResponse,
    PaginatedResponse,
    ProcessDefinitionCreate,
    ProcessDefinitionResponse,
    ProcessDefinitionUpdate,
    ProcessVersionResponse,
)
from pythmata.models.process import ProcessDefinition as ProcessDefinitionModel
from pythmata.models.process import ProcessInstance as ProcessInstanceModel
from pythmata.models.process import ProcessStatus
from pythmata.models.process import ProcessVersion
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
async def get_processes(session: AsyncSession = Depends(get_session)):
    """Get all process definitions with their instance statistics."""
    processes = await get_process_stats(session)

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
                for process in processes
            ],
            "total": len(processes),
            "page": 1,
            "pageSize": len(processes),
            "totalPages": 1,
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
    """Create a new process definition and its initial version."""
    try:
        logger.info(
            f"Creating process '{data.name}' with {len(data.variable_definitions or [])} vars."
        )
        if data.variable_definitions:
            logger.debug(f"Variable definitions: {data.variable_definitions}")

        # Create Process Definition
        process = ProcessDefinitionModel(
            name=data.name,
            variable_definitions=[
                definition.model_dump() for definition in data.variable_definitions or []
            ],
        )
        session.add(process)
        await session.flush()  # Assign ID to process object

        # Create initial Process Version
        process_version = ProcessVersion(
            process_id=process.id,
            number=1,  # Initial version is always 1
            bpmn_xml=data.bpmn_xml,
            notes=data.notes or "Initial version created."
        )
        session.add(process_version)
        await session.flush()

        # Set the current version
        process.current_version_id = process_version.id

        await session.commit()
        await session.refresh(process)

        # Get process stats for response
        processes = await get_process_stats(session, str(process.id))
        process_obj, active_instances, total_instances = processes[0]

        # Construct response with version info
        response_data = ProcessDefinitionResponse.model_validate(
            {k: v for k, v in process_obj.__dict__.items() if k != '_sa_instance_state'}
            | {
                "active_instances": active_instances,
                "total_instances": total_instances,
                "current_version": process_version
            }
        )
        return {"data": response_data}

    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating process '{data.name}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating process: {str(e)}")


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

        # Update basic process definition fields
        if data.name is not None:
            process.name = data.name
        if data.variable_definitions is not None:
            logger.info(
                f"Updating process with {len(data.variable_definitions)} variable definitions"
            )
            logger.debug(f"Variable definitions: {data.variable_definitions}")
            process.variable_definitions = [
                definition.model_dump() for definition in data.variable_definitions
            ]
        if data.current_version_id is not None:
            # Verify the version exists and belongs to this process
            version_result = await session.execute(
                select(ProcessVersion).filter(
                    ProcessVersion.id == data.current_version_id,
                    ProcessVersion.process_id == process_id
                )
            )
            version = version_result.scalar_one_or_none()
            if not version:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid version ID or version does not belong to this process"
                )
            process.current_version_id = data.current_version_id

        await session.commit()
        await session.refresh(process)

        # Get process stats for response
        processes = await get_process_stats(session, process_id)
        process_obj, active_instances, total_instances = processes[0]

        # Include current version in response if it exists
        current_version = None
        if process.current_version_id:
            version_result = await session.execute(
                select(ProcessVersion).filter(ProcessVersion.id == process.current_version_id)
            )
            current_version = version_result.scalar_one_or_none()

        return {
            "data": ProcessDefinitionResponse.model_validate(
                {k: v for k, v in process_obj.__dict__.items() if k != '_sa_instance_state'}
                | {
                    "active_instances": active_instances,
                    "total_instances": total_instances,
                    "current_version": current_version
                }
            )
        }
    except HTTPException:
        raise
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

@router.get(
    "/{process_id}/versions",
    response_model=ApiResponse[list[ProcessVersionResponse]],
)
async def get_process_versions(
    process_id: str, session: AsyncSession = Depends(get_session)
):
    """Get the version history for a specific process definition."""
    try:
        # Verify process definition exists first
        process_check = await session.execute(
            select(ProcessDefinitionModel.id).filter(ProcessDefinitionModel.id == process_id)
        )
        if not process_check.scalar_one_or_none():
             raise HTTPException(status_code=404, detail="Process definition not found")

        # Fetch versions ordered by number descending
        result = await session.execute(
            select(ProcessVersion)
            .filter(ProcessVersion.process_id == process_id)
            .order_by(ProcessVersion.number.desc())
        )
        versions = result.scalars().all()
        return {"data": versions}
    except HTTPException:
        raise # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error fetching versions for process {process_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching process versions: {str(e)}")
