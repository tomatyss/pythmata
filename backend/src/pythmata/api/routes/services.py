"""API routes for service tasks."""

from typing import Dict, List

from fastapi import APIRouter, HTTPException

from pythmata.core.services.registry import get_service_task_registry
from pythmata.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/services", tags=["services"])


@router.get("/tasks", response_model=List[Dict])
async def list_service_tasks():
    """
    List all available service tasks.

    Returns:
        List of service task information including name, description, and properties
    """
    try:
        registry = get_service_task_registry()
        return registry.list_tasks()
    except Exception as e:
        logger.error(f"Failed to list service tasks: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to list service tasks: {str(e)}"
        )
