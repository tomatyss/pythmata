"""Process instance API routes."""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.params import Depends as FastAPIDepends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import and_

from pythmata.api.dependencies import (
    get_event_bus,
    get_instance_manager,
    get_session,
    get_state_manager,
)
from pythmata.api.schemas import (
    ApiResponse,
    PaginatedResponse,
    ProcessInstanceCreate,
    ProcessInstanceResponse,
    TokenResponse,
)
from pythmata.core.bpmn.parser import BPMNParser
from pythmata.core.engine.instance import ProcessInstanceError, ProcessInstanceManager
from pythmata.core.engine.token import Token, TokenState
from pythmata.core.events import EventBus
from pythmata.core.types import Event, EventType
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
    status: Optional[str] = Query(
        None,
        description="Process status",
        enum=[status.value for status in ProcessStatus],
    ),
    start_date: Optional[datetime] = FastAPIDepends(parse_datetime),
    end_date: Optional[datetime] = FastAPIDepends(parse_datetime),
    definition_id: Optional[UUID] = Query(None),
    page: int = Query(1, gt=0),
    page_size: int = Query(10, gt=0, le=100),
    session: AsyncSession = Depends(get_session),
):
    # Convert string status to enum if provided
    status_enum = ProcessStatus(status) if status else None
    """Get process instances with filtering and pagination."""
    try:
        # Build base query starting from ProcessInstanceModel
        base_query = select(ProcessInstanceModel)

        # Build conditions
        conditions = []
        if definition_id:
            conditions.append(ProcessInstanceModel.definition_id == definition_id)
        if status_enum:
            conditions.append(ProcessInstanceModel.status == status_enum)
        if start_date:
            conditions.append(ProcessInstanceModel.start_time >= start_date)
        if end_date:
            conditions.append(ProcessInstanceModel.start_time <= end_date)

        # Apply conditions to base query
        if conditions:
            base_query = base_query.where(and_(*conditions))

        # Get total count using subquery as recommended by SQLAlchemy
        total = await session.scalar(
            select(func.count()).select_from(base_query.subquery())
        )

        # Build data query with inner join to get definition name
        data_query = select(
            ProcessInstanceModel, ProcessDefinitionModel.name.label("definition_name")
        ).join(
            ProcessDefinitionModel,
            ProcessInstanceModel.definition_id == ProcessDefinitionModel.id,
            isouter=False,  # Use inner join
        )

        # Apply same conditions to data query
        if conditions:
            data_query = data_query.where(and_(*conditions))

        # Add ordering
        data_query = data_query.order_by(ProcessInstanceModel.created_at.desc())

        # Apply pagination
        data_query = data_query.offset((page - 1) * page_size).limit(page_size)

        # Execute data query
        result = await session.execute(data_query)
        rows = result.all()
        instances = []
        for row in rows:
            instance = row[0]
            instance.definition_name = row[1]
            instances.append(instance)

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
        select(
            ProcessInstanceModel, ProcessDefinitionModel.name.label("definition_name")
        )
        .join(
            ProcessDefinitionModel,
            ProcessInstanceModel.definition_id == ProcessDefinitionModel.id,
            isouter=False,
        )
        .where(ProcessInstanceModel.id == instance_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Process instance not found")
    instance = row[0]
    instance.definition_name = row[1]
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

        try:
            # Validate variables against process definition
            data.validate_variables(definition.variable_definitions)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

        # Create instance
        instance = ProcessInstanceModel(
            definition_id=data.definition_id,
            status=ProcessStatus.RUNNING,
            start_time=datetime.now(timezone.utc),
        )
        session.add(instance)
        await session.flush()  # Get the ID without committing

        # Convert variables to storage format
        variables = {}
        if data.variables:
            variables = {
                name: var.to_storage_format() for name, var in data.variables.items()
            }

        try:
            # Start process execution
            instance = await instance_manager.start_instance(
                instance=instance,
                bpmn_xml=definition.bpmn_xml,
                variables=variables,
            )

            # Commit the transaction to save the instance
            await session.commit()

            # Publish process.started event with just IDs
            await event_bus.publish(
                "process.started",
                {
                    "instance_id": str(instance.id),
                    "definition_id": str(instance.definition_id),
                },
            )

        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to start process execution: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Failed to start process: {str(e)}"
            )

        # Add definition name to instance before returning
        instance.definition_name = definition.name
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
    session: AsyncSession = Depends(get_session),
):
    """Suspend a process instance."""
    try:
        instance = await instance_manager.suspend_instance(instance_id)
        # Get definition name using the same query pattern
        result = await session.execute(
            select(ProcessDefinitionModel.name)
            .join(
                ProcessInstanceModel,
                ProcessInstanceModel.definition_id == ProcessDefinitionModel.id,
                isouter=False,
            )
            .where(ProcessInstanceModel.id == instance_id)
        )
        instance.definition_name = result.scalar_one()
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
    session: AsyncSession = Depends(get_session),
):
    """Resume a suspended process instance."""
    try:
        instance = await instance_manager.resume_instance(instance_id)
        # Get definition name using the same query pattern
        result = await session.execute(
            select(ProcessDefinitionModel.name)
            .join(
                ProcessInstanceModel,
                ProcessInstanceModel.definition_id == ProcessDefinitionModel.id,
                isouter=False,
            )
            .where(ProcessInstanceModel.id == instance_id)
        )
        instance.definition_name = result.scalar_one()
        return {"data": instance}
    except ProcessInstanceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error resuming instance: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{instance_id}/tokens",
    response_model=ApiResponse[List[TokenResponse]],
)
async def get_instance_tokens(
    instance_id: UUID,
    state_manager=Depends(get_state_manager),
    session: AsyncSession = Depends(get_session),
):
    """Get current token positions for a process instance."""
    try:
        # First verify instance exists and get its details
        instance = await session.get(ProcessInstanceModel, instance_id)
        if not instance:
            raise HTTPException(status_code=404, detail="Process instance not found")

        # Get process definition to get BPMN XML
        definition = await session.get(ProcessDefinitionModel, instance.definition_id)
        if not definition:
            raise HTTPException(status_code=404, detail="Process definition not found")

        # Get tokens from Redis
        tokens = await state_manager.get_token_positions(str(instance_id))

        # If instance is running but has no tokens, try to recreate initial token
        if instance.status == ProcessStatus.RUNNING and not tokens:
            # Parse BPMN to find start event
            parser = BPMNParser()
            process_graph = parser.parse(definition.bpmn_xml)
            start_event = next(
                (
                    node
                    for node in process_graph["nodes"]
                    if isinstance(node, Event) and node.event_type == EventType.START
                ),
                None,
            )
            if start_event:
                token = Token(instance_id=str(instance_id), node_id=start_event.id)
                await state_manager.add_token(
                    instance_id=str(instance_id),
                    node_id=start_event.id,
                    data=token.to_dict(),
                )
                await state_manager.update_token_state(
                    instance_id=str(instance_id),
                    node_id=start_event.id,
                    state=TokenState.ACTIVE,
                )
                tokens = await state_manager.get_token_positions(str(instance_id))

        return {
            "data": [
                TokenResponse(
                    node_id=token["node_id"],
                    state=token["state"],
                    scope_id=token.get("scope_id"),
                    data=token.get("data"),
                )
                for token in tokens
            ]
        }
    except Exception as e:
        logger.error(f"Error getting instance tokens: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
