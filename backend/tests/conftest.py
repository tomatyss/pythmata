import os
import subprocess
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional

import pytest
from pytest import Config
from pythmata.api.schemas import ProcessVariableValue
from pythmata.core.engine.executor import ProcessExecutor
from pythmata.core.engine.expressions import ExpressionEvaluator
from pythmata.core.engine.saga import ParallelStepGroup, SagaOrchestrator, SagaStatus
from pythmata.core.engine.token import Token
from pythmata.core.state import StateManager
from pythmata.core.types import Event, EventType, Gateway, GatewayType, Task
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
    setup_script = Path(__file__).parent.parent / \
        "scripts" / "setup_test_db.py"
    try:
        subprocess.run([str(setup_script)], check=True)
    except subprocess.CalledProcessError as e:
        pytest.exit(f"Failed to set up test database: {e}")


@pytest.fixture
def expression_evaluator() -> ExpressionEvaluator:
    """Create an expression evaluator for tests."""
    return ExpressionEvaluator()


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


# Test helpers and assertions
async def assert_token_state(state_manager: StateManager, instance_id: str, expected_count: int, expected_node_ids: Optional[List[str]] = None):
    """Assert the token state for a process instance."""
    tokens = await state_manager.get_token_positions(instance_id)
    assert len(
        tokens) == expected_count, f"Expected {expected_count} tokens, got {len(tokens)}"
    if expected_node_ids:
        token_node_ids = {t["node_id"] for t in tokens}
        assert token_node_ids == set(
            expected_node_ids), f"Expected tokens at {expected_node_ids}, got {token_node_ids}"


async def assert_saga_state(
    saga: SagaOrchestrator,
    expected_status: SagaStatus,
    expected_completed_steps: int,
    compensation_required: bool = False
):
    """Assert the state of a saga orchestrator."""
    assert saga.status == expected_status, f"Expected saga status {expected_status}, got {saga.status}"
    assert len(
        saga.completed_steps) == expected_completed_steps, f"Expected {expected_completed_steps} completed steps, got {len(saga.completed_steps)}"
    assert saga.compensation_required == compensation_required, f"Expected compensation_required={compensation_required}, got {saga.compensation_required}"


async def assert_process_variables(state_manager: StateManager, instance_id: str, expected_variables: Dict[str, ProcessVariableValue]):
    """Assert process variables match expected values."""
    for name, expected in expected_variables.items():
        actual = await state_manager.get_variable(instance_id, name)
        assert actual.type == expected.type, f"Variable {name} type mismatch"
        assert actual.value == expected.value, f"Variable {name} value mismatch"


class BaseSagaTest:
    """Base class for saga tests providing common setup and utilities."""

    def create_basic_saga(self, saga_id: str = "Saga_1", instance_id: str = "test_instance") -> SagaOrchestrator:
        """Create a basic saga with default configuration."""
        return SagaOrchestrator(saga_id, instance_id)

    async def setup_sequential_steps(self, saga: SagaOrchestrator, num_steps: int = 2, fail_step: Optional[int] = None) -> None:
        """Add sequential steps to a saga, optionally making one step fail."""
        for i in range(num_steps):
            data = {"task": i + 1}
            if fail_step is not None and i == fail_step:
                data["should_fail"] = True
            await saga.add_step(
                action_id=f"Task_{i+1}",
                compensation_id=f"Comp_{i+1}",
                data=data
            )

    async def setup_parallel_steps(self, saga: SagaOrchestrator, num_steps: int = 2, sleep_time: float = 0.1) -> ParallelStepGroup:
        """Create a parallel step group with specified number of steps."""
        group = await saga.create_parallel_group()
        for i in range(num_steps):
            await group.add_step(
                action_id=f"Task_{i+1}",
                compensation_id=f"Comp_{i+1}",
                data={"task": i + 1, "sleep": sleep_time}
            )
        return group

# Base test class for engine tests


class BaseEngineTest:
    """Base class for engine tests providing common setup and utilities."""

    @pytest.fixture(autouse=True)
    async def setup_test(self, state_manager: StateManager):
        """Setup test environment with state manager."""
        self.state_manager = state_manager
        self.executor = ProcessExecutor(state_manager)
        yield

    def create_sequence_flow(self, start_id: str = "Start_1", task_id: str = "Task_1", end_id: str = "End_1") -> dict:
        """Create a simple sequence flow process graph."""
        return {
            "nodes": [
                Event(id=start_id, type="event", event_type=EventType.START,
                      outgoing=[f"Flow_{start_id}_to_{task_id}"]),
                Task(id=task_id, type="task", incoming=[
                     f"Flow_{start_id}_to_{task_id}"], outgoing=[f"Flow_{task_id}_to_{end_id}"]),
                Event(id=end_id, type="event", event_type=EventType.END,
                      incoming=[f"Flow_{task_id}_to_{end_id}"]),
            ],
            "flows": [
                {"id": f"Flow_{start_id}_to_{task_id}",
                    "source_ref": start_id, "target_ref": task_id},
                {"id": f"Flow_{task_id}_to_{end_id}",
                    "source_ref": task_id, "target_ref": end_id},
            ],
        }

    def create_parallel_flow(self, tasks: List[str] = None) -> dict:
        """Create a parallel gateway process graph."""
        if not tasks:
            tasks = ["Task_1", "Task_2"]

        start_id = "Start_1"
        split_gateway_id = "Gateway_1"
        join_gateway_id = "Gateway_2"
        end_id = "End_1"

        nodes = [
            Event(id=start_id, type="event", event_type=EventType.START,
                  outgoing=[f"Flow_to_split"]),
            Gateway(id=split_gateway_id, type="gateway", gateway_type=GatewayType.PARALLEL,
                    incoming=[f"Flow_to_split"], outgoing=[f"Flow_to_{task}" for task in tasks]),
        ]

        flows = [{"id": "Flow_to_split", "source_ref": start_id,
                  "target_ref": split_gateway_id}]

        # Add task nodes
        for task_id in tasks:
            nodes.append(Task(id=task_id, type="task",
                              incoming=[f"Flow_to_{task_id}"],
                              outgoing=[f"Flow_from_{task_id}"]))
            flows.append({"id": f"Flow_to_{task_id}",
                         "source_ref": split_gateway_id, "target_ref": task_id})
            flows.append({"id": f"Flow_from_{task_id}",
                         "source_ref": task_id, "target_ref": join_gateway_id})

        # Add join gateway and end event
        nodes.extend([
            Gateway(id=join_gateway_id, type="gateway", gateway_type=GatewayType.PARALLEL,
                    incoming=[f"Flow_from_{task}" for task in tasks], outgoing=["Flow_to_end"]),
            Event(id=end_id, type="event", event_type=EventType.END,
                  incoming=["Flow_to_end"]),
        ])
        flows.append(
            {"id": "Flow_to_end", "source_ref": join_gateway_id, "target_ref": end_id})

        return {"nodes": nodes, "flows": flows}

    def create_exclusive_flow(self, conditions: Dict[str, str]) -> dict:
        """Create an exclusive gateway process graph with conditions."""
        start_id = "Start_1"
        gateway_id = "Gateway_1"
        end_id = "End_1"

        nodes = [
            Event(id=start_id, type="event", event_type=EventType.START,
                  outgoing=["Flow_to_gateway"]),
            Gateway(id=gateway_id, type="gateway", gateway_type=GatewayType.EXCLUSIVE,
                    incoming=["Flow_to_gateway"], outgoing=[f"Flow_to_{task}" for task in conditions.keys()]),
        ]

        flows = [{"id": "Flow_to_gateway",
                  "source_ref": start_id, "target_ref": gateway_id}]

        # Add conditional paths
        for task_id, condition in conditions.items():
            nodes.append(Task(id=task_id, type="task",
                              incoming=[f"Flow_to_{task_id}"],
                              outgoing=[f"Flow_from_{task_id}"]))
            flows.extend([
                {"id": f"Flow_to_{task_id}", "source_ref": gateway_id, "target_ref": task_id,
                 "condition_expression": condition},
                {"id": f"Flow_from_{task_id}",
                    "source_ref": task_id, "target_ref": end_id},
            ])

        nodes.append(Event(id=end_id, type="event", event_type=EventType.END,
                           incoming=[f"Flow_from_{task}" for task in conditions.keys()]))

        return {"nodes": nodes, "flows": flows}

    def create_subprocess_flow(self, subprocess_id: str = "Subprocess_1", next_task_id: str = "Task_1") -> dict:
        """Create a process graph with a subprocess."""
        start_id = "Start_1"
        end_id = "End_1"

        return {
            "nodes": [
                Event(id=start_id, type="event",
                      event_type=EventType.START, outgoing=["Flow_1"]),
                Task(id=subprocess_id, type="task", incoming=["Flow_1"], outgoing=["Flow_2"],
                     extensions={"subprocess": True}),
                Task(id=next_task_id, type="task", incoming=[
                     "Flow_2"], outgoing=["Flow_3"]),
                Event(id=end_id, type="event",
                      event_type=EventType.END, incoming=["Flow_3"]),
            ],
            "flows": [
                {"id": "Flow_1", "source_ref": start_id,
                    "target_ref": subprocess_id},
                {"id": "Flow_2", "source_ref": subprocess_id,
                    "target_ref": next_task_id},
                {"id": "Flow_3", "source_ref": next_task_id, "target_ref": end_id},
            ],
        }

    def create_multi_instance_flow(self, activity_id: str = "Activity_1", next_task_id: str = "Task_1") -> dict:
        """Create a process graph with a multi-instance activity."""
        start_id = "Start_1"
        end_id = "End_1"

        return {
            "nodes": [
                Event(id=start_id, type="event",
                      event_type=EventType.START, outgoing=["Flow_1"]),
                Task(id=activity_id, type="task", incoming=["Flow_1"], outgoing=["Flow_2"],
                     extensions={"multi_instance": True}),
                Task(id=next_task_id, type="task", incoming=[
                     "Flow_2"], outgoing=["Flow_3"]),
                Event(id=end_id, type="event",
                      event_type=EventType.END, incoming=["Flow_3"]),
            ],
            "flows": [
                {"id": "Flow_1", "source_ref": start_id, "target_ref": activity_id},
                {"id": "Flow_2", "source_ref": activity_id,
                    "target_ref": next_task_id},
                {"id": "Flow_3", "source_ref": next_task_id, "target_ref": end_id},
            ],
        }

    async def setup_multi_instance_token(self, instance_id: str, activity_id: str, collection_data: List[str], is_parallel: bool = True) -> Token:
        """Helper to set up a multi-instance activity token with collection data."""
        token = await self.executor.create_initial_token(instance_id, activity_id)
        token.data["collection"] = collection_data
        token.data["is_parallel"] = is_parallel
        return token


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