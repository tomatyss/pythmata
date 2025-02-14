import time
from typing import Dict, List, Optional

import pytest

from pythmata.core.engine.saga import SagaStatus
from tests.core.saga.base import BaseSagaTest
from tests.core.testing import assert_saga_state


@pytest.mark.asyncio
class TestSagaOrchestration(BaseSagaTest):
    """Tests for saga orchestration patterns."""

    async def test_basic_saga_orchestration(self):
        """Test basic saga pattern with successful execution."""
        # Setup saga structure:
        # Saga_1
        #   ├─ Task_1 (with compensation)
        #   └─ Task_2 (with compensation)

        saga = self.create_basic_saga()
        await self.setup_sequential_steps(saga)

        # Execute saga
        result = await saga.execute()

        # Verify successful execution
        await assert_saga_state(saga, SagaStatus.COMPLETED, 2)
        assert not saga.compensation_required

    async def test_saga_compensation_on_failure(self):
        """Test saga compensation when step fails."""
        saga = self.create_basic_saga()
        await self.setup_sequential_steps(saga, fail_step=1)  # Make second step fail

        # Execute saga
        result = await saga.execute()

        # Verify failure and compensation
        await assert_saga_state(
            saga, SagaStatus.COMPENSATED, 1, compensation_required=True
        )
        assert saga.steps[0].compensated  # First step should be compensated
        assert not saga.steps[1].completed  # Second step should have failed
        assert result.data and "error" in result.data

    async def test_parallel_saga_steps(self):
        """Test parallel execution of saga steps."""
        saga = self.create_basic_saga()
        sleep_time = 0.1

        # Create parallel steps
        await self.setup_parallel_steps(saga, sleep_time=sleep_time)

        # Record start time and execute
        start_time = time.time()
        result = await saga.execute()
        execution_time = time.time() - start_time

        # Verify parallel execution
        await assert_saga_state(saga, SagaStatus.COMPLETED, 2)
        assert not saga.compensation_required
        # If steps were executed in parallel, total time should be less than sum of individual sleep times
        assert execution_time < (sleep_time * 2)  # Less than sum of sleep times
