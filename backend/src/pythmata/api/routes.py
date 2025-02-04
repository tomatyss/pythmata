from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.params import Depends as FastAPIDepends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import and_

from pythmata.api.schemas import (
    ApiResponse,
    PaginatedResponse,
    ProcessDefinitionCreate,
    ProcessDefinitionResponse,
    ProcessDefinitionUpdate,
    ProcessInstanceCreate,
    ProcessInstanceFilter,
    ProcessInstanceResponse,
    ProcessStats,
    ScriptContent,
    ScriptResponse,
)
from pythmata.core.database import get_db
from pythmata.models.process import (
    ProcessDefinition as ProcessDefinitionModel,
    ProcessInstance as ProcessInstanceModel,
    ProcessStatus,
    Script as ScriptModel,
)
from pythmata.utils.logger import get_logger, log_error

router = APIRouter()
logger = get_logger(__name__)


async def get_session() -> AsyncSession:
    """Get database session."""
    db = get_db()
    async with db.session() as session:
        yield session


@router.get(
    "/processes",
    response_model=ApiResponse[PaginatedResponse[ProcessDefinitionResponse]],
)
async def get_processes(session: AsyncSession = Depends(get_session)):
    """Get all process definitions."""
    result = await session.execute(
        select(ProcessDefinitionModel).order_by(
            ProcessDefinitionModel.created_at.desc()
        )
    )
    processes = result.scalars().all()
    return {
        "data": {
            "items": processes,
            "total": len(processes),
            "page": 1,
            "pageSize": len(processes),
            "totalPages": 1,
        }
    }


@router.get(
    "/processes/{process_id}", response_model=ApiResponse[ProcessDefinitionResponse]
)
async def get_process(process_id: str, session: AsyncSession = Depends(get_session)):
    """Get a specific process definition."""
    result = await session.execute(
        select(ProcessDefinitionModel).filter(ProcessDefinitionModel.id == process_id)
    )
    process = result.scalar_one_or_none()
    if not process:
        raise HTTPException(status_code=404, detail="Process not found")
    return {"data": process}


@router.post("/processes", response_model=ApiResponse[ProcessDefinitionResponse])
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

        process = ProcessDefinitionModel(
            name=data.name, bpmn_xml=data.bpmn_xml, version=version
        )
        session.add(process)
        await session.commit()
        await session.refresh(process)
        return {"data": process}
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/processes/{process_id}", response_model=ApiResponse[ProcessDefinitionResponse]
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

        if data.name is not None:
            process.name = data.name
        if data.bpmn_xml is not None:
            process.bpmn_xml = data.bpmn_xml
        if data.version is not None:
            process.version = data.version
        else:
            process.version += 1  # Auto-increment version if not specified
        process.updated_at = datetime.now(timezone.utc)

        await session.commit()
        await session.refresh(process)
        return {"data": process}
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/processes/{process_id}")
async def delete_process(process_id: str, session: AsyncSession = Depends(get_session)):
    """Delete a process definition."""
    try:
        result = await session.execute(
            select(ProcessDefinitionModel).filter(
                ProcessDefinitionModel.id == process_id
            )
        )
        process = result.scalar_one_or_none()
        if not process:
            raise HTTPException(status_code=404, detail="Process not found")

        await session.delete(process)
        await session.commit()
        return {"message": "Process deleted successfully"}
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# Process Instance Endpoints

async def parse_datetime(date_str: Optional[str] = Query(None)) -> Optional[datetime]:
    """Parse datetime string to datetime object."""
    if not date_str:
        return None
    try:
        # Parse ISO format datetime string
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        # Ensure timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid datetime format. Expected ISO format with timezone: {str(e)}"
        )

@router.get(
    "/instances",
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
    "/instances/{instance_id}",
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
    "/instances",
    response_model=ApiResponse[ProcessInstanceResponse],
)
async def create_instance(
    data: ProcessInstanceCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a new process instance."""
    try:
        # Verify process definition exists
        result = await session.execute(
            select(ProcessDefinitionModel).filter(
                ProcessDefinitionModel.id == data.definition_id
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=404,
                detail=f"Process definition {data.definition_id} not found",
            )

        instance = ProcessInstanceModel(
            definition_id=data.definition_id,
            status=ProcessStatus.RUNNING,
        )
        session.add(instance)
        await session.commit()
        await session.refresh(instance)
        return {"data": instance}
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating instance: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/instances/{instance_id}/suspend",
    response_model=ApiResponse[ProcessInstanceResponse],
)
async def suspend_instance(
    instance_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Suspend a process instance."""
    try:
        # Get latest instance state from database
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
    "/instances/{instance_id}/resume",
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


@router.get("/stats", response_model=ApiResponse[ProcessStats])
async def get_statistics(session: AsyncSession = Depends(get_session)):
    """Get process statistics."""
    try:
        # Get total instances
        total_query = select(func.count()).select_from(ProcessInstanceModel)
        total_instances = await session.scalar(total_query)

        # Get status counts
        status_query = select(
            ProcessInstanceModel.status,
            func.count(ProcessInstanceModel.id)
        ).group_by(ProcessInstanceModel.status)
        status_result = await session.execute(status_query)
        status_counts = dict(status_result.all())

        # Get average completion time for completed instances
        completion_query = select(
            func.avg(
                ProcessInstanceModel.end_time - ProcessInstanceModel.start_time
            )
        ).where(ProcessInstanceModel.status == ProcessStatus.COMPLETED)
        avg_completion_time = await session.scalar(completion_query)
        avg_completion_seconds = (
            avg_completion_time.total_seconds()
            if avg_completion_time is not None
            else None
        )

        # Calculate error rate
        error_count = status_counts.get(ProcessStatus.ERROR, 0)
        error_rate = (error_count / total_instances * 100) if total_instances > 0 else 0

        # Get active instances count
        active_instances = status_counts.get(ProcessStatus.RUNNING, 0)

        return {
            "data": ProcessStats(
                total_instances=total_instances,
                status_counts=status_counts,
                average_completion_time=avg_completion_seconds,
                error_rate=error_rate,
                active_instances=active_instances,
            )
        }
    except Exception as e:
        logger.error(f"Error getting statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Script Management Endpoints

@router.get(
    "/processes/{process_def_id}/scripts",
    response_model=ApiResponse[List[ScriptResponse]],
)
async def list_scripts(
    process_def_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """List all scripts for a process definition."""
    try:
        result = await session.execute(
            select(ScriptModel)
            .filter(ScriptModel.process_def_id == process_def_id)
            .order_by(ScriptModel.node_id)
        )
        scripts = result.scalars().all()
        return {"data": scripts}
    except Exception as e:
        logger.error(f"Error listing scripts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/processes/{process_def_id}/scripts/{node_id}",
    response_model=ApiResponse[ScriptResponse],
)
async def get_script(
    process_def_id: UUID,
    node_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get a specific script."""
    result = await session.execute(
        select(ScriptModel).filter(
            ScriptModel.process_def_id == process_def_id,
            ScriptModel.node_id == node_id,
        )
    )
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return {"data": script}


@router.put(
    "/processes/{process_def_id}/scripts/{node_id}",
    response_model=ApiResponse[ScriptResponse],
)
async def update_script(
    process_def_id: UUID,
    node_id: str,
    data: ScriptContent,
    session: AsyncSession = Depends(get_session),
):
    """Update or create a script."""
    try:
        # Check if process definition exists
        proc_result = await session.execute(
            select(ProcessDefinitionModel).filter(
                ProcessDefinitionModel.id == process_def_id
            )
        )
        if not proc_result.scalar_one_or_none():
            raise HTTPException(
                status_code=404,
                detail="Process definition not found",
            )

        # Get existing script or create new one
        result = await session.execute(
            select(ScriptModel).filter(
                ScriptModel.process_def_id == process_def_id,
                ScriptModel.node_id == node_id,
            )
        )
        script = result.scalar_one_or_none()

        if script:
            script.content = data.content
            script.version = data.version
            script.updated_at = datetime.now(timezone.utc)
        else:
            script = ScriptModel(
                process_def_id=process_def_id,
                node_id=node_id,
                content=data.content,
                version=data.version,
            )
            session.add(script)

        await session.commit()
        await session.refresh(script)
        return {"data": script}
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error updating script: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
