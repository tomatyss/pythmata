"""Tests for main application functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pythmata.core.types import Event, EventType
from pythmata.core.utils.event_handlers import handle_process_started
from pythmata.main import app
from pythmata.models.process import ProcessDefinition as ProcessDefinitionModel


@pytest.mark.asyncio
async def test_lifespan():
    """Test application lifespan (startup and shutdown)."""
    mock_event_bus = AsyncMock()
    # Setup state manager with no existing tokens
    mock_state_manager = AsyncMock()
    mock_state_manager.get_token_positions = AsyncMock(return_value=None)
    mock_settings = AsyncMock()
    mock_db = AsyncMock()

    with (
        patch("pythmata.core.utils.lifecycle.EventBus", return_value=mock_event_bus),
        patch(
            "pythmata.core.utils.lifecycle.StateManager",
            return_value=mock_state_manager,
        ),
        patch("pythmata.core.utils.lifecycle.Settings", return_value=mock_settings),
        patch("pythmata.core.utils.lifecycle.get_db", return_value=mock_db),
        patch("pythmata.core.utils.lifecycle.init_db"),
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
        patch("pythmata.core.utils.lifecycle.EventBus", return_value=mock_event_bus),
        patch(
            "pythmata.core.utils.lifecycle.StateManager",
            return_value=mock_state_manager,
        ),
        patch("pythmata.core.utils.lifecycle.Settings", return_value=mock_settings),
        patch("pythmata.core.utils.lifecycle.get_db", return_value=mock_db),
        patch("pythmata.core.utils.lifecycle.init_db"),
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
    """
    Test process.started event handler following BPMN lifecycle.

    This test verifies:
    1. Process definition loading
    2. BPMN parsing and validation
    3. Process instance initialization
    4. Token creation and management
    5. Process execution
    """
    # Setup test data and mocks
    mock_state_manager = AsyncMock()
    mock_db = AsyncMock()
    mock_session = AsyncMock()
    mock_executor = AsyncMock()
    mock_definition = MagicMock()
    mock_parser = MagicMock()

    test_data = {
        "instance_id": "test-instance",
        "definition_id": "test-definition",
    }

    # Mock process definition
    mock_definition.bpmn_xml = "<xml>test</xml>"
    mock_definition.id = test_data["definition_id"]

    # Configure database session
    mock_session = AsyncMock(spec=AsyncSession)
    execute_result = AsyncMock()
    execute_result.scalar_one_or_none = MagicMock(return_value=mock_definition)
    mock_session.execute = AsyncMock(return_value=execute_result)

    # Setup session context
    session_ctx = AsyncMock()
    session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    session_ctx.__aexit__ = AsyncMock()
    mock_db.session = MagicMock(return_value=session_ctx)
    mock_db.is_connected = True

    # Configure database query
    select_stmt = select(ProcessDefinitionModel).filter(
        ProcessDefinitionModel.id == test_data["definition_id"]
    )
    mock_select = AsyncMock(return_value=select_stmt)

    # Setup valid BPMN process graph
    process_graph = {
        "nodes": [
            Event(
                id="Start_1",
                type="event",
                event_type=EventType.START,
                outgoing=["Flow_1"],
            ),
            Event(
                id="End_1", type="event", event_type=EventType.END, incoming=["Flow_1"]
            ),
        ],
        "flows": [{"id": "Flow_1", "source_ref": "Start_1", "target_ref": "End_1"}],
    }
    mock_parser.parse.return_value = process_graph

    # Mock initial token
    mock_initial_token = MagicMock()
    mock_initial_token.id = "token-1"
    mock_initial_token.instance_id = test_data["instance_id"]
    mock_initial_token.node_id = "Start_1"
    mock_executor.create_initial_token.return_value = mock_initial_token

    with (
        patch("pythmata.core.utils.event_handlers.Settings"),
        patch(
            "pythmata.core.utils.event_handlers.StateManager",
            return_value=mock_state_manager,
        ),
        patch("pythmata.core.utils.event_handlers.get_db", return_value=mock_db),
        patch("pythmata.core.utils.process_utils.BPMNParser", return_value=mock_parser),
        patch(
            "pythmata.core.utils.process_utils.ProcessExecutor",
            return_value=mock_executor,
        ),
        patch("pythmata.core.utils.process_utils.select", return_value=mock_select),
    ):
        # Execute handler
        await handle_process_started(test_data)

        # 1. Verify state manager lifecycle
        mock_state_manager.connect.assert_called_once()
        mock_state_manager.disconnect.assert_called_once()

        # 2. Verify process definition loading
        mock_session.execute.assert_called_once()
        mock_parser.parse.assert_called_once_with(mock_definition.bpmn_xml)

        # 3. Verify token creation
        mock_executor.create_initial_token.assert_called_once_with(
            test_data["instance_id"], "Start_1"
        )

        # 4. Verify process execution
        mock_executor.execute_process.assert_called_once_with(
            test_data["instance_id"], process_graph
        )

        # 5. Verify execution order
        assert mock_executor.create_initial_token.call_count == 1
        assert mock_executor.execute_process.call_count == 1


@pytest.mark.asyncio
async def test_handle_process_started_error_cases():
    """
    Test error handling in process.started event handler.

    Tests the following error cases:
    1. Process definition not found
    2. Invalid BPMN XML
    3. Missing start event
    """
    mock_state_manager = AsyncMock()
    mock_db = AsyncMock()
    mock_session = AsyncMock()
    mock_parser = MagicMock()

    test_data = {
        "instance_id": "test-instance",
        "definition_id": "test-definition",
    }

    # Test Case 1: Process definition not found
    mock_session = AsyncMock(spec=AsyncSession)
    execute_result = AsyncMock()
    execute_result.scalar_one_or_none = MagicMock(return_value=None)
    mock_session.execute = AsyncMock(return_value=execute_result)

    session_ctx = AsyncMock()
    session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    session_ctx.__aexit__ = AsyncMock()
    mock_db.session = MagicMock(return_value=session_ctx)
    mock_db.is_connected = True

    select_stmt = select(ProcessDefinitionModel).filter(
        ProcessDefinitionModel.id == test_data["definition_id"]
    )
    mock_select = AsyncMock(return_value=select_stmt)

    # Test Case 1: Process definition not found
    with (
        patch("pythmata.core.utils.event_handlers.Settings"),
        patch(
            "pythmata.core.utils.event_handlers.StateManager",
            return_value=mock_state_manager,
        ),
        patch("pythmata.core.utils.event_handlers.get_db", return_value=mock_db),
        patch("pythmata.core.utils.process_utils.BPMNParser", return_value=mock_parser),
        patch("pythmata.core.utils.process_utils.select", return_value=mock_select),
    ):
        await handle_process_started(test_data)
        mock_state_manager.disconnect.assert_called_once()
        mock_parser.parse.assert_not_called()

    # Test Case 2: Invalid BPMN XML
    # Create new mock for each test case
    mock_state_manager = AsyncMock()
    mock_state_manager.get_token_positions = AsyncMock(return_value=None)
    mock_definition = MagicMock()
    mock_definition.bpmn_xml = "<invalid>xml</invalid>"
    mock_definition.id = test_data["definition_id"]
    execute_result.scalar_one_or_none = MagicMock(return_value=mock_definition)
    mock_parser = MagicMock()  # Create new mock for each test case
    mock_parser.parse.side_effect = Exception("Invalid BPMN XML")

    with (
        patch("pythmata.core.utils.event_handlers.Settings"),
        patch(
            "pythmata.core.utils.event_handlers.StateManager",
            return_value=mock_state_manager,
        ),
        patch("pythmata.core.utils.event_handlers.get_db", return_value=mock_db),
        patch("pythmata.core.utils.process_utils.BPMNParser", return_value=mock_parser),
        patch("pythmata.core.utils.process_utils.select", return_value=mock_select),
    ):
        await handle_process_started(test_data)
        mock_state_manager.disconnect.assert_called_once()
        mock_parser.parse.assert_called_once_with("<invalid>xml</invalid>")

    # Test Case 3: Missing start event
    # Create new mock for each test case
    mock_state_manager = AsyncMock()
    mock_state_manager.get_token_positions = AsyncMock(return_value=None)
    mock_definition = MagicMock()
    mock_definition.bpmn_xml = "<xml>test</xml>"
    mock_definition.id = test_data["definition_id"]
    execute_result.scalar_one_or_none = MagicMock(return_value=mock_definition)
    mock_parser = MagicMock()  # Create new mock for each test case
    mock_parser.parse.return_value = {"nodes": [], "flows": []}  # No start event

    with (
        patch("pythmata.core.utils.event_handlers.Settings"),
        patch(
            "pythmata.core.utils.event_handlers.StateManager",
            return_value=mock_state_manager,
        ),
        patch("pythmata.core.utils.event_handlers.get_db", return_value=mock_db),
        patch("pythmata.core.utils.process_utils.BPMNParser", return_value=mock_parser),
        patch("pythmata.core.utils.process_utils.select", return_value=mock_select),
    ):
        await handle_process_started(test_data)
        mock_state_manager.disconnect.assert_called_once()
        mock_parser.parse.assert_called_once_with("<xml>test</xml>")


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
