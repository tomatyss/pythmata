"""Base class for saga tests."""

from typing import Optional

from pythmata.core.engine.saga import ParallelStepGroup, SagaOrchestrator


class BaseSagaTest:
    """Base class for saga tests providing common setup and utilities."""

    def create_basic_saga(
        self, saga_id: str = "Saga_1", instance_id: str = "test_instance"
    ) -> SagaOrchestrator:
        """Create a basic saga with default configuration.

        Args:
            saga_id: Unique identifier for the saga
            instance_id: Process instance ID

        Returns:
            SagaOrchestrator: Configured saga orchestrator
        """
        return SagaOrchestrator(saga_id, instance_id)

    async def setup_sequential_steps(
        self,
        saga: SagaOrchestrator,
        num_steps: int = 2,
        fail_step: Optional[int] = None,
    ) -> None:
        """Add sequential steps to a saga, optionally making one step fail.

        Args:
            saga: Saga orchestrator to add steps to
            num_steps: Number of sequential steps to add
            fail_step: Index of step that should fail (optional)
        """
        for i in range(num_steps):
            data = {"task": i + 1}
            if fail_step is not None and i == fail_step:
                data["should_fail"] = True
            await saga.add_step(
                action_id=f"Task_{i+1}", compensation_id=f"Comp_{i+1}", data=data
            )

    async def setup_parallel_steps(
        self, saga: SagaOrchestrator, num_steps: int = 2, sleep_time: float = 0.1
    ) -> ParallelStepGroup:
        """Create a parallel step group with specified number of steps.

        Args:
            saga: Saga orchestrator to add parallel steps to
            num_steps: Number of parallel steps to add
            sleep_time: Time to sleep between steps (for testing timing)

        Returns:
            ParallelStepGroup: Configured parallel step group
        """
        group = await saga.create_parallel_group()
        for i in range(num_steps):
            await group.add_step(
                action_id=f"Task_{i+1}",
                compensation_id=f"Comp_{i+1}",
                data={"task": i + 1, "sleep": sleep_time},
            )
        return group
