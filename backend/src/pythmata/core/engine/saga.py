import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


@dataclass
class ParallelStepGroup:
    """Group of steps to be executed in parallel"""

    steps: List["SagaStep"] = field(default_factory=list)

    async def add_step(self, action_id: str, compensation_id: str, data: Dict) -> None:
        """Add a step to the parallel group"""
        step = SagaStep(action_id=action_id, compensation_id=compensation_id, data=data)
        self.steps.append(step)


class SagaStatus(Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    COMPENSATING = "COMPENSATING"
    COMPENSATED = "COMPENSATED"
    FAILED = "FAILED"


@dataclass
class SagaStep:
    action_id: str
    compensation_id: str
    data: Dict
    completed: bool = False
    compensated: bool = False


@dataclass
class SagaResult:
    status: SagaStatus
    data: Optional[Dict] = None


class SagaOrchestrator:
    def __init__(self, saga_id: str, instance_id: str):
        self.saga_id = saga_id
        self.instance_id = instance_id
        self.steps: List[SagaStep] = []
        self.parallel_groups: List[ParallelStepGroup] = []
        self.status = SagaStatus.ACTIVE
        self.compensation_required = False

    @property
    def completed_steps(self) -> List[SagaStep]:
        return [step for step in self.steps if step.completed]

    async def add_step(self, action_id: str, compensation_id: str, data: Dict) -> None:
        """Add a new step to the saga with its compensation action"""
        step = SagaStep(action_id=action_id, compensation_id=compensation_id, data=data)
        self.steps.append(step)

    async def create_parallel_group(self) -> ParallelStepGroup:
        """Create a new group of steps to be executed in parallel"""
        group = ParallelStepGroup()
        self.parallel_groups.append(group)
        return group

    async def _execute_step(self, step: SagaStep) -> bool:
        """Execute a single saga step"""
        try:
            # Simulate step execution with sleep if specified
            if "sleep" in step.data:
                await asyncio.sleep(step.data["sleep"])

            if "should_fail" in step.data and step.data["should_fail"]:
                raise Exception(f"Step {step.action_id} failed")

            step.completed = True
            return True
        except Exception as e:
            step.data["error"] = str(e)
            return False

    async def _compensate_step(self, step: SagaStep) -> None:
        """Execute compensation for a single step"""
        if step.completed and not step.compensated:
            # Simulate compensation execution
            if "sleep" in step.data:
                await asyncio.sleep(step.data["sleep"])
            step.compensated = True

    async def _execute_parallel_group(self, group: ParallelStepGroup) -> bool:
        """Execute all steps in a parallel group concurrently"""
        # Create tasks for all steps in the group
        tasks = [self._execute_step(step) for step in group.steps]

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check if any step failed
        for i, result in enumerate(results):
            if isinstance(result, Exception) or not result:
                return False
            # Add successful steps to main steps list for tracking
            self.steps.append(group.steps[i])

        return True

    async def execute(self) -> SagaResult:
        """Execute saga steps, handling both sequential and parallel execution"""
        try:
            # Execute sequential steps
            for step in self.steps:
                success = await self._execute_step(step)
                if not success:
                    await self._handle_failure(step)
                    return SagaResult(
                        status=self.status,
                        data={"error": step.data.get("error", "Unknown error")},
                    )

            # Execute parallel groups
            for group in self.parallel_groups:
                success = await self._execute_parallel_group(group)
                if not success:
                    await self._handle_failure(group.steps[-1])
                    return SagaResult(
                        status=self.status,
                        data={"error": "Parallel step execution failed"},
                    )

            # All steps completed successfully
            self.status = SagaStatus.COMPLETED
            return SagaResult(status=self.status)

        except Exception as e:
            self.status = SagaStatus.FAILED
            self.compensation_required = True
            return SagaResult(status=self.status, data={"error": str(e)})

    async def _handle_failure(self, failed_step: SagaStep) -> None:
        """Handle step failure by triggering compensation"""
        self.compensation_required = True
        self.status = SagaStatus.COMPENSATING

        # Compensate completed steps in reverse order
        for completed_step in reversed(self.completed_steps):
            await self._compensate_step(completed_step)

        self.status = SagaStatus.COMPENSATED
