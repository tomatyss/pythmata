from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.params import Depends as FastAPIDepends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import and_

from pythmata.api.dependencies import get_session, get_state_manager
from pythmata.api.schemas import (
    ApiResponse,
    PaginatedResponse,
    ProcessInstanceCreate,
    ProcessInstanceResponse,
)
from pythmata.models.process import ProcessDefinition as ProcessDefinitionModel
from pythmata.models.process import ProcessInstance as ProcessInstanceModel
from pythmata.models.process import ProcessStatus, Variable
from pythmata.utils.logger import get_logger
from pythmata.core.engine import ProcessExecutor
from pythmata.core.state import StateManager

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
    state_manager: StateManager = Depends(get_state_manager),
):
    """Create a new process instance."""
    try:
        # Verify process definition exists
        result = await session.execute(
            select(ProcessDefinitionModel).filter(
                ProcessDefinitionModel.id == data.definition_id
            )
        )
        definition = result.scalar_one_or_none()
        if not definition:
            raise HTTPException(
                status_code=404,
                detail=f"Process definition {data.definition_id} not found",
            )

        # Create instance
        instance = ProcessInstanceModel(
            definition_id=data.definition_id,
            status=ProcessStatus.RUNNING,
            start_time=datetime.now(timezone.utc),
        )
        session.add(instance)
        await session.commit()
        await session.refresh(instance)

        # Initialize process engine
        executor = ProcessExecutor(state_manager)

        # Store variables if provided
        if data.variables:
            for name, variable in data.variables.items():
                # Store in Redis
                await state_manager.set_variable(
                    instance_id=str(instance.id),
                    name=name,
                    variable=variable,
                )

                # Store in database
                storage_format = variable.to_storage_format()
                db_variable = Variable(
                    instance_id=instance.id,
                    name=name,
                    value_type=storage_format["value_type"],
                    value_data=storage_format["value_data"],
                    version=1,
                )
                session.add(db_variable)

            await session.commit()

        # Create initial token
        await executor.create_initial_token(str(instance.id), "Start_1")

        return {"data": instance}
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating instance: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/{instance_id}/suspend",
    response_model=ApiResponse[ProcessInstanceResponse],
)
async def suspend_instance(
    instance_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Suspend a process instance."""
    try:
        result = await session.execute(
            select(ProcessInstanceModel).filter(ProcessInstanceModel.id == instance_id)
        )
        instance = result.scalar_one_or_none()
        if not instance:
            raise HTTPException(status_code=404, detail="Process instance not found")

        # Refresh instance to get latest status
        await session.refresh(instance)

        if instance.status != ProcessStatus.RUNNING:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot suspend instance in {instance.status} status. Only RUNNING instances can be suspended.",
            )

        instance.status = ProcessStatus.SUSPENDED
        await session.commit()
        await session.refresh(instance)
        return {"data": instance}
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/{instance_id}/resume",
    response_model=ApiResponse[ProcessInstanceResponse],
)
async def resume_instance(
    instance_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Resume a suspended process instance."""
    try:
        result = await session.execute(
            select(ProcessInstanceModel).filter(ProcessInstanceModel.id == instance_id)
        )
        instance = result.scalar_one_or_none()
        if not instance:
            raise HTTPException(status_code=404, detail="Process instance not found")

        if instance.status != ProcessStatus.SUSPENDED:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot resume instance in {instance.status} status. Only SUSPENDED instances can be resumed.",
            )

        instance.status = ProcessStatus.RUNNING
        await session.commit()
        await session.refresh(instance)
        return {"data": instance}
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
