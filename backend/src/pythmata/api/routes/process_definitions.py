from datetime import datetime, timezone
import re
import xml.etree.ElementTree as ET
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
)
from pythmata.models.process import ProcessDefinition as ProcessDefinitionModel
from pythmata.models.process import ProcessInstance as ProcessInstanceModel
from pythmata.models.process import ProcessStatus
from pythmata.models.process import Script as ScriptModel
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

        # Extract script content from BPMN XML
        await extract_and_save_scripts(session, process)

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


async def extract_and_save_scripts(session: AsyncSession, process: ProcessDefinitionModel) -> None:
    """
    Extract script content from BPMN XML and save to database.
    
    Args:
        session: Database session
        process: Process definition model
    """
    try:
        # Parse XML
        root = ET.fromstring(process.bpmn_xml)
        
        # Define namespaces
        ns = {
            "bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL",
            "pythmata": "http://pythmata.org/schema/1.0/bpmn"
        }
        
        # Find all script tasks
        script_tasks = root.findall(".//bpmn:scriptTask", ns)
        
        for task in script_tasks:
            node_id = task.get("id")
            if not node_id:
                continue
                
            # Check for script content in extension elements
            script_content = None
            ext_elements = task.find("bpmn:extensionElements", ns)
            
            if ext_elements is not None:
                script_config = ext_elements.find(".//pythmata:scriptConfig", ns)
                if script_config is not None:
                    # First try to get scriptContent as a direct child element
                    script_content_elem = script_config.find("pythmata:scriptContent", ns)
                    if script_content_elem is not None and script_content_elem.text:
                        script_content = script_content_elem.text.strip()
                    # If not found, try to get it as text content of scriptConfig
                    elif hasattr(script_config, "text") and script_config.text:
                        script_content = script_config.text.strip()
            
            if script_content:
                # Check if script already exists
                result = await session.execute(
                    select(ScriptModel).filter(
                        ScriptModel.process_def_id == process.id,
                        ScriptModel.node_id == node_id
                    )
                )
                script = result.scalar_one_or_none()
                
                if script:
                    # Update existing script
                    script.content = script_content
                    script.updated_at = datetime.now(timezone.utc)
                else:
                    # Create new script
                    script = ScriptModel(
                        process_def_id=process.id,
                        node_id=node_id,
                        content=script_content,
                        version=1
                    )
                    session.add(script)
                    
        logger.info(f"Extracted and saved scripts for process {process.id}")
    except Exception as e:
        logger.error(f"Error extracting scripts from BPMN XML: {str(e)}")
        # Don't raise the exception, just log it
