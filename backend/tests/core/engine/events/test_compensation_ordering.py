import pytest

from pythmata.core.engine.events.compensation import (
    CompensationActivity,
    CompensationBoundaryEvent,
    CompensationEventDefinition,
    CompensationScope,
)
from pythmata.core.engine.token import Token, TokenState


@pytest.mark.asyncio
async def test_sequential_compensation_chain():
    """Test sequential execution of compensation handlers in a chain"""
    # Setup structure:
    # Process
    #   ├─ Task_1 (with compensation handler, order 3)
    #   ├─ Task_2 (with compensation handler, order 1)
    #   └─ Task_3 (with compensation handler, order 2)

    process_scope = CompensationScope(scope_id="Process_1")

    # Setup compensation handlers with explicit ordering
    handlers = [
        CompensationBoundaryEvent(
            event_id="CompensationBoundary_1",
            attached_to_id="Task_1",
            handler_id="CompensationHandler_1",
            scope=process_scope,
            execution_order=3,  # Execute last
        ),
        CompensationBoundaryEvent(
            event_id="CompensationBoundary_2",
            attached_to_id="Task_2",
            handler_id="CompensationHandler_2",
            scope=process_scope,
            execution_order=1,  # Execute first
        ),
        CompensationBoundaryEvent(
            event_id="CompensationBoundary_3",
            attached_to_id="Task_3",
            handler_id="CompensationHandler_3",
            scope=process_scope,
            execution_order=2,  # Execute second
        ),
    ]

    # Create compensation token
    token = Token(
        instance_id="test_instance",
        node_id="Process_1",
        state=TokenState.COMPENSATION,
        data={"compensate_scope_id": "Process_1", "activity_data": {"process": "data"}},
    )

    # Get handlers in execution order
    ordered_handlers = process_scope.get_ordered_handlers()

    # Verify handler ordering
    assert len(ordered_handlers) == 3
    assert ordered_handlers[0].handler_id == "CompensationHandler_2"  # First
    assert ordered_handlers[1].handler_id == "CompensationHandler_3"  # Second
    assert ordered_handlers[2].handler_id == "CompensationHandler_1"  # Last

    # Execute handlers in order and verify each execution
    execution_sequence = []
    for handler in ordered_handlers:
        result = await handler.execute(token)
        assert result.state == TokenState.ACTIVE
        execution_sequence.append(result.node_id)

    # Verify execution sequence
    assert execution_sequence == [
        "CompensationHandler_2",
        "CompensationHandler_3",
        "CompensationHandler_1",
    ]


@pytest.mark.asyncio
async def test_nested_compensation_ordering():
    """Test compensation ordering with nested scopes"""
    # Setup structure:
    # Process (order 2)
    #   └─ Subprocess (order 1)
    #        ├─ Task_1 (with compensation handler, order 2)
    #        └─ Task_2 (with compensation handler, order 1)

    process_scope = CompensationScope(scope_id="Process_1")
    subprocess_scope = CompensationScope(
        scope_id="Subprocess_1", parent_scope=process_scope
    )

    # Setup subprocess compensation handlers
    subprocess_handlers = [
        CompensationBoundaryEvent(
            event_id="SubCompensationBoundary_1",
            attached_to_id="Task_1",
            handler_id="SubCompensationHandler_1",
            scope=subprocess_scope,
            execution_order=2,
        ),
        CompensationBoundaryEvent(
            event_id="SubCompensationBoundary_2",
            attached_to_id="Task_2",
            handler_id="SubCompensationHandler_2",
            scope=subprocess_scope,
            execution_order=1,
        ),
    ]

    # Create compensation token for subprocess
    token = Token(
        instance_id="test_instance",
        node_id="Subprocess_1",
        state=TokenState.COMPENSATION,
        data={
            "compensate_scope_id": "Subprocess_1",
            "activity_data": {"subprocess": "data"},
        },
    )

    # Get ordered handlers for subprocess
    ordered_handlers = subprocess_scope.get_ordered_handlers()

    # Verify subprocess handler ordering
    assert len(ordered_handlers) == 2
    assert ordered_handlers[0].handler_id == "SubCompensationHandler_2"  # First
    assert ordered_handlers[1].handler_id == "SubCompensationHandler_1"  # Second

    # Execute handlers in order
    execution_sequence = []
    for handler in ordered_handlers:
        result = await handler.execute(token)
        assert result.state == TokenState.ACTIVE
        execution_sequence.append(result.node_id)

    # Verify execution sequence
    assert execution_sequence == [
        "SubCompensationHandler_2",
        "SubCompensationHandler_1",
    ]


@pytest.mark.asyncio
async def test_default_compensation_ordering():
    """Test default ordering when no explicit order is specified"""
    # Setup structure with no explicit ordering
    process_scope = CompensationScope(scope_id="Process_1")

    # Add handlers in specific order
    handlers = [
        CompensationBoundaryEvent(
            event_id="CompensationBoundary_1",
            attached_to_id="Task_1",
            handler_id="CompensationHandler_1",
            scope=process_scope,
        ),
        CompensationBoundaryEvent(
            event_id="CompensationBoundary_2",
            attached_to_id="Task_2",
            handler_id="CompensationHandler_2",
            scope=process_scope,
        ),
    ]

    # Get handlers in default order
    ordered_handlers = process_scope.get_ordered_handlers()

    # Verify registration order is preserved
    assert len(ordered_handlers) == 2
    assert ordered_handlers[0].handler_id == "CompensationHandler_1"
    assert ordered_handlers[1].handler_id == "CompensationHandler_2"

    # Create compensation token
    token = Token(
        instance_id="test_instance",
        node_id="Process_1",
        state=TokenState.COMPENSATION,
        data={"compensate_scope_id": "Process_1", "activity_data": {"process": "data"}},
    )

    # Execute handlers and verify order is maintained
    execution_sequence = []
    for handler in ordered_handlers:
        result = await handler.execute(token)
        assert result.state == TokenState.ACTIVE
        execution_sequence.append(result.node_id)

    # Verify execution sequence matches registration order
    assert execution_sequence == ["CompensationHandler_1", "CompensationHandler_2"]
