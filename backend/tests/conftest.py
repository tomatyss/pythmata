import asyncio
import pytest
from pathlib import Path
from typing import AsyncGenerator, Optional

import redis.asyncio as redis
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from pythmata.core.config import Settings, RedisSettings, ServerSettings, DatabaseSettings, RabbitMQSettings, SecuritySettings, ProcessSettings
from pythmata.models.process import Base

@pytest.fixture(scope="function")
def event_loop():
    """Create an instance of the default event loop for each test."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()
    asyncio.set_event_loop(None)

@pytest.fixture(scope="function")
async def redis_connection(test_settings: Settings, event_loop) -> AsyncGenerator[Redis, None]:
    """Create a Redis connection for testing."""
    connection = redis.from_url(
        str(test_settings.redis.url),
        encoding="utf-8",
        decode_responses=True,
        max_connections=test_settings.redis.pool_size
    )
    
    try:
        await connection.ping()
        yield connection
    finally:
        await connection.flushdb()  # Clean up test data
        await connection.aclose()   # Close connection

@pytest.fixture(scope="function")
async def engine(test_settings: Settings, event_loop):
    """Create a test database engine."""
    engine = create_async_engine(
        str(test_settings.database.url),  # Convert PostgresDsn to string
        poolclass=NullPool,
        echo=False
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Clean up
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with session_factory() as session:
        yield session
        await session.rollback()

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

@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Create test settings with Redis configuration."""
    return Settings(
        server=ServerSettings(
            host="localhost",
            port=8000,
            debug=True
        ),
        database=DatabaseSettings(
            url="postgresql+asyncpg://pythmata:pythmata@localhost:5432/pythmata_test",
            pool_size=5,
            max_overflow=10
        ),
        redis=RedisSettings(
            url="redis://localhost:6379/0",
            pool_size=10
        ),
        rabbitmq=RabbitMQSettings(
            url="amqp://guest:guest@localhost:5672/",
            connection_attempts=3,
            retry_delay=1
        ),
        security=SecuritySettings(
            secret_key="test-secret-key",
            algorithm="HS256",
            access_token_expire_minutes=30
        ),
        process=ProcessSettings(
            script_timeout=30,
            max_instances=100,
            cleanup_interval=60
        ),
        _env_file=None  # Disable environment file loading for tests
    )
