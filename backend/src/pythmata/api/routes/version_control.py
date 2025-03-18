"""Version control API routes."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from pythmata.api.dependencies import get_session
from pythmata.api.schemas import (
    ApiResponse,
    VersionBase,
    VersionCreate,
    VersionDetailResponse,
    VersionListResponse,
    VersionResponse,
)
from pythmata.core.services.versioning.manager import VersionManager
from pythmata.models.process import BranchType, ChangeType, ProcessElementChange, ProcessVersion
from pythmata.utils.logger import get_logger, log_error

logger = get_logger(__name__)

router = APIRouter(prefix="/versions", tags=["versions"])


@router.post("", response_model=ApiResponse[VersionResponse])
@log_error(logger)
async def create_version(
    data: VersionCreate = Body(...),
    session: AsyncSession = Depends(get_session),
):
    """Create a new version for a process definition.
    
    This endpoint allows creating a new version of a process definition with specified
    changes. It supports incremental versioning (major, minor, patch) and tracking
    element-level changes.
    """
    try:
        version_manager = VersionManager(session)
        
        # Extract element changes to correct format if provided
        element_changes = None
        if data.element_changes:
            element_changes = [
                {
                    "element_id": change.element_id,
                    "element_type": change.element_type,
                    "change_type": ChangeType(change.change_type.value),
                    "previous_values": change.previous_values,
                    "new_values": change.new_values,
                }
                for change in data.element_changes
            ]
        
        # Convert branch type enum value
        branch_type = BranchType(data.branch_type.value)
        
        # Create new version
        version = await version_manager.create_new_version(
            process_definition_id=data.process_definition_id,
            author=data.author,
            bpmn_xml=data.bpmn_xml,
            variable_definitions=data.variable_definitions or [],
            commit_message=data.commit_message,
            parent_version_id=data.parent_version_id,
            version_increment=data.version_increment.value,
            element_changes=element_changes,
            branch_type=branch_type,
            branch_name=data.branch_name,
        )
        
        return {"data": version}
    except ValueError as e:
        logger.error(f"Error creating version: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating version: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/process/{process_id}",
    response_model=ApiResponse[VersionListResponse],
)
async def get_process_versions(
    process_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    """Get version history for a process definition.
    
    Returns a paginated list of versions for the specified process definition,
    ordered by creation date (newest first).
    """
    try:
        version_manager = VersionManager(session)
        versions = await version_manager.get_version_history(
            process_definition_id=process_id,
            limit=limit,
            offset=offset,
        )
        
        # Get total count for pagination
        total = await version_manager.get_version_count(process_id)
        
        return {
            "data": {
                "versions": versions,
                "total": total,
            }
        }
    except Exception as e:
        logger.error(f"Error getting versions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{version_id}",
    response_model=ApiResponse[VersionDetailResponse],
)
async def get_version(
    version_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get details of a specific version.
    
    Returns detailed information about a specific version, including its
    BPMN XML content, variable definitions, and element changes.
    """
    try:
        version_manager = VersionManager(session)
        version = await version_manager.get_version(version_id)
        
        if not version:
            raise HTTPException(status_code=404, detail="Version not found")
        
        # Get element changes for this version
        element_changes = await version_manager.get_version_element_changes(version_id)
        
        # Create response data
        response_data = {
            **version.__dict__,
            "element_changes": element_changes,
        }
        
        # Remove SQLAlchemy state
        if "_sa_instance_state" in response_data:
            del response_data["_sa_instance_state"]
            
        return {"data": response_data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting version: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/restore/{version_id}",
    response_model=ApiResponse[VersionResponse],
)
@log_error(logger)
async def restore_version(
    version_id: UUID,
    data: VersionBase = Body(...),
    session: AsyncSession = Depends(get_session),
):
    """Restore a previous version.
    
    Creates a new version based on the content of a previous version.
    This effectively reverts the process definition to a previous state
    while maintaining the version history.
    """
    try:
        version_manager = VersionManager(session)
        
        # Convert branch type enum value
        branch_type = BranchType(data.branch_type.value)
        
        # Restore version
        new_version = await version_manager.restore_version(
            version_id=version_id,
            author=data.author,
            commit_message=data.commit_message,
            branch_type=branch_type,
            branch_name=data.branch_name,
        )
        
        return {"data": new_version}
    except ValueError as e:
        logger.error(f"Error restoring version: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error restoring version: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) 