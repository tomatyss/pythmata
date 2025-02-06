from sqlalchemy.ext.asyncio import AsyncSession

from pythmata.core.database import get_db


async def get_session() -> AsyncSession:
    """Get database session."""
    db = get_db()
    async with db.session() as session:
        yield session
