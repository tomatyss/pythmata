import asyncio
import os
import pytest
from pathlib import Path

from pythmata.core.engine.executor import ProcessExecutor
from pythmata.core.engine.instance import ProcessInstanceManager
from pythmata.core.bpmn.parser import BPMNParser
from pythmata.core.state import StateManager


@pytest.fixture
async def state_manager():
    """Create a real state manager connected to Redis."""
    manager = StateManager()
    await manager.initialize()
    yield manager
    await manager.close()


@pytest.fixture
async def process_instance_manager(state_manager):
    """Create a process instance manager."""
    manager = ProcessInstanceManager(state_manager)
    yield manager


@pytest.fixture
async def process_executor(state_manager, process_instance_manager):
    """Create a process executor."""
    executor = ProcessExecutor(state_manager, process_instance_manager)
    yield executor


@pytest.fixture
def compensation_process_path():
    """Get path to compensation process BPMN file."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    fixtures_dir = os.path.join(current_dir, "..", "fixtures")
    return os.path.join(fixtures_dir, "compensation_process.bpmn")


@pytest.fixture
async def compensation_process_graph(compensation_process_path):
    """Parse compensation process BPMN file into process graph."""
    parser = BPMNParser()
    with open(compensation_process_path, "r") as f:
        bpmn_xml = f.read()
    return parser.parse(bpmn_xml)


@pytest.mark.asyncio
async def test_successful_booking_without_compensation(
    state_manager, process_instance_manager, process_executor, compensation_process_graph
):
    """Test successful booking without compensation."""
    # Create process instance
    instance_id = "test-success-instance"
    
    # Start process execution
    await process_instance_manager.create_process_instance(
        instance_id=instance_id,
        process_definition_id="CompensationProcess",
        process_graph=compensation_process_graph,
        variables={"payment_success": True},
    )
    
    # Wait for process to complete (max 10 seconds)
    for _ in range(20):
        # Check if process has completed
        tokens = await state_manager.get_token_positions(instance_id)
        if not tokens:
            break
        await asyncio.sleep(0.5)
    
    # Get process variables
    variables = await state_manager.get_variables(instance_id)
    
    # Verify process completed successfully
    assert "hotel_reservation_id" in variables
    assert "flight_reservation_id" in variables
    assert "payment_id" in variables
    assert variables["payment_status"] == "completed"
    assert variables["confirmation_sent"] is True
    
    # Verify compensation was not triggered
    assert "hotel_cancelled" not in variables
    assert "flight_cancelled" not in variables
    
    # Verify no tokens remain
    tokens = await state_manager.get_token_positions(instance_id)
    assert not tokens


@pytest.mark.asyncio
async def test_booking_with_compensation(
    state_manager, process_instance_manager, process_executor, compensation_process_graph
):
    """Test booking with compensation when payment fails."""
    # Create process instance
    instance_id = "test-compensation-instance"
    
    # Start process execution with payment_success=False to trigger compensation
    await process_instance_manager.create_process_instance(
        instance_id=instance_id,
        process_definition_id="CompensationProcess",
        process_graph=compensation_process_graph,
        variables={"payment_success": False},
    )
    
    # Wait for process to complete (max 10 seconds)
    for _ in range(20):
        # Check if process has completed
        tokens = await state_manager.get_token_positions(instance_id)
        if not tokens:
            break
        await asyncio.sleep(0.5)
    
    # Get process variables
    variables = await state_manager.get_variables(instance_id)
    
    # Verify initial bookings were made
    assert "hotel_reservation_id" in variables
    assert "flight_reservation_id" in variables
    
    # Verify compensation was triggered
    assert "hotel_cancelled" in variables
    assert variables["hotel_cancelled"] is True
    assert "flight_cancelled" in variables
    assert variables["flight_cancelled"] is True
    
    # Verify notification was sent
    assert "notification_sent" in variables
    assert variables["notification_sent"] is True
    assert variables["reason"] == "Payment failed"
    
    # Verify cancellation IDs match the original reservation IDs
    assert variables["cancellation_id"].startswith("HC-")
    assert variables["hotel_reservation_id"] in variables["cancellation_id"]
    
    # Verify no tokens remain (process completed)
    tokens = await state_manager.get_token_positions(instance_id)
    assert not tokens
    
    # Verify compensation handlers were registered and then cleared
    handlers = await state_manager.get_all_compensation_handlers(instance_id)
    assert not handlers  # Should be empty after compensation completes 