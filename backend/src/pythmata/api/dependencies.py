from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from pythmata.core.config import get_settings
from pythmata.core.database import get_db
from pythmata.core.state import StateManager


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
