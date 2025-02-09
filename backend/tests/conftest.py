import os
import subprocess
from pathlib import Path
from typing import AsyncGenerator

import pytest
from pytest import Config
from pythmata.core.state import StateManager
import redis.asyncio as redis
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from pythmata.core.database import get_db, init_db
from pythmata.api.dependencies import get_session, get_state_manager 
from pythmata.core.config import (
    DatabaseSettings,
    ProcessSettings,
    RabbitMQSettings,
    RedisSettings,
    SecuritySettings,
    ServerSettings,
    Settings,
)


def pytest_configure(config: Config) -> None:
    """Set up test environment before test collection."""
    # Run database setup script
    setup_script = Path(__file__).parent.parent / "scripts" / "setup_test_db.py"
    try:
        subprocess.run([str(setup_script)], check=True)
    except subprocess.CalledProcessError as e:
        pytest.exit(f"Failed to set up test database: {e}")

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
async def state_manager(test_settings: Settings) -> AsyncGenerator:
    """Create a StateManager instance for testing."""
    manager = StateManager(test_settings)
    await manager.connect()  # Connect to Redis

    yield manager

    await manager.disconnect()  # Clean up


@pytest.fixture
def app(test_settings: Settings, state_manager) -> FastAPI:
    """Create a FastAPI test application."""
    from pythmata.api.routes import router

    app = FastAPI()
    app.include_router(router)

    # Override production dependencies with test ones
    async def get_test_state_manager():
        yield state_manager

    async def get_test_session():
        db = get_db()
        async with db.session() as session:
            yield session

    app.dependency_overrides[get_state_manager] = get_test_state_manager
    app.dependency_overrides[get_session] = get_test_session

    return app


@pytest.fixture
async def async_client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Create test settings with environment-aware configuration."""
    from pythmata.core.testing.config import (
        get_db_url,
        REDIS_URL,
        RABBITMQ_URL,
    )

    db_url = get_db_url(for_asyncpg=False)  # Use SQLAlchemy format

    return Settings(
        server=ServerSettings(
            host=os.getenv("SERVER_HOST", "localhost"),
            port=int(os.getenv("SERVER_PORT", "8000")),
            debug=os.getenv("DEBUG", "true").lower() == "true"
        ),
        database=DatabaseSettings(
            url=db_url,
            pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
        ),
        redis=RedisSettings(
            url=REDIS_URL,
            pool_size=int(os.getenv("REDIS_POOL_SIZE", "10")),
        ),
        rabbitmq=RabbitMQSettings(
            url=RABBITMQ_URL,
            connection_attempts=int(os.getenv("RABBITMQ_CONNECTION_ATTEMPTS", "3")),
            retry_delay=int(os.getenv("RABBITMQ_RETRY_DELAY", "1")),
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
