"""Tests for main application functionality."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi import FastAPI

from pythmata.core.config import (
    DatabaseSettings,
    ProcessSettings,
    RabbitMQSettings,
    RedisSettings,
    SecuritySettings,
    ServerSettings,
    Settings,
)
from pythmata.core.database import Database
from pythmata.core.events import EventBus
from pythmata.core.state import StateManager
from pythmata.main import handle_process_started, lifespan
from sqlalchemy.ext.asyncio import AsyncSession
from pythmata.models.process import ProcessDefinition as ProcessDefinitionModel


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock(spec=Settings)
    settings.server = ServerSettings(host="localhost", port=8000, debug=True)
    settings.database = DatabaseSettings(
        url="postgresql+asyncpg://user:pass@localhost/test",
        pool_size=5,
        max_overflow=10,
    )
    settings.redis = RedisSettings(url="redis://localhost:6379", pool_size=10)
    settings.rabbitmq = RabbitMQSettings(
        url="amqp://guest:guest@localhost:5672/",
        connection_attempts=3,
        retry_delay=5,
    )
    settings.security = SecuritySettings(
        secret_key="test_secret",
        algorithm="HS256",
        access_token_expire_minutes=30,
    )
    settings.process = ProcessSettings(
        script_timeout=30,
        max_instances=100,
        cleanup_interval=300,
    )
    return settings


@pytest.fixture
def mock_db():
    """Create a mock database."""
    with patch("pythmata.main.get_db") as mock_get_db:
        db = AsyncMock(spec=Database)
        mock_get_db.return_value = db
        yield db


@pytest.fixture
def mock_event_bus():
    """Create a mock event bus."""
    with patch("pythmata.main.EventBus") as mock_event_bus_cls:
        event_bus = AsyncMock(spec=EventBus)
        mock_event_bus_cls.return_value = event_bus
        yield event_bus


@pytest.fixture
def mock_state_manager():
    """Create a mock state manager."""
    with patch("pythmata.main.StateManager") as mock_state_manager_cls:
        state_manager = AsyncMock(spec=StateManager)
        mock_state_manager_cls.return_value = state_manager
        yield state_manager


@pytest.fixture
def mock_settings_factory(mock_settings):
    """Create a mock settings factory."""
    with patch("pythmata.main.Settings", return_value=mock_settings):
        yield mock_settings


@pytest.mark.asyncio
async def test_lifespan_connects_services(
    mock_db, mock_event_bus, mock_state_manager, mock_settings_factory
):
    """Test that lifespan properly connects all services."""
    app = FastAPI()

    # Create lifespan context
    async with lifespan(app):
        # Verify all services were connected
        mock_db.connect.assert_called_once()
        mock_event_bus.connect.assert_called_once()
        mock_state_manager.connect.assert_called_once()

        # Verify services are stored in app state
        assert app.state.event_bus == mock_event_bus
        assert app.state.state_manager == mock_state_manager

    # Verify proper cleanup
    mock_db.disconnect.assert_called_once()
    mock_event_bus.disconnect.assert_called_once()
    mock_state_manager.disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_lifespan_handles_connection_errors(
    mock_db, mock_event_bus, mock_state_manager, mock_settings_factory
):
    """Test that lifespan properly handles connection errors."""
    app = FastAPI()

    # Simulate database connection error
    error = RuntimeError("Database connection failed")
    mock_db.connect.side_effect = error

    # Verify that connection error is propagated
    with pytest.raises(RuntimeError) as exc_info:
        async with lifespan(app):
            pass
    assert str(exc_info.value) == "Database connection failed"

    # Verify cleanup is still performed
    mock_event_bus.disconnect.assert_not_called()
    mock_state_manager.disconnect.assert_not_called()


@pytest.mark.asyncio
async def test_lifespan_handles_disconnection_errors(
    mock_db, mock_event_bus, mock_state_manager, mock_settings_factory
):
    """Test that lifespan properly handles disconnection errors."""
    app = FastAPI()

    # Simulate database disconnection error
    error = RuntimeError("Database disconnection failed")
    mock_db.disconnect.side_effect = error

    # Verify that other services are still disconnected even if one fails
    with pytest.raises(RuntimeError) as exc_info:
        async with lifespan(app):
            pass
    assert str(exc_info.value) == "Database disconnection failed"

    # Verify all disconnect attempts were made
    mock_db.disconnect.assert_called_once()
    mock_event_bus.disconnect.assert_called_once()
    mock_state_manager.disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_handle_process_started(
    session: AsyncSession, state_manager: StateManager, test_settings: Settings
):
    """Test process.started event handler."""
    # Create a test process definition
    definition = ProcessDefinitionModel(
        name="Test Process",
        bpmn_xml="""<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" xmlns:di="http://www.omg.org/spec/DD/20100524/DI" id="Definitions_1" targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="Process_1" isExecutable="true">
    <bpmn:startEvent id="Start_1">
      <bpmn:outgoing>Flow_1</bpmn:outgoing>
    </bpmn:startEvent>
    <bpmn:task id="Task_1">
      <bpmn:incoming>Flow_1</bpmn:incoming>
      <bpmn:outgoing>Flow_2</bpmn:outgoing>
    </bpmn:task>
    <bpmn:endEvent id="End_1">
      <bpmn:incoming>Flow_2</bpmn:incoming>
    </bpmn:endEvent>
    <bpmn:sequenceFlow id="Flow_1" sourceRef="Start_1" targetRef="Task_1" />
    <bpmn:sequenceFlow id="Flow_2" sourceRef="Task_1" targetRef="End_1" />
  </bpmn:process>
</bpmn:definitions>""",
        version=1,
    )
    session.add(definition)
    await session.commit()
    await session.refresh(definition)

    # Test data
    instance_id = str(UUID("12345678-1234-5678-1234-567812345678"))
    definition_id = str(definition.id)

    # Call handler with test settings
    with patch("pythmata.main.Settings", return_value=test_settings):
        await handle_process_started(
            {
                "instance_id": instance_id,
                "definition_id": definition_id,
            }
        )

    # Verify token was created
    tokens = await state_manager.get_token_positions(instance_id)
    assert len(tokens) == 1
    assert tokens[0]["node_id"] == "Start_1"
