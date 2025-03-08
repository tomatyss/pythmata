"""WebSocket routes for process instance updates."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pythmata.api.dependencies import get_session
from pythmata.api.websocket.manager import manager
from pythmata.models.process import ProcessInstance
from pythmata.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


async def verify_instance(
    session: AsyncSession, instance_id: UUID
) -> Optional[ProcessInstance]:
    """
    Verify that a process instance exists.

    Args:
        session: Database session
        instance_id: ID of the process instance

    Returns:
        ProcessInstance if found, None otherwise
    """
    result = await session.execute(
        select(ProcessInstance).where(ProcessInstance.id == instance_id)
    )
    return result.scalar_one_or_none()


@router.websocket("/instances/{instance_id}")
async def process_websocket(
    websocket: WebSocket,
    instance_id: UUID,
    session: AsyncSession = get_session,
):
    """
    WebSocket endpoint for process instance updates.

    Args:
        websocket: The WebSocket connection
        instance_id: ID of the process instance to subscribe to
        session: Database session
    """
    # Verify instance exists
    instance = await verify_instance(session, instance_id)
    if not instance:
        await websocket.close(code=4004, reason="Process instance not found")
        return

    try:
        # Accept connection and add to manager
        await manager.connect(websocket, instance_id)
        logger.info(f"WebSocket connection established for instance {instance_id}")

        # Keep connection alive and handle client messages if needed
        while True:
            try:
                # Wait for client messages (can be used for ping/pong)
                data = await websocket.receive_text()
            except WebSocketDisconnect:
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected from instance {instance_id}")
    except Exception as e:
        logger.error(f"Error in WebSocket connection: {e}")
    finally:
        # Clean up connection
        manager.disconnect(websocket, instance_id)
