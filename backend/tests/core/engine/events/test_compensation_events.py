import pytest

from pythmata.core.engine.events.compensation import (
    CompensationActivity,
    CompensationBoundaryEvent,
    CompensationEventDefinition,
)
from pythmata.core.engine.token import Token, TokenState


@pytest.mark.asyncio
async def test_basic_compensation_trigger():
    """Test that compensation event is properly triggered"""
    # Setup
    task_id = "Task_1"
    handler_id = "CompensationHandler_1"
    boundary_event = CompensationBoundaryEvent(
        event_id="CompensationBoundary_1", attached_to_id=task_id, handler_id=handler_id
    )

    # Create token in compensation state targeting our task
    token = Token(
        instance_id="test_instance",
        node_id=task_id,
        state=TokenState.COMPENSATION,
        data={"compensate_activity_id": task_id},
    )

    # Execute compensation boundary event
    result_token = await boundary_event.execute(token)

    # Verify compensation handler is triggered
    assert result_token.state == TokenState.ACTIVE
    assert result_token.node_id == handler_id
    assert result_token.data["compensated_activity_id"] == task_id


@pytest.mark.asyncio
async def test_compensation_handler_execution():
    """Test that compensation handler is executed when triggered"""
    # Setup compensation activity
    compensate_activity = CompensationActivity(
        event_id="CompensateTask_1", compensate_activity_id="Task_1"
    )

    # Create token for compensation activity
    token = Token(
        instance_id="test_instance", node_id="CompensateTask_1", state=TokenState.ACTIVE
    )

    # Execute compensation activity
    result_token = await compensate_activity.execute(token)

    # Verify compensation state is set
    assert result_token.state == TokenState.COMPENSATION
    assert result_token.data["compensate_activity_id"] == "Task_1"


@pytest.mark.asyncio
async def test_compensation_data_preservation():
    """Test that original task data is available to compensation handler"""
    # Setup
    task_id = "Task_1"
    handler_id = "CompensationHandler_1"
    original_data = {"amount": 1000, "status": "completed"}

    boundary_event = CompensationBoundaryEvent(
        event_id="CompensationBoundary_1", attached_to_id=task_id, handler_id=handler_id
    )

    # Create token with original task data
    token = Token(
        instance_id="test_instance",
        node_id=task_id,
        state=TokenState.COMPENSATION,
        data={"compensate_activity_id": task_id, "activity_data": original_data},
    )

    # Execute compensation boundary event
    result_token = await boundary_event.execute(token)

    # Verify original data is preserved in compensation handler
    assert result_token.data["original_activity_data"] == original_data
    assert result_token.data["compensated_activity_id"] == task_id
