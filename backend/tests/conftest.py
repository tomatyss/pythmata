"""Test configuration and shared fixtures."""

import os
import subprocess
from pathlib import Path
from typing import AsyncGenerator

import pytest
import redis.asyncio as redis
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from pytest import Config
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from pythmata.api.dependencies import (
    get_event_bus,
    get_instance_manager,
    get_session,
    get_state_manager,
)
from pythmata.core.config import (
    DatabaseSettings,
    ProcessSettings,
    RabbitMQSettings,
    RedisSettings,
    SecuritySettings,
    ServerSettings,
    Settings,
    get_settings,
)
from pythmata.core.database import get_db, init_db
from pythmata.core.engine.expressions import ExpressionEvaluator
from pythmata.core.events import EventBus
from pythmata.core.state import StateManager
from tests.core.testing.constants import (
    DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES,
    DEFAULT_ALGORITHM,
    DEFAULT_CLEANUP_INTERVAL,
    DEFAULT_DB_MAX_OVERFLOW,
    DEFAULT_DB_POOL_SIZE,
    DEFAULT_DEBUG,
    DEFAULT_MAX_INSTANCES,
    DEFAULT_RABBITMQ_CONNECTION_ATTEMPTS,
    DEFAULT_RABBITMQ_RETRY_DELAY,
    DEFAULT_RABBITMQ_URL,
    DEFAULT_REDIS_POOL_SIZE,
    DEFAULT_REDIS_URL,
    DEFAULT_SCRIPT_TIMEOUT,
    DEFAULT_SECRET_KEY,
    DEFAULT_SERVER_HOST,
    DEFAULT_SERVER_PORT,
)


def pytest_configure(config: Config) -> None:
    """Set up test environment before test collection.

    Args:
        config: Pytest configuration object

    Raises:
        SystemExit: If database setup fails
    """
    setup_script = Path(__file__).parent.parent / "scripts" / "setup_test_db.py"
    try:
        subprocess.run([str(setup_script)], check=True)
    except subprocess.CalledProcessError as e:
        pytest.exit(f"Failed to set up test database: {e}")


# ============================================================================
# Core Fixtures
# ============================================================================


@pytest.fixture
def expression_evaluator() -> ExpressionEvaluator:
    """Create an expression evaluator for tests.

    Returns:
        ExpressionEvaluator: Instance for evaluating expressions in tests
    """
    return ExpressionEvaluator()


@pytest.fixture(scope="function")
async def redis_connection(test_settings: Settings) -> AsyncGenerator[Redis, None]:
    """Create a Redis connection for testing.

    Args:
        test_settings: Test configuration settings

    Yields:
        Redis: Connected Redis client
    """
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
        try:
            await connection.flushdb()  # Clean up test data
            await connection.aclose()  # Close connection
        except Exception:
            # Ignore cleanup errors since the event loop might be closed
            pass


@pytest.fixture(scope="function", autouse=True)
async def setup_database(test_settings: Settings):
    """Initialize and setup test database.

    Args:
        test_settings: Test configuration settings
    """
    init_db(test_settings)
    db = get_db()

    try:
        await db.drop_tables()
        await db.create_tables()
        yield
    finally:
        try:
            await db.drop_tables()
            await db.close()
        except Exception:
            # Ignore cleanup errors since the event loop might be closed
            pass


@pytest.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session.

    Yields:
        AsyncSession: Database session for test use
    """
    db = get_db()
    async with db.session() as session:
        yield session


@pytest.fixture
def test_data_dir() -> Path:
    """Get the path to the test data directory.

    Returns:
        Path: Path to test data directory
    """
    return Path(__file__).parent / "data"


@pytest.fixture(autouse=True)
def setup_test_data_dir(test_data_dir: Path):
    """Create the test data directory if it doesn't exist.

    Args:
        test_data_dir: Path to test data directory
    """
    test_data_dir.mkdir(parents=True, exist_ok=True)


# ============================================================================
# Application Fixtures
# ============================================================================


@pytest.fixture
async def state_manager(test_settings: Settings) -> AsyncGenerator:
    """Create a StateManager instance for testing.

    Args:
        test_settings: Test configuration settings

    Yields:
        StateManager: Configured state manager instance
    """
    manager = StateManager(test_settings)
    try:
        await manager.connect()
        yield manager
    finally:
        try:
            await manager.disconnect()
        except Exception:
            # Ignore cleanup errors since the event loop might be closed
            pass


@pytest.fixture
async def event_bus(test_settings: Settings) -> AsyncGenerator[EventBus, None]:
    """Create an EventBus instance for testing.

    Args:
        test_settings: Test configuration settings

    Yields:
        EventBus: Configured event bus instance
    """
    bus = EventBus(test_settings)
    try:
        await bus.connect()
        yield bus
    finally:
        try:
            await bus.disconnect()
        except Exception:
            # Ignore cleanup errors since the event loop might be closed
            pass


@pytest.fixture
def app(test_settings: Settings, state_manager, event_bus) -> FastAPI:
    """Create a FastAPI test application.

    Args:
        test_settings: Test configuration settings
        state_manager: State manager instance
        event_bus: Event bus instance

    Returns:
        FastAPI: Configured test application
    """
    from pythmata.api.routes import router

    app = FastAPI()
    app.include_router(router)

    # Override production dependencies with test ones
    async def get_test_state_manager():
        yield state_manager

    async def get_test_session():
        async with get_db().session() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                try:
                    await session.close()
                except Exception:
                    # Ignore cleanup errors since the event loop might be closed
                    pass

    async def get_test_event_bus():
        yield event_bus

    # Create a test instance manager dependency
    async def get_test_instance_manager(
        state_manager: StateManager = Depends(get_test_state_manager),
        event_bus: EventBus = Depends(get_test_event_bus),
        session: AsyncSession = Depends(get_test_session),
    ):
        from pythmata.core.engine.executor import ProcessExecutor
        from pythmata.core.engine.instance import ProcessInstanceManager

        executor = ProcessExecutor(state_manager=state_manager)
        instance_manager = ProcessInstanceManager(
            session=session,
            executor=executor,
            state_manager=state_manager,
        )
        yield instance_manager

    # Override dependencies
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_state_manager] = get_test_state_manager
    app.dependency_overrides[get_session] = get_test_session
    app.dependency_overrides[get_event_bus] = get_test_event_bus
    app.dependency_overrides[get_instance_manager] = get_test_instance_manager

    return app


@pytest.fixture
async def async_client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client.

    Args:
        app: FastAPI test application

    Yields:
        AsyncClient: Configured test client
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Create test settings with environment-aware configuration.

    Returns:
        Settings: Test configuration settings
    """
    from pythmata.core.testing.config import get_db_url

    db_url = get_db_url(for_asyncpg=False)  # Use SQLAlchemy format

    return Settings(
        server=ServerSettings(
            host=os.getenv("SERVER_HOST", DEFAULT_SERVER_HOST),
            port=int(os.getenv("SERVER_PORT", str(DEFAULT_SERVER_PORT))),
            debug=os.getenv("DEBUG", str(DEFAULT_DEBUG)).lower() == "true",
        ),
        database=DatabaseSettings(
            url=db_url,
            pool_size=int(os.getenv("DB_POOL_SIZE", str(DEFAULT_DB_POOL_SIZE))),
            max_overflow=int(
                os.getenv("DB_MAX_OVERFLOW", str(DEFAULT_DB_MAX_OVERFLOW))
            ),
        ),
        redis=RedisSettings(
            url=os.getenv(DEFAULT_REDIS_URL, "redis://localhost:6379/0"),
            pool_size=int(os.getenv("REDIS_POOL_SIZE", str(DEFAULT_REDIS_POOL_SIZE))),
        ),
        rabbitmq=RabbitMQSettings(
            url=os.getenv(DEFAULT_RABBITMQ_URL, "amqp://guest:guest@localhost:5672/"),
            connection_attempts=int(
                os.getenv(
                    "RABBITMQ_CONNECTION_ATTEMPTS",
                    str(DEFAULT_RABBITMQ_CONNECTION_ATTEMPTS),
                )
            ),
            retry_delay=int(
                os.getenv("RABBITMQ_RETRY_DELAY", str(DEFAULT_RABBITMQ_RETRY_DELAY))
            ),
        ),
        security=SecuritySettings(
            secret_key=os.getenv("SECRET_KEY", DEFAULT_SECRET_KEY),
            algorithm=os.getenv("ALGORITHM", DEFAULT_ALGORITHM),
            access_token_expire_minutes=int(
                os.getenv(
                    "ACCESS_TOKEN_EXPIRE_MINUTES",
                    str(DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES),
                )
            ),
        ),
        process=ProcessSettings(
            script_timeout=int(
                os.getenv("SCRIPT_TIMEOUT", str(DEFAULT_SCRIPT_TIMEOUT))
            ),
            max_instances=int(os.getenv("MAX_INSTANCES", str(DEFAULT_MAX_INSTANCES))),
            cleanup_interval=int(
                os.getenv("CLEANUP_INTERVAL", str(DEFAULT_CLEANUP_INTERVAL))
            ),
        ),
        _env_file=None,  # Disable environment file loading for tests
    )
