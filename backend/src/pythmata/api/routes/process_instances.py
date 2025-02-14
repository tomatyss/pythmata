"""Process instance API routes."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.params import Depends as FastAPIDepends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import and_

from pythmata.api.dependencies import get_event_bus, get_instance_manager, get_session
from pythmata.api.schemas import (
    ApiResponse,
    PaginatedResponse,
    ProcessInstanceCreate,
    ProcessInstanceResponse,
)
from pythmata.core.engine.instance import ProcessInstanceError, ProcessInstanceManager
from pythmata.core.events import EventBus
from pythmata.models.process import ProcessDefinition as ProcessDefinitionModel
from pythmata.models.process import ProcessInstance as ProcessInstanceModel
from pythmata.models.process import ProcessStatus
from pythmata.utils.logger import get_logger

router = APIRouter(prefix="/instances", tags=["instances"])
logger = get_logger(__name__)


async def parse_datetime(date_str: Optional[str] = Query(None)) -> Optional[datetime]:
    """Parse datetime string to datetime object."""
    if not date_str:
        return None
    try:
        # Parse ISO format datetime string
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        # Ensure timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid datetime format. Expected ISO format with timezone: {str(e)}",
        )


@router.get(
    "",
    response_model=ApiResponse[PaginatedResponse[ProcessInstanceResponse]],
)
async def list_instances(
    status: Optional[ProcessStatus] = Query(None, enum=ProcessStatus),
    start_date: Optional[datetime] = FastAPIDepends(parse_datetime),
    end_date: Optional[datetime] = FastAPIDepends(parse_datetime),
    definition_id: Optional[UUID] = Query(None),
    page: int = Query(1, gt=0),
    page_size: int = Query(10, gt=0, le=100),
    session: AsyncSession = Depends(get_session),
):
    """Get process instances with filtering and pagination."""
    try:
        query = select(ProcessInstanceModel)

        # Apply filters
        conditions = []
        if status:
            conditions.append(ProcessInstanceModel.status == status)
        if start_date:
            conditions.append(ProcessInstanceModel.start_time >= start_date)
        if end_date:
            conditions.append(ProcessInstanceModel.start_time <= end_date)
        if definition_id:
            conditions.append(ProcessInstanceModel.definition_id == definition_id)

        if conditions:
            query = query.where(and_(*conditions))

        # Add ordering
        query = query.order_by(ProcessInstanceModel.created_at.desc())

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await session.scalar(count_query)

        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await session.execute(query)
        instances = result.scalars().all()

        total_pages = (total + page_size - 1) // page_size

        return {
            "data": {
                "items": instances,
                "total": total,
                "page": page,
                "pageSize": page_size,
                "totalPages": total_pages,
            }
        }
    except Exception as e:
        logger.error(f"Error listing instances: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{instance_id}",
    response_model=ApiResponse[ProcessInstanceResponse],
)
async def get_instance(
    instance_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get a specific process instance."""
    result = await session.execute(
        select(ProcessInstanceModel).filter(ProcessInstanceModel.id == instance_id)
    )
    instance = result.scalar_one_or_none()
    if not instance:
        raise HTTPException(status_code=404, detail="Process instance not found")
    return {"data": instance}


@router.post(
    "",
    response_model=ApiResponse[ProcessInstanceResponse],
)
async def create_instance(
    data: ProcessInstanceCreate,
    session: AsyncSession = Depends(get_session),
    instance_manager: ProcessInstanceManager = Depends(get_instance_manager),
    event_bus: EventBus = Depends(get_event_bus),
):
    """Create a new process instance."""
    try:
        logger.info(f"Creating process instance with data: {data}")

        # Verify process definition exists
        result = await session.execute(
            select(ProcessDefinitionModel).filter(
                ProcessDefinitionModel.id == data.definition_id
            )
        )
        definition = result.scalar_one_or_none()
        if not definition:
            logger.error(f"Process definition {data.definition_id} not found")
            raise HTTPException(
                status_code=404,
                detail=f"Process definition {data.definition_id} not found",
            )

        logger.info(
            f"Found process definition: {definition.name} (v{definition.version})"
        )
        logger.info(f"Variable definitions: {definition.variable_definitions}")

        try:
            # Validate variables against process definition
            logger.info("Validating variables against process definition")
            data.validate_variables(definition.variable_definitions)
            logger.info("Variable validation successful")
        except ValueError as e:
            logger.error(f"Variable validation failed: {str(e)}")
            raise HTTPException(status_code=422, detail=str(e))

        # Create instance
        instance = ProcessInstanceModel(
            definition_id=data.definition_id,
            status=ProcessStatus.RUNNING,
            start_time=datetime.now(timezone.utc),
        )
        session.add(instance)
        await session.flush()  # Get the ID without committing
        logger.info(f"Created process instance with ID: {instance.id}")

        # Convert variables to storage format
        variables = {}
        if data.variables:
            variables = {
                name: var.to_storage_format() for name, var in data.variables.items()
            }
            logger.info(f"Converted variables for storage: {variables}")

        try:
            # Start process execution
            logger.info("Starting process execution")
            instance = await instance_manager.start_instance(
                instance=instance,
                bpmn_xml=definition.bpmn_xml,
                variables=variables,
            )
            logger.info("Process execution started successfully")

            # Commit the transaction to save the instance
            await session.commit()
            logger.info("Process instance committed to database")

            # Publish process.started event with just IDs
            await event_bus.publish(
                "process.started",
                {
                    "instance_id": str(instance.id),
                    "definition_id": str(instance.definition_id),
                },
            )
            logger.info("Published process.started event")

        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to start process execution: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Failed to start process: {str(e)}"
            )

        return {"data": instance}
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        error_msg = f"Error creating instance: {str(e)}"
        logger.error(error_msg, exc_info=True)  # Include full stack trace
        raise HTTPException(status_code=500, detail=error_msg)


@router.post(
    "/{instance_id}/suspend",
    response_model=ApiResponse[ProcessInstanceResponse],
)
async def suspend_instance(
    instance_id: UUID,
    instance_manager: ProcessInstanceManager = Depends(get_instance_manager),
):
    """Suspend a process instance."""
    try:
        instance = await instance_manager.suspend_instance(instance_id)
        return {"data": instance}
    except ProcessInstanceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error suspending instance: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/{instance_id}/resume",
    response_model=ApiResponse[ProcessInstanceResponse],
)
async def resume_instance(
    instance_id: UUID,
    instance_manager: ProcessInstanceManager = Depends(get_instance_manager),
):
    """Resume a suspended process instance."""
    try:
        instance = await instance_manager.resume_instance(instance_id)
        return {"data": instance}
    except ProcessInstanceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error resuming instance: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
