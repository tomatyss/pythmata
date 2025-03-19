import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from pythmata.core.engine.node_executor import CompensationHandler, NodeExecutor
from pythmata.core.engine.token import Token, TokenState
from pythmata.core.state import StateManager
from pythmata.core.types import Event, EventType


@pytest.fixture
def mock_state_manager():
    """Create a mocked state manager."""
    state_manager = AsyncMock(spec=StateManager)
    
    # Redis pipeline mock
    pipeline_mock = AsyncMock()
    pipeline_mock.__aenter__ = AsyncMock(return_value=pipeline_mock)
    pipeline_mock.__aexit__ = AsyncMock(return_value=None)
    
    # Mock state manager's Redis connection
    state_manager.redis = AsyncMock()
    state_manager.redis.pipeline = MagicMock(return_value=pipeline_mock)
    
    return state_manager


@pytest.fixture
def mock_token_manager():
    """Create a mocked token manager."""
    return AsyncMock()


@pytest.fixture
def mock_instance_manager():
    """Create a mocked instance manager."""
    return AsyncMock()


@pytest.fixture
def compensation_handler(mock_state_manager, mock_token_manager, mock_instance_manager):
    """Create a compensation handler with mocked dependencies."""
    return CompensationHandler(
        state_manager=mock_state_manager,
        token_manager=mock_token_manager,
        instance_manager=mock_instance_manager,
    )


@pytest.fixture
def node_executor(mock_state_manager, mock_token_manager, mock_instance_manager):
    """Create a node executor with mocked dependencies."""
    return NodeExecutor(
        state_manager=mock_state_manager,
        token_manager=mock_token_manager,
        instance_manager=mock_instance_manager,
    )


@pytest.fixture
def process_graph():
    """Create a sample process graph with compensation activities."""
    return {
        "nodes": [
            {
                "id": "Task_1",
                "type": "task",
                "name": "Book Hotel",
                "incoming": ["Flow_1"],
                "outgoing": ["Flow_2"],
            },
            {
                "id": "Task_2",
                "type": "task",
                "name": "Book Flight",
                "incoming": ["Flow_2"],
                "outgoing": ["Flow_3"],
            },
            {
                "id": "CompensateTask_1",
                "type": "task",
                "name": "Cancel Hotel",
                "is_for_compensation": True,
                "incoming": [],
                "outgoing": [],
            },
            {
                "id": "CompensateTask_2",
                "type": "task",
                "name": "Cancel Flight",
                "is_for_compensation": True,
                "incoming": [],
                "outgoing": [],
            },
            {
                "id": "BoundaryEvent_1",
                "type": "boundaryEvent",
                "event_type": "boundary",
                "event_definition": "compensation",
                "attached_to": "Task_1",
                "outgoing": ["Flow_Comp_1"],
            },
            {
                "id": "BoundaryEvent_2",
                "type": "boundaryEvent",
                "event_type": "boundary",
                "event_definition": "compensation",
                "attached_to": "Task_2",
                "outgoing": ["Flow_Comp_2"],
            },
            {
                "id": "ThrowEvent_1",
                "type": "event",
                "event_type": "intermediate",
                "event_definition": "compensation",
                "incoming": ["Flow_3"],
                "outgoing": ["Flow_4"],
            },
            {
                "id": "EndEvent_1",
                "type": "event",
                "event_type": "end",
                "incoming": ["Flow_4"],
                "outgoing": [],
            },
        ],
        "flows": [
            {
                "id": "Flow_1",
                "source_ref": "StartEvent_1",
                "target_ref": "Task_1",
            },
            {
                "id": "Flow_2",
                "source_ref": "Task_1",
                "target_ref": "Task_2",
            },
            {
                "id": "Flow_3",
                "source_ref": "Task_2",
                "target_ref": "ThrowEvent_1",
            },
            {
                "id": "Flow_4",
                "source_ref": "ThrowEvent_1",
                "target_ref": "EndEvent_1",
            },
            {
                "id": "Flow_Comp_1",
                "source_ref": "BoundaryEvent_1",
                "target_ref": "CompensateTask_1",
            },
            {
                "id": "Flow_Comp_2",
                "source_ref": "BoundaryEvent_2",
                "target_ref": "CompensateTask_2",
            },
        ],
    }


@pytest.mark.asyncio
async def test_boundary_event_registration(compensation_handler, mock_state_manager):
    """Test registration of compensation boundary events."""
    # Create token and boundary event
    token = Token(
        instance_id="test_instance", 
        node_id="Task_1", 
        state=TokenState.ACTIVE,
        data={}
    )
    
    event = Event(
        id="BoundaryEvent_1",
        type="boundaryEvent",
        event_type=EventType.BOUNDARY,
        event_definition="compensation",
        attached_to="Task_1",
        outgoing=["Flow_Comp_1"],
    )
    
    process_graph = {
        "flows": [
            {
                "id": "Flow_Comp_1",
                "source_ref": "BoundaryEvent_1",
                "target_ref": "CompensateTask_1",
            }
        ],
        "nodes": [
            {
                "id": "CompensateTask_1",
                "type": "task",
                "name": "Cancel Hotel",
                "is_for_compensation": True,
            }
        ]
    }
    
    # Test handling of compensation boundary event
    await compensation_handler._handle_compensation_boundary_event(token, event, process_graph)
    
    # Check if compensation handler was stored
    mock_state_manager.store_compensation_handler.assert_called_once()
    call_args = mock_state_manager.store_compensation_handler.call_args[1]
    assert call_args["instance_id"] == "test_instance"
    assert call_args["activity_id"] == "Task_1"
    assert call_args["handler_data"]["handler_id"] == "CompensateTask_1"


@pytest.mark.asyncio
async def test_compensation_throw_event(compensation_handler, mock_state_manager, mock_token_manager):
    """Test handling of compensation throw events."""
    # Create token and compensation event
    token = Token(
        instance_id="test_instance", 
        node_id="ThrowEvent_1", 
        state=TokenState.ACTIVE,
        data={}
    )
    
    event = Event(
        id="ThrowEvent_1",
        type="event",
        event_type=EventType.INTERMEDIATE,
        event_definition="compensation",
        incoming=["Flow_3"],
        outgoing=["Flow_4"],
    )
    
    process_graph = {
        "flows": [
            {
                "id": "Flow_4",
                "source_ref": "ThrowEvent_1",
                "target_ref": "EndEvent_1",
            }
        ],
        "nodes": []
    }
    
    # Setup handler data to be returned
    handlers = [
        {
            "activity_id": "Task_1", 
            "handler_id": "CompensateTask_1",
            "boundary_event_id": "BoundaryEvent_1"
        },
        {
            "activity_id": "Task_2", 
            "handler_id": "CompensateTask_2",
            "boundary_event_id": "BoundaryEvent_2"
        }
    ]
    
    mock_state_manager.get_all_compensation_handlers.return_value = handlers
    
    # Test handling of compensation throw event
    with patch.object(compensation_handler, '_trigger_compensation_handler', AsyncMock()) as mock_trigger:
        await compensation_handler._handle_compensation_throw_event(token, event, process_graph)
        
        # Check if all compensation handlers were triggered
        assert mock_trigger.call_count == 2
        # Handlers should be triggered in reverse order (LIFO)
        mock_trigger.assert_any_call(token, handlers[1], process_graph)
        mock_trigger.assert_any_call(token, handlers[0], process_graph)
        
        # Check if token moved to next node
        mock_token_manager.move_token.assert_called_once_with(
            token, "EndEvent_1", compensation_handler.instance_manager
        )


@pytest.mark.asyncio
async def test_compensation_end_event(compensation_handler, mock_state_manager, mock_token_manager):
    """Test handling of compensation end events."""
    # Create token and compensation event
    token = Token(
        instance_id="test_instance", 
        node_id="EndEvent_1", 
        state=TokenState.ACTIVE,
        data={}
    )
    
    event = Event(
        id="EndEvent_1",
        type="event",
        event_type=EventType.END,
        event_definition="compensation",
        incoming=["Flow_3"],
        outgoing=[],
    )
    
    process_graph = {"flows": [], "nodes": []}
    
    # Setup mock handling of compensation throw event (which is called internally)
    with patch.object(compensation_handler, '_handle_compensation_throw_event', AsyncMock()) as mock_throw:
        await compensation_handler._handle_compensation_end_event(token, event, process_graph)
        
        # Check if compensation throw event was handled
        mock_throw.assert_called_once_with(token, event, process_graph)
        
        # Check if token was consumed (since this is an end event)
        mock_token_manager.consume_token.assert_called_once_with(token)


@pytest.mark.asyncio
async def test_trigger_compensation_handler(compensation_handler, mock_state_manager, mock_instance_manager):
    """Test triggering of specific compensation handler."""
    # Create token
    token = Token(
        instance_id="test_instance", 
        node_id="ThrowEvent_1", 
        state=TokenState.ACTIVE,
        data={"business_data": "important_value"}
    )
    
    # Create handler data
    handler_data = {
        "activity_id": "Task_1", 
        "handler_id": "CompensateTask_1",
        "boundary_event_id": "BoundaryEvent_1"
    }
    
    process_graph = {
        "nodes": [
            {
                "id": "CompensateTask_1",
                "type": "task",
                "name": "Cancel Hotel",
                "is_for_compensation": True,
            }
        ]
    }
    
    # Test triggering compensation handler
    await compensation_handler._trigger_compensation_handler(token, handler_data, process_graph)
    
    # Check if compensation token was created and stored
    mock_state_manager.add_token.assert_called_once()
    call_args = mock_state_manager.add_token.call_args[1]
    assert call_args["instance_id"] == "test_instance"
    assert call_args["node_id"] == "CompensateTask_1"
    
    # Check if token data contains relevant information
    token_data = json.loads(json.dumps(call_args["data"]))  # Simulate JSON serialization
    assert token_data["state"] == "COMPENSATION"
    assert token_data["compensated_activity_id"] == "Task_1"
    assert token_data["boundary_event_id"] == "BoundaryEvent_1"
    assert "original_token_data" in token_data
    assert token_data["original_token_data"]["business_data"] == "important_value"
    
    # Check if handler execution was queued
    mock_instance_manager.queue_node_execution.assert_called_once()
    call_args = mock_instance_manager.queue_node_execution.call_args[0]
    assert call_args[1]["id"] == "CompensateTask_1"


@pytest.mark.asyncio
async def test_node_executor_with_compensation_task(node_executor, process_graph):
    """Test node executor handling compensation tasks."""
    # Create token with normal state
    token = Token(
        instance_id="test_instance", 
        node_id="CompensateTask_1", 
        state=TokenState.ACTIVE,
        data={}
    )
    
    # Create compensation task
    task = {
        "id": "CompensateTask_1",
        "type": "task",
        "name": "Cancel Hotel",
        "is_for_compensation": True,
        "outgoing": ["Flow_Next"],
    }
    
    modified_graph = process_graph.copy()
    modified_graph["flows"].append({
        "id": "Flow_Next",
        "source_ref": "CompensateTask_1",
        "target_ref": "NextTask",
    })
    
    # Test execution of compensation task with normal token (should skip)
    result = await node_executor._execute_task(token, task, modified_graph)
    
    # Check if token was moved to next task without executing compensation
    node_executor.token_manager.move_token.assert_called_once_with(
        token, "NextTask", node_executor.instance_manager
    )
    
    # Check script executor was not called
    assert not hasattr(node_executor.script_executor, 'call_count') or node_executor.script_executor.call_count == 0
    
    # Now test with compensation token
    comp_token = Token(
        instance_id="test_instance", 
        node_id="CompensateTask_1", 
        state=TokenState.COMPENSATION,
        data={}
    )
    
    node_executor.token_manager.reset_mock()
    
    # Execute task with compensation token
    with patch.object(node_executor.script_executor, 'execute_script', AsyncMock(return_value={})):
        result = await node_executor._execute_task(comp_token, task, modified_graph)
        
        # Should execute normally for compensation tokens
        node_executor.token_manager.move_token.assert_called_once_with(
            comp_token, "NextTask", node_executor.instance_manager
        ) 