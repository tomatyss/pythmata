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
    ProcessVersionResponse,
)
from pythmata.api.schemas.process.definitions import ProcessDefinitionUpdate
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
        # Determine version number
        result = await session.execute(
            select(func.max(ProcessDefinitionModel.version))
            .filter(ProcessDefinitionModel.name == data.name)
        )
        max_existing_version = result.scalar() or 0
        version = max_existing_version + 1

        logger.info(
            f"Creating process '{data.name}' version {version} with {len(data.variable_definitions or [])} vars."
        )
        if data.variable_definitions:
            logger.debug(f"Variable definitions: {data.variable_definitions}")

        # Create Process Definition
        process = ProcessDefinitionModel(
            name=data.name,
            bpmn_xml=data.bpmn_xml,
            version=version,
            variable_definitions=[
                definition.model_dump() for definition in data.variable_definitions or []
            ],
        )
        session.add(process)
        await session.flush()  # Assign ID to process object

        # Create initial Process Version
        process_version = ProcessVersion(
            process_id=process.id,
            number=process.version,
            bpmn_xml=process.bpmn_xml,
            notes="Initial version created."
        )
        session.add(process_version)

        await session.commit()  # Commit both objects
        await session.refresh(process) # Refresh to load relationships if needed later

        # Manually construct response data including stats
        # We know stats are 0 for a new process
        response_data = ProcessDefinitionResponse.model_validate(
             {k: v for k, v in process.__dict__.items() if k != '_sa_instance_state'}
             | {"active_instances": 0, "total_instances": 0}
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
@log_error(logger)
async def update_process(
    process_id: str,
    data: ProcessDefinitionUpdate = Body(...),
    session: AsyncSession = Depends(get_session),
):
    """Update a process definition. Creates a new version if BPMN XML changes."""
    try:
        result = await session.execute(
            select(ProcessDefinitionModel).filter(
                ProcessDefinitionModel.id == process_id
            )
        )
        process = result.scalar_one_or_none()
        if not process:
            raise HTTPException(status_code=404, detail="Process not found")

        updated = False
        version_created = False

        # Update name if provided and different
        if data.name is not None and process.name != data.name:
            logger.info(f"Updating name for process {process_id} to '{data.name}'")
            process.name = data.name
            updated = True

        # Update variable definitions if provided
        # Note: This comparison assumes list order matters. For a more robust check,
        # consider converting to sets of tuples or using a deep comparison library.
        if data.variable_definitions is not None:
            new_defs = [d.model_dump() for d in data.variable_definitions]
            if process.variable_definitions != new_defs:
                logger.info(f"Updating variable definitions for process {process_id}")
                process.variable_definitions = new_defs
                updated = True

        # Check if BPMN XML is provided and different
        if data.bpmn_xml is not None and process.bpmn_xml != data.bpmn_xml:
            logger.info(f"Updating BPMN XML and creating new version for process {process_id}")
            # Increment version number
            process.version += 1
            # Update BPMN on the main definition
            process.bpmn_xml = data.bpmn_xml
            updated = True
            version_created = True

            # Create new ProcessVersion entry
            new_version = ProcessVersion(
                process_id=process.id,
                number=process.version,
                bpmn_xml=process.bpmn_xml,
                notes=data.notes or f"Version {process.version} created via update.",
            )
            session.add(new_version)
            logger.info(f"Created ProcessVersion record number {process.version} for process {process_id}")

        if updated:
            process.updated_at = datetime.now(timezone.utc)
            session.add(process) # Add process to session if any changes occurred
            await session.commit()
            await session.refresh(process)
            logger.info(f"Process {process_id} updated successfully.{' New version created.' if version_created else ''}")
        else:
            logger.info(f"No changes detected for process {process_id}. Update skipped.")

        # Fetch stats for the response, regardless of update status
        stats_result = await get_process_stats(session, process_id)
        if not stats_result:
             # Should not happen if process existed, but handle defensively
             raise HTTPException(status_code=404, detail="Process not found after update attempt")

        _, active_instances, total_instances = stats_result[0]

        # Construct response using the (potentially updated) process data and fresh stats
        response_data = ProcessDefinitionResponse.model_validate(
             {k: v for k, v in process.__dict__.items() if k != '_sa_instance_state'}
             | {"active_instances": active_instances, "total_instances": total_instances}
         )

        return {"data": response_data}

    except HTTPException as http_exc:
        await session.rollback()
        raise http_exc # Re-raise HTTP exceptions directly
    except Exception as e:
        await session.rollback()
        logger.error(f"Error updating process {process_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error updating process: {str(e)}")


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
    response_model=ApiResponse[PaginatedResponse[ProcessVersionResponse]],
)
async def get_process_versions(
    process_id: str,
    session: AsyncSession = Depends(get_session),
    page: int = Query(1, ge=1, description="Page number"),
    pageSize: int = Query(10, ge=1, le=100, description="Number of items per page"),
):
    """Get the version history for a specific process definition with pagination."""
    try:
        # Verify process definition exists first
        process_check_result = await session.execute(
            select(ProcessDefinitionModel.id).filter(ProcessDefinitionModel.id == process_id)
        )
        if not process_check_result.scalar_one_or_none():
             raise HTTPException(status_code=404, detail="Process definition not found")

        # Count total versions for pagination
        total_count_result = await session.execute(
            select(func.count(ProcessVersion.id))
            .filter(ProcessVersion.process_id == process_id)
        )
        total_count = total_count_result.scalar_one()

        # Fetch versions for the current page, ordered by number descending
        offset = (page - 1) * pageSize
        versions_result = await session.execute(
            select(ProcessVersion)
            .filter(ProcessVersion.process_id == process_id)
            .order_by(ProcessVersion.number.desc())
            .limit(pageSize)
            .offset(offset)
        )
        versions = versions_result.scalars().all()

        total_pages = (total_count + pageSize - 1) // pageSize

        return {
            "data": {
                "items": versions,
                "total": total_count,
                "page": page,
                "pageSize": pageSize,
                "totalPages": total_pages,
            }
        }
    except HTTPException:
        raise # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error fetching versions for process {process_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching process versions: {str(e)}")


@router.get(
    "/{process_id}/versions/{version_number}",
    response_model=ApiResponse[ProcessVersionResponse],
)
async def get_process_version_by_number(
    process_id: str,
    version_number: int,
    session: AsyncSession = Depends(get_session),
):
    """Get a specific version of a process definition by its number."""
    try:
        # Verify process definition exists first (optional but good practice)
        process_check = await session.execute(
            select(ProcessDefinitionModel.id).filter(ProcessDefinitionModel.id == process_id)
        )
        if not process_check.scalar_one_or_none():
             raise HTTPException(status_code=404, detail="Process definition not found")

        # Fetch the specific version
        result = await session.execute(
            select(ProcessVersion)
            .filter(ProcessVersion.process_id == process_id)
            .filter(ProcessVersion.number == version_number)
        )
        version = result.scalar_one_or_none()

        if not version:
            raise HTTPException(
                status_code=404,
                detail=f"Version {version_number} not found for process {process_id}",
            )

        return {"data": version}
    except HTTPException as http_exc:
        raise http_exc # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(
            f"Error fetching version {version_number} for process {process_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"Error fetching process version: {str(e)}"
        )
