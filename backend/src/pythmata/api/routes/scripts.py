from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pythmata.api.schemas import (
    ApiResponse,
    ScriptContent,
    ScriptResponse,
)
from pythmata.api.dependencies import get_session
from pythmata.models.process import ProcessDefinition as ProcessDefinitionModel
from pythmata.models.process import Script as ScriptModel
from pythmata.utils.logger import get_logger

router = APIRouter(tags=["scripts"])
logger = get_logger(__name__)


@router.get(
    "/processes/{process_def_id}/scripts",
    response_model=ApiResponse[list[ScriptResponse]],
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
