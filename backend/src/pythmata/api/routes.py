from fastapi import APIRouter, HTTPException, Depends, Body
from typing import List
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pythmata.models.process import ProcessDefinition as ProcessDefinitionModel
from pythmata.core.database import get_db
from pythmata.api.schemas import (
    ProcessDefinitionResponse,
    ProcessDefinitionCreate,
    ProcessDefinitionUpdate
)

router = APIRouter(prefix="/api")

async def get_session() -> AsyncSession:
    """Get database session."""
    db = get_db()
    async with db.session() as session:
        yield session

@router.get("/processes", response_model=List[ProcessDefinitionResponse])
async def get_processes(session: AsyncSession = Depends(get_session)):
    """Get all process definitions."""
    result = await session.execute(
        select(ProcessDefinitionModel).order_by(ProcessDefinitionModel.created_at.desc())
    )
    return result.scalars().all()

@router.get("/processes/{process_id}", response_model=ProcessDefinitionResponse)
async def get_process(process_id: str, session: AsyncSession = Depends(get_session)):
    """Get a specific process definition."""
    result = await session.execute(
        select(ProcessDefinitionModel).filter(ProcessDefinitionModel.id == process_id)
    )
    process = result.scalar_one_or_none()
    if not process:
        raise HTTPException(status_code=404, detail="Process not found")
    return process

@router.post("/processes", response_model=ProcessDefinitionResponse)
async def create_process(
    data: ProcessDefinitionCreate = Body(...),
    session: AsyncSession = Depends(get_session)
):
    """Create a new process definition."""
    try:
        process = ProcessDefinitionModel(
            name=data.name,
            bpmn_xml=data.bpmn_xml,
            version=data.version
        )
        session.add(process)
        await session.commit()
        await session.refresh(process)
        return process
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/processes/{process_id}", response_model=ProcessDefinitionResponse)
async def update_process(
    process_id: str,
    data: ProcessDefinitionUpdate = Body(...),
    session: AsyncSession = Depends(get_session)
):
    """Update a process definition."""
    try:
        result = await session.execute(
            select(ProcessDefinitionModel).filter(ProcessDefinitionModel.id == process_id)
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
        process.updated_at = datetime.utcnow()
        
        await session.commit()
        await session.refresh(process)
        return process
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/processes/{process_id}")
async def delete_process(
    process_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Delete a process definition."""
    try:
        result = await session.execute(
            select(ProcessDefinitionModel).filter(ProcessDefinitionModel.id == process_id)
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
