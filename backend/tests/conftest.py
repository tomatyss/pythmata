import asyncio
from pathlib import Path
from typing import AsyncGenerator, Optional

import httpx
import pytest
import redis.asyncio as redis
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from pythmata.core.config import (
    DatabaseSettings,
    ProcessSettings,
    RabbitMQSettings,
    RedisSettings,
    SecuritySettings,
    ServerSettings,
    Settings,
)
from pythmata.models.process import Base


@pytest.fixture(scope="function")
async def redis_connection(test_settings: Settings) -> AsyncGenerator[Redis, None]:
    """Create a Redis connection for testing."""
    connection = redis.from_url(
        str(test_settings.redis.url),
        encoding="utf-8",
        decode_responses=True,
        max_connections=test_settings.redis.pool_size,
    )

    try:
        await connection.ping()
        yield connection
    finally:
        await connection.flushdb()  # Clean up test data
        await connection.aclose()  # Close connection


@pytest.fixture(scope="function", autouse=True)
async def setup_database(test_settings: Settings):
    """Initialize and setup test database."""
    from pythmata.core.database import get_db, init_db

    # Initialize database
    init_db(test_settings)
    db = get_db()

    # Create tables
    await db.create_tables()

    yield

    # Cleanup
    await db.drop_tables()
    await db.close()


@pytest.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    from pythmata.core.database import get_db

    db = get_db()
    async with db.session() as session:
        yield session


@pytest.fixture
def test_data_dir() -> Path:
    """Returns the path to the test data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture(autouse=True)
def setup_test_data_dir(test_data_dir: Path):
    """Creates the test data directory if it doesn't exist."""
    test_data_dir.mkdir(parents=True, exist_ok=True)


@pytest.fixture
async def state_manager(test_settings: Settings, redis_connection: Redis):
    """Create a StateManager instance for testing."""
    from pythmata.core.state import StateManager

    manager = StateManager(test_settings)
    manager.redis = redis_connection  # Use the test Redis connection

    return manager


@pytest.fixture
def app(test_settings: Settings) -> FastAPI:
    """Create a FastAPI test application."""
    from pythmata.api.routes import router

    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
async def async_client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client."""
    async with AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Create test settings with Redis configuration."""
    return Settings(
        server=ServerSettings(host="localhost", port=8000, debug=True),
        database=DatabaseSettings(
            url="postgresql+asyncpg://pythmata:pythmata@localhost:5432/pythmata_test",
            pool_size=5,
            max_overflow=10,
        ),
        redis=RedisSettings(url="redis://localhost:6379/0", pool_size=10),
        rabbitmq=RabbitMQSettings(
            url="amqp://guest:guest@localhost:5672/",
            connection_attempts=3,
            retry_delay=1,
        ),
        security=SecuritySettings(
            secret_key="test-secret-key",
            algorithm="HS256",
            access_token_expire_minutes=30,
        ),
        process=ProcessSettings(
            script_timeout=30, max_instances=100, cleanup_interval=60
        ),
        _env_file=None,  # Disable environment file loading for tests
    )
