import pytest

from pythmata.core.engine.events.compensation import (
    CompensationActivity,
    CompensationBoundaryEvent,
    CompensationEventDefinition,
    CompensationScope,
)
from pythmata.core.engine.token import Token, TokenState


@pytest.mark.asyncio
async def test_parallel_compensation_handlers():
    """Test multiple compensation handlers executing in parallel"""
    # Setup structure:
    # Process
    #   ├─ Task_1 (with compensation handler)
    #   └─ Task_2 (with compensation handler)

    # Create scope
    process_scope = CompensationScope(scope_id="Process_1")

    # Setup compensation handlers
    handler1_id = "CompensationHandler_1"
    handler2_id = "CompensationHandler_2"

    boundary_event1 = CompensationBoundaryEvent(
        event_id="CompensationBoundary_1",
        attached_to_id="Task_1",
        handler_id=handler1_id,
        scope=process_scope,
    )

    boundary_event2 = CompensationBoundaryEvent(
        event_id="CompensationBoundary_2",
        attached_to_id="Task_2",
        handler_id=handler2_id,
        scope=process_scope,
    )

    # Create compensation token for the process scope
    token = Token(
        instance_id="test_instance",
        node_id="Process_1",
        state=TokenState.COMPENSATION,
        data={"compensate_scope_id": "Process_1", "activity_data": {"process": "data"}},
    )

    # Execute compensation boundary events
    result1 = await boundary_event1.execute(token)
    result2 = await boundary_event2.execute(token)

    # Verify both handlers are triggered
    assert result1.state == TokenState.ACTIVE
    assert result1.node_id == handler1_id
    assert result1.data["compensated_activity_id"] == "Task_1"
    assert result1.data["compensation_scope_id"] == "Process_1"

    assert result2.state == TokenState.ACTIVE
    assert result2.node_id == handler2_id
    assert result2.data["compensated_activity_id"] == "Task_2"
    assert result2.data["compensation_scope_id"] == "Process_1"


@pytest.mark.asyncio
async def test_parallel_compensation_data_isolation():
    """Test that parallel compensation handlers maintain data isolation"""
    # Setup structure with two tasks with different data
    process_scope = CompensationScope(scope_id="Process_1")

    # Setup compensation handlers
    handler1_id = "CompensationHandler_1"
    handler2_id = "CompensationHandler_2"

    boundary_event1 = CompensationBoundaryEvent(
        event_id="CompensationBoundary_1",
        attached_to_id="Task_1",
        handler_id=handler1_id,
        scope=process_scope,
    )

    boundary_event2 = CompensationBoundaryEvent(
        event_id="CompensationBoundary_2",
        attached_to_id="Task_2",
        handler_id=handler2_id,
        scope=process_scope,
    )

    # Create tokens with different activity data
    token1 = Token(
        instance_id="test_instance",
        node_id="Task_1",
        state=TokenState.COMPENSATION,
        data={
            "compensate_scope_id": "Process_1",
            "activity_data": {"task": 1, "value": "first"},
        },
    )

    token2 = Token(
        instance_id="test_instance",
        node_id="Task_2",
        state=TokenState.COMPENSATION,
        data={
            "compensate_scope_id": "Process_1",
            "activity_data": {"task": 2, "value": "second"},
        },
    )

    # Execute compensation boundary events
    result1 = await boundary_event1.execute(token1)
    result2 = await boundary_event2.execute(token2)

    # Verify data isolation
    assert result1.data["original_activity_data"] == {"task": 1, "value": "first"}
    assert result2.data["original_activity_data"] == {"task": 2, "value": "second"}


@pytest.mark.asyncio
async def test_parallel_compensation_ordering():
    """Test that parallel compensation handlers respect execution order when specified"""
    # Setup structure with ordered compensation
    process_scope = CompensationScope(scope_id="Process_1")

    # Setup compensation handlers with order
    handler1_id = "CompensationHandler_1"
    handler2_id = "CompensationHandler_2"

    boundary_event1 = CompensationBoundaryEvent(
        event_id="CompensationBoundary_1",
        attached_to_id="Task_1",
        handler_id=handler1_id,
        scope=process_scope,
        execution_order=1,  # Should execute first
    )

    boundary_event2 = CompensationBoundaryEvent(
        event_id="CompensationBoundary_2",
        attached_to_id="Task_2",
        handler_id=handler2_id,
        scope=process_scope,
        execution_order=2,  # Should execute second
    )

    # Create compensation token
    token = Token(
        instance_id="test_instance",
        node_id="Process_1",
        state=TokenState.COMPENSATION,
        data={"compensate_scope_id": "Process_1", "activity_data": {"process": "data"}},
    )

    # Get ordered handlers
    handlers = process_scope.get_ordered_handlers()

    # Verify handler order
    assert len(handlers) == 2
    assert handlers[0].handler_id == handler1_id
    assert handlers[1].handler_id == handler2_id

    # Execute handlers in order
    for handler in handlers:
        result = await handler.execute(token)
        assert result.state == TokenState.ACTIVE
        assert result.data["compensation_scope_id"] == "Process_1"
