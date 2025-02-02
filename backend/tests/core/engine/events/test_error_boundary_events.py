import pytest
from pythmata.core.engine.token import Token, TokenState
from pythmata.core.engine.events.error import ErrorBoundaryEvent

@pytest.mark.asyncio
async def test_error_boundary_event_basic():
    """Test basic error boundary event catching"""
    # Create error boundary event
    error_event = ErrorBoundaryEvent(
        event_id="Error_1",
        attached_to_id="Task_1",
        error_code="Error_Code_1"
    )
    
    # Create token with error data
    token = Token(
        instance_id="test_instance",
        node_id="Task_1",
        state=TokenState.ERROR,
        data={
            "error": {
                "code": "Error_Code_1",
                "message": "Test error"
            }
        }
    )
    
    # Execute error boundary event
    result_token = await error_event.execute(token)
    
    # Verify token state and data
    assert result_token.state == TokenState.ACTIVE
    assert result_token.node_id == "Error_1"
    assert result_token.instance_id == "test_instance"
    assert result_token.data["error"]["code"] == "Error_Code_1"
    assert result_token.data["error"]["message"] == "Test error"

@pytest.mark.asyncio
async def test_multiple_error_boundary_events():
    """Test multiple error boundary events on same task"""
    # Create error boundary events
    error_event_1 = ErrorBoundaryEvent(
        event_id="Error_1",
        attached_to_id="Task_1",
        error_code="Error_Code_1"
    )
    
    error_event_2 = ErrorBoundaryEvent(
        event_id="Error_2",
        attached_to_id="Task_1",
        error_code="Error_Code_2"
    )
    
    # Create token with first error code
    token_1 = Token(
        instance_id="test_instance",
        node_id="Task_1",
        state=TokenState.ERROR,
        data={
            "error": {
                "code": "Error_Code_1",
                "message": "Test error 1"
            }
        }
    )
    
    # Create token with second error code
    token_2 = Token(
        instance_id="test_instance",
        node_id="Task_1",
        state=TokenState.ERROR,
        data={
            "error": {
                "code": "Error_Code_2",
                "message": "Test error 2"
            }
        }
    )
    
    # Test first error event handles its error code
    result_1 = await error_event_1.execute(token_1)
    assert result_1.state == TokenState.ACTIVE
    assert result_1.node_id == "Error_1"
    assert result_1.data["error"]["code"] == "Error_Code_1"
    
    # Test second error event handles its error code
    result_2 = await error_event_2.execute(token_2)
    assert result_2.state == TokenState.ACTIVE
    assert result_2.node_id == "Error_2"
    assert result_2.data["error"]["code"] == "Error_Code_2"
    
    # Test first error event doesn't handle second error code
    result_3 = await error_event_1.execute(token_2)
    assert result_3.state == TokenState.ERROR
    assert result_3.node_id == "Task_1"
    assert result_3.data["error"]["code"] == "Error_Code_2"
    
    # Test second error event doesn't handle first error code
    result_4 = await error_event_2.execute(token_1)
    assert result_4.state == TokenState.ERROR
    assert result_4.node_id == "Task_1"
    assert result_4.data["error"]["code"] == "Error_Code_1"

@pytest.mark.asyncio
async def test_error_propagation():
    """Test error propagation through process hierarchy"""
    # Create error boundary events at different levels
    subprocess_error_event = ErrorBoundaryEvent(
        event_id="SubProcess_Error",
        attached_to_id="SubProcess_1",
        error_code="Error_Code_1"
    )
    
    task_error_event = ErrorBoundaryEvent(
        event_id="Task_Error",
        attached_to_id="Task_1",
        error_code="Error_Code_1"
    )
    
    # Create error token at task level
    task_token = Token(
        instance_id="test_instance",
        node_id="Task_1",
        state=TokenState.ERROR,
        data={
            "error": {
                "code": "Error_Code_1",
                "message": "Test error"
            }
        }
    )
    
    # Test task-level error is caught by task boundary event
    result_1 = await task_error_event.execute(task_token)
    assert result_1.state == TokenState.ACTIVE
    assert result_1.node_id == "Task_Error"
    
    # Test subprocess-level error handling
    subprocess_token = Token(
        instance_id="test_instance",
        node_id="SubProcess_1",
        state=TokenState.ERROR,
        data={
            "error": {
                "code": "Error_Code_1",
                "message": "Test error"
            }
        }
    )
    
    result_2 = await subprocess_error_event.execute(subprocess_token)
    assert result_2.state == TokenState.ACTIVE
    assert result_2.node_id == "SubProcess_Error"
    
    # Test error propagation (task error not caught propagates to subprocess)
    unhandled_token = Token(
        instance_id="test_instance",
        node_id="Task_1",
        state=TokenState.ERROR,
        data={
            "error": {
                "code": "Error_Code_2",  # Different error code
                "message": "Unhandled error"
            }
        }
    )
    
    # Task boundary event doesn't handle it
    result_3 = await task_error_event.execute(unhandled_token)
    assert result_3.state == TokenState.ERROR
    assert result_3.node_id == "Task_1"
    
    # Subprocess boundary event doesn't handle different error code
    result_4 = await subprocess_error_event.execute(unhandled_token)
    assert result_4.state == TokenState.ERROR
    assert result_4.node_id == "Task_1"
