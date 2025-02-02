import pytest
import asyncio
import time
from typing import List, Dict, Optional

from pythmata.core.engine.token import Token, TokenState
from pythmata.core.engine.saga import SagaOrchestrator, SagaStatus, ParallelStepGroup


@pytest.mark.asyncio
async def test_basic_saga_orchestration():
    """Test basic saga pattern with successful execution"""
    # Setup saga structure:
    # Saga_1
    #   ├─ Task_1 (with compensation)
    #   └─ Task_2 (with compensation)
    
    saga = SagaOrchestrator("Saga_1", "test_instance")
    
    # Define steps with their compensations
    await saga.add_step(
        action_id="Task_1",
        compensation_id="Comp_1",
        data={"task": 1}
    )
    await saga.add_step(
        action_id="Task_2",
        compensation_id="Comp_2",
        data={"task": 2}
    )
    
    # Execute saga
    result = await saga.execute()
    
    assert result.status == SagaStatus.COMPLETED
    assert len(saga.completed_steps) == 2
    assert not saga.compensation_required


@pytest.mark.asyncio
async def test_saga_compensation_on_failure():
    """Test saga compensation when step fails"""
    saga = SagaOrchestrator("Saga_1", "test_instance")
    
    # Add steps where second step will fail
    await saga.add_step(
        action_id="Task_1",
        compensation_id="Comp_1",
        data={"task": 1}
    )
    await saga.add_step(
        action_id="Task_2",
        compensation_id="Comp_2",
        data={"task": 2, "should_fail": True}
    )
    
    result = await saga.execute()
    
    # Verify failure and compensation
    assert result.status == SagaStatus.COMPENSATED
    assert saga.compensation_required
    assert len(saga.completed_steps) == 1
    assert saga.steps[0].compensated  # First step should be compensated
    assert not saga.steps[1].completed  # Second step should have failed
    assert result.data and "error" in result.data


@pytest.mark.asyncio
async def test_parallel_saga_steps():
    """Test parallel execution of saga steps"""
    saga = SagaOrchestrator("Saga_1", "test_instance")
    
    # Create a parallel step group
    parallel_group = await saga.create_parallel_group()
    
    # Add steps that simulate work with sleep
    await parallel_group.add_step(
        action_id="Task_1",
        compensation_id="Comp_1",
        data={"task": 1, "sleep": 0.1}
    )
    await parallel_group.add_step(
        action_id="Task_2",
        compensation_id="Comp_2",
        data={"task": 2, "sleep": 0.1}
    )
    
    # Record start time
    start_time = time.time()
    
    # Execute saga with parallel steps
    result = await saga.execute()
    
    # Calculate total execution time
    execution_time = time.time() - start_time
    
    # Verify parallel execution
    assert result.status == SagaStatus.COMPLETED
    assert len(saga.completed_steps) == 2
    assert not saga.compensation_required
    # If steps were executed in parallel, total time should be less than sum of individual sleep times
    assert execution_time < 0.2  # Less than sum of sleep times (0.1 + 0.1)
