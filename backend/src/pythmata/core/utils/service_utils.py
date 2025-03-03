"""Service management utilities."""

from contextlib import asynccontextmanager

from pythmata.core.config import Settings
from pythmata.core.database import get_db
from pythmata.core.events import EventBus
from pythmata.core.state import StateManager
from pythmata.utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def get_process_services():
    """Context manager for process execution services.

    Provides centralized initialization and cleanup of services required for process execution.
    This reduces code duplication and ensures proper resource management.

    Yields:
        Tuple containing (settings, state_manager, db, event_bus)
    """
    settings = Settings()
    state_manager = StateManager(settings)
    db = get_db()
    event_bus = EventBus(settings)

    # Connect services
    await state_manager.connect()
    if not db.is_connected:
        logger.info("Database not connected, connecting...")
        await db.connect()
        logger.info("Database connected successfully")
    await event_bus.connect()

    try:
        yield (settings, state_manager, db, event_bus)
    finally:
        # Ensure services are disconnected even if an error occurs
        await event_bus.disconnect()
        await state_manager.disconnect()
