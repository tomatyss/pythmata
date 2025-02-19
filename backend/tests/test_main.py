"""Tests for main application functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pythmata.core.types import Event, EventType
from pythmata.main import app, handle_process_started
from pythmata.models.process import ProcessDefinition as ProcessDefinitionModel


@pytest.mark.asyncio
async def test_lifespan():
    """Test application lifespan (startup and shutdown)."""
    mock_event_bus = AsyncMock()
    mock_state_manager = AsyncMock()
    mock_settings = AsyncMock()
    mock_db = AsyncMock()

    with (
        patch("pythmata.main.EventBus", return_value=mock_event_bus),
        patch("pythmata.main.StateManager", return_value=mock_state_manager),
        patch("pythmata.main.Settings", return_value=mock_settings),
        patch("pythmata.main.get_db", return_value=mock_db),
        patch("pythmata.main.init_db"),
    ):
        # Create a lifespan context
        async with app.router.lifespan_context(app) as _:
            # Verify startup
            assert mock_event_bus.connect.called
            assert mock_state_manager.connect.called
            assert mock_db.connect.called
            assert mock_event_bus.subscribe.called

            # Test the application works
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/health")
                assert response.status_code == 200

        # Verify shutdown after lifespan context exits
        assert mock_event_bus.disconnect.called
        assert mock_state_manager.disconnect.called
        assert mock_db.disconnect.called


@pytest.mark.asyncio
async def test_health_check():
    """Test the health check endpoint returns correct status."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_lifespan_error_handling():
    """Test error handling during application shutdown."""
    mock_event_bus = AsyncMock()
    mock_state_manager = AsyncMock()
    mock_settings = AsyncMock()
    mock_db = AsyncMock()

    # Configure mock to raise error during disconnect
    db_error = Exception("Database disconnect error")
    mock_db.disconnect.side_effect = db_error

    with (
        patch("pythmata.main.EventBus", return_value=mock_event_bus),
        patch("pythmata.main.StateManager", return_value=mock_state_manager),
        patch("pythmata.main.Settings", return_value=mock_settings),
        patch("pythmata.main.get_db", return_value=mock_db),
        patch("pythmata.main.init_db"),
        pytest.raises(Exception) as exc_info,
    ):
        async with app.router.lifespan_context(app) as _:
            # Verify startup succeeded
            assert mock_event_bus.connect.called
            assert mock_state_manager.connect.called
            assert mock_db.connect.called

    # Verify the database error was raised
    assert exc_info.value == db_error

    # Verify other services still attempted to disconnect
    assert mock_event_bus.disconnect.called
    assert mock_state_manager.disconnect.called


@pytest.mark.asyncio
async def test_handle_process_started():
    """Test process.started event handler."""
    mock_state_manager = AsyncMock()
    mock_db = AsyncMock()
    mock_session = AsyncMock()
    mock_executor = AsyncMock()
    mock_definition = AsyncMock()
    mock_parser = MagicMock()

    test_data = {
        "instance_id": "test-instance",
        "definition_id": "test-definition",
    }

    # Create a regular mock for the definition (since it's a model instance)
    mock_definition = MagicMock()
    mock_definition.bpmn_xml = "<xml>test</xml>"

    # Configure mock session with async result
    mock_session = AsyncMock(spec=AsyncSession)
    execute_result = AsyncMock()
    execute_result.scalar_one_or_none = AsyncMock(return_value=mock_definition)
    mock_session.execute = AsyncMock(return_value=execute_result)

    # Create session context manager
    session_ctx = AsyncMock()
    session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    session_ctx.__aexit__ = AsyncMock()

    # Mock the session method to return the context manager
    mock_db.session = MagicMock(return_value=session_ctx)
    mock_db.is_connected = True

    # Configure select statement
    select_stmt = select(ProcessDefinitionModel).filter(
        ProcessDefinitionModel.id == test_data["definition_id"]
    )
    mock_select = AsyncMock(return_value=select_stmt)

    # Configure parser mock with valid process graph
    process_graph = {
        "nodes": [
            Event(id="Start_1", type="event", event_type=EventType.START, outgoing=["Flow_1"]),
            Event(id="End_1", type="event", event_type=EventType.END, incoming=["Flow_1"])
        ],
        "flows": [
            {"id": "Flow_1", "source_ref": "Start_1", "target_ref": "End_1"}
        ]
    }
    mock_parser.parse.return_value = process_graph

    with (
        patch("pythmata.main.Settings"),
        patch("pythmata.main.StateManager", return_value=mock_state_manager),
        patch("pythmata.main.get_db", return_value=mock_db),
        patch("pythmata.main.BPMNParser", return_value=mock_parser),
        patch("pythmata.main.ProcessExecutor", return_value=mock_executor),
        patch("pythmata.main.select", return_value=mock_select),
    ):
        # Execute handler
        await handle_process_started(test_data)

        # Verify state manager lifecycle
        assert mock_state_manager.connect.called
        assert mock_state_manager.disconnect.called

        # Verify process definition retrieval
        mock_session.execute.assert_called_once()

        # Verify process execution
        assert mock_executor.create_initial_token.called
        assert mock_executor.execute_process.called
        mock_executor.create_initial_token.assert_called_with(
            "test-instance", "Start_1"
        )

        # Verify process graph validation
        mock_parser.parse.assert_called_once()
        mock_executor.execute_process.assert_called_once_with(
            "test-instance", process_graph
        )


@pytest.mark.asyncio
async def test_handle_process_started_error_cases():
    """Test error handling in process.started event handler."""
    mock_state_manager = AsyncMock()
    mock_db = AsyncMock()
    mock_session = AsyncMock()
    mock_parser = MagicMock()

    test_data = {
        "instance_id": "test-instance",
        "definition_id": "test-definition",
    }

    # Configure mock session with async result
    mock_session = AsyncMock(spec=AsyncSession)
    execute_result = AsyncMock()
    execute_result.scalar_one_or_none = AsyncMock(return_value=None)
    mock_session.execute = AsyncMock(return_value=execute_result)

    # Create session context manager
    session_ctx = AsyncMock()
    session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    session_ctx.__aexit__ = AsyncMock()

    # Mock the session method to return the context manager
    mock_db.session = MagicMock(return_value=session_ctx)
    mock_db.is_connected = True

    select_stmt = select(ProcessDefinitionModel).filter(
        ProcessDefinitionModel.id == test_data["definition_id"]
    )
    mock_select = AsyncMock(return_value=select_stmt)

    with (
        patch("pythmata.main.Settings"),
        patch("pythmata.main.StateManager", return_value=mock_state_manager),
        patch("pythmata.main.get_db", return_value=mock_db),
        patch("pythmata.main.BPMNParser", return_value=mock_parser),
        patch("pythmata.main.select", return_value=mock_select),
    ):
        await handle_process_started(test_data)
        # Should not raise exception but log error
        assert mock_state_manager.disconnect.called

    # Test case 2: Missing start event
    mock_definition = AsyncMock()
    mock_definition.bpmn_xml = "<xml>test</xml>"
    execute_result = AsyncMock()
    execute_result.scalar_one_or_none.return_value = mock_definition
    mock_session.execute.return_value = execute_result
    # Configure parser mock for error case
    mock_parser.parse.return_value = {"nodes": [], "flows": []}  # No start event in nodes

    with (
        patch("pythmata.main.Settings"),
        patch("pythmata.main.StateManager", return_value=mock_state_manager),
        patch("pythmata.main.get_db", return_value=mock_db),
        patch("pythmata.main.BPMNParser", return_value=mock_parser),
        patch("pythmata.main.select", return_value=mock_select),
    ):
        await handle_process_started(test_data)
        # Should not raise exception but log error
        assert mock_state_manager.disconnect.called


@pytest.mark.asyncio
async def test_cors_middleware():
    """Test CORS middleware configuration."""
    test_origin = "http://example.com"
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.options(
            "/health",
            headers={
                "Origin": test_origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )

        assert response.status_code == 200
        # When allow_credentials is True, the origin is reflected back
        assert response.headers["access-control-allow-origin"] == test_origin
        assert response.headers["access-control-allow-credentials"] == "true"
        assert "GET" in response.headers["access-control-allow-methods"]
        assert "Content-Type" in response.headers["access-control-allow-headers"]
