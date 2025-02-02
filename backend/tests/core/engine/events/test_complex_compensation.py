import pytest

from pythmata.core.engine.events.compensation import (
    CompensationActivity,
    CompensationBoundaryEvent,
    CompensationEventDefinition,
    CompensationScope,
)
from pythmata.core.engine.token import Token, TokenState


@pytest.mark.asyncio
async def test_nested_compensation_propagation():
    """Test compensation handling within nested scopes"""
    # Setup nested structure:
    # Process
    #   └─ Subprocess_1
    #        └─ Task_1 (with compensation handler)

    # Create scopes
    process_scope = CompensationScope(scope_id="Process_1")
    subprocess_scope = CompensationScope(
        scope_id="Subprocess_1", parent_scope=process_scope
    )

    # Setup compensation handler for Task_1
    task_id = "Task_1"
    handler_id = "CompensationHandler_1"
    boundary_event = CompensationBoundaryEvent(
        event_id="CompensationBoundary_1",
        attached_to_id=task_id,
        handler_id=handler_id,
        scope=subprocess_scope,
    )

    # Create compensation token targeting the subprocess
    token = Token(
        instance_id="test_instance",
        node_id="Subprocess_1",
        state=TokenState.COMPENSATION,
        data={"compensate_scope_id": "Subprocess_1", "activity_data": {"key": "value"}},
    )

    # Execute compensation boundary event
    result_token = await boundary_event.execute(token)

    # Verify compensation handler is triggered with correct scope
    assert result_token.state == TokenState.ACTIVE
    assert result_token.node_id == handler_id
    assert result_token.data["compensated_activity_id"] == task_id
    assert result_token.data["compensation_scope_id"] == "Subprocess_1"
    assert result_token.data["original_activity_data"] == {"key": "value"}


@pytest.mark.asyncio
async def test_nested_compensation_isolation():
    """Test that compensation is properly isolated within scopes"""
    # Setup nested structure with two subprocesses
    # Process
    #   ├─ Subprocess_1
    #   │    └─ Task_1 (with compensation handler)
    #   └─ Subprocess_2
    #        └─ Task_2 (with compensation handler)

    # Create scopes
    process_scope = CompensationScope(scope_id="Process_1")
    subprocess1_scope = CompensationScope(
        scope_id="Subprocess_1", parent_scope=process_scope
    )
    subprocess2_scope = CompensationScope(
        scope_id="Subprocess_2", parent_scope=process_scope
    )

    # Setup compensation handlers
    handler1_id = "CompensationHandler_1"
    handler2_id = "CompensationHandler_2"

    boundary_event1 = CompensationBoundaryEvent(
        event_id="CompensationBoundary_1",
        attached_to_id="Task_1",
        handler_id=handler1_id,
        scope=subprocess1_scope,
    )

    boundary_event2 = CompensationBoundaryEvent(
        event_id="CompensationBoundary_2",
        attached_to_id="Task_2",
        handler_id=handler2_id,
        scope=subprocess2_scope,
    )

    # Create compensation token for Subprocess_1
    token = Token(
        instance_id="test_instance",
        node_id="Subprocess_1",
        state=TokenState.COMPENSATION,
        data={
            "compensate_scope_id": "Subprocess_1",
            "activity_data": {"subprocess": 1},
        },
    )

    # Execute compensation boundary events
    result1 = await boundary_event1.execute(token)
    result2 = await boundary_event2.execute(token)

    # Verify only the correct handler is triggered
    assert result1.state == TokenState.ACTIVE
    assert result1.node_id == handler1_id
    assert result2 == token  # Second handler should not trigger
