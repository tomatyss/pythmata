"""FastAPI dependencies."""

from typing import AsyncGenerator, Optional

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from pythmata.core.config import get_settings
from pythmata.core.database import get_db
from pythmata.core.events import EventBus
from pythmata.core.state import StateManager
from pythmata.core.engine.executor import ProcessExecutor
from pythmata.core.engine.instance import ProcessInstanceManager

_event_bus: Optional[EventBus] = None
_instance_manager: Optional[ProcessInstanceManager] = None


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session."""
    db = get_db()
    async with db.session() as session:
        yield session


async def get_state_manager() -> AsyncGenerator[StateManager, None]:
    """Get a StateManager instance."""
    settings = get_settings()
    manager = StateManager(settings)
    await manager.connect()
    try:
        yield manager
    finally:
        await manager.disconnect()


async def get_event_bus() -> AsyncGenerator[EventBus, None]:
    """Get the EventBus instance."""
    global _event_bus
    if not _event_bus:
        settings = get_settings()
        _event_bus = EventBus(settings)
        await _event_bus.connect()
    try:
        yield _event_bus
    finally:
        if _event_bus:
            await _event_bus.disconnect()
            _event_bus = None


async def get_instance_manager(
    state_manager: StateManager = Depends(get_state_manager),
    event_bus: EventBus = Depends(get_event_bus),
    session: AsyncSession = Depends(get_session),
) -> AsyncGenerator[ProcessInstanceManager, None]:
    """Get the ProcessInstanceManager instance."""
    global _instance_manager
    if not _instance_manager:
        # Create ProcessExecutor first
        executor = ProcessExecutor(state_manager=state_manager)
        
        _instance_manager = ProcessInstanceManager(
            session=session,
            executor=executor,
            state_manager=state_manager,
        )
    try:
        yield _instance_manager
    finally:
        _instance_manager = None
