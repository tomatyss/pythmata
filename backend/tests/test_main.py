"""Tests for main application functionality."""

from uuid import UUID

import pytest
from fastapi import FastAPI

from pythmata.core.config import DatabaseSettings, Settings, get_settings
from pythmata.main import handle_process_started, lifespan
from pythmata.models.process import ProcessDefinition as ProcessDefinitionModel
from tests.data.process_samples import SIMPLE_PROCESS_XML


@pytest.mark.asyncio
async def test_lifespan_connects_services(app: FastAPI, test_settings):
    """Test that lifespan properly connects all services."""
    async with lifespan(app):
        # Verify services are stored in app state
        assert hasattr(app.state, "event_bus")
        assert hasattr(app.state, "state_manager")

        # Verify services are connected
        assert await app.state.event_bus.is_connected()
        assert await app.state.state_manager.is_connected()

    # After context exit, services should be disconnected
    assert not await app.state.event_bus.is_connected()
    assert not await app.state.state_manager.is_connected()


@pytest.mark.asyncio
async def test_lifespan_handles_connection_errors(app: FastAPI, test_settings: Settings):
    """Test that lifespan properly handles connection errors."""
    # Create invalid settings
    invalid_settings = Settings(
        server=test_settings.server,
        database=DatabaseSettings(
            url="postgresql+asyncpg://invalid:invalid@localhost/invalid",
            pool_size=test_settings.database.pool_size,
            max_overflow=test_settings.database.max_overflow
        ),
        redis=test_settings.redis,
        rabbitmq=test_settings.rabbitmq,
        security=test_settings.security,
        process=test_settings.process
    )

    # Override get_settings to return invalid settings
    app.dependency_overrides[get_settings] = lambda: invalid_settings

    with pytest.raises(RuntimeError) as exc_info:
        async with lifespan(app):
            pass
    assert "connection failed" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_lifespan_handles_disconnection_errors(app: FastAPI, test_settings: Settings):
    """Test that lifespan properly handles disconnection errors."""
    # Ensure test_settings is used
    app.dependency_overrides[get_settings] = lambda: test_settings

    async with lifespan(app):
        # Simulate disconnection error by corrupting the connection
        app.state.event_bus._connection = None

    # Test should complete without raising an exception
    # as disconnect errors should be handled gracefully


@pytest.mark.asyncio
async def test_handle_process_started(
    session, state_manager, test_settings: Settings, app: FastAPI
):
    """Test process.started event handler."""
    # Ensure test_settings is used
    app.dependency_overrides[get_settings] = lambda: test_settings

    # Create a test process definition
    definition = ProcessDefinitionModel(
        name="Test Process",
        bpmn_xml=SIMPLE_PROCESS_XML,
        version=1,
    )
    session.add(definition)
    await session.commit()
    await session.refresh(definition)

    # Test data
    instance_id = str(UUID("12345678-1234-5678-1234-567812345678"))
    definition_id = str(definition.id)

    # Call handler
    await handle_process_started(
        {
            "instance_id": instance_id,
            "definition_id": definition_id,
        }
    )

    # Verify token was created using the existing state_manager
    tokens = await state_manager.get_token_positions(instance_id)
    assert len(tokens) == 1
    # This matches the ID in SIMPLE_PROCESS_XML
    assert tokens[0]["node_id"] == "StartEvent_1"
