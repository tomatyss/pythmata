"""Base class for engine tests."""

from typing import Dict, List

import pytest

from pythmata.core.engine.executor import ProcessExecutor
from pythmata.core.engine.token import Token
from pythmata.core.state import StateManager
from pythmata.core.types import Event, EventType, Gateway, GatewayType, Task


class BaseEngineTest:
    """Base class for engine tests providing common setup and utilities."""

    @pytest.fixture(autouse=True)
    async def setup_test(self, state_manager: StateManager):
        """Setup test environment with state manager.

        Args:
            state_manager: The state manager fixture
        """
        self.state_manager = state_manager
        self.executor = ProcessExecutor(state_manager)

        # Clear Redis before each test
        await state_manager.redis.flushdb()

        yield

        # Clean up after test
        await state_manager.redis.flushdb()

    def create_sequence_flow(
        self, start_id: str = "Start_1", task_id: str = "Task_1", end_id: str = "End_1"
    ) -> dict:
        """Create a simple sequence flow process graph.

        Args:
            start_id: ID for the start event
            task_id: ID for the task
            end_id: ID for the end event

        Returns:
            dict: Process graph definition with nodes and flows
        """
        return {
            "nodes": [
                Event(
                    id=start_id,
                    type="event",
                    event_type=EventType.START,
                    outgoing=[f"Flow_{start_id}_to_{task_id}"],
                ),
                Task(
                    id=task_id,
                    type="task",
                    incoming=[f"Flow_{start_id}_to_{task_id}"],
                    outgoing=[f"Flow_{task_id}_to_{end_id}"],
                ),
                Event(
                    id=end_id,
                    type="event",
                    event_type=EventType.END,
                    incoming=[f"Flow_{task_id}_to_{end_id}"],
                ),
            ],
            "flows": [
                {
                    "id": f"Flow_{start_id}_to_{task_id}",
                    "source_ref": start_id,
                    "target_ref": task_id,
                },
                {
                    "id": f"Flow_{task_id}_to_{end_id}",
                    "source_ref": task_id,
                    "target_ref": end_id,
                },
            ],
        }

    def create_parallel_flow(self, tasks: List[str] = None) -> dict:
        """Create a parallel gateway process graph.

        Args:
            tasks: List of task IDs to include in parallel branches

        Returns:
            dict: Process graph definition with parallel flow
        """
        if not tasks:
            tasks = ["Task_1", "Task_2"]

        start_id = "Start_1"
        split_gateway_id = "Gateway_1"
        join_gateway_id = "Gateway_2"
        end_id = "End_1"

        nodes = [
            Event(
                id=start_id,
                type="event",
                event_type=EventType.START,
                outgoing=[f"Flow_to_split"],
            ),
            Gateway(
                id=split_gateway_id,
                type="gateway",
                gateway_type=GatewayType.PARALLEL,
                incoming=[f"Flow_to_split"],
                outgoing=[f"Flow_to_{task}" for task in tasks],
            ),
        ]

        flows = [
            {
                "id": "Flow_to_split",
                "source_ref": start_id,
                "target_ref": split_gateway_id,
            }
        ]

        # Add task nodes
        for task_id in tasks:
            nodes.append(
                Task(
                    id=task_id,
                    type="task",
                    incoming=[f"Flow_to_{task_id}"],
                    outgoing=[f"Flow_from_{task_id}"],
                )
            )
            flows.append(
                {
                    "id": f"Flow_to_{task_id}",
                    "source_ref": split_gateway_id,
                    "target_ref": task_id,
                }
            )
            flows.append(
                {
                    "id": f"Flow_from_{task_id}",
                    "source_ref": task_id,
                    "target_ref": join_gateway_id,
                }
            )

        # Add join gateway and end event
        nodes.extend(
            [
                Gateway(
                    id=join_gateway_id,
                    type="gateway",
                    gateway_type=GatewayType.PARALLEL,
                    incoming=[f"Flow_from_{task}" for task in tasks],
                    outgoing=["Flow_to_end"],
                ),
                Event(
                    id=end_id,
                    type="event",
                    event_type=EventType.END,
                    incoming=["Flow_to_end"],
                ),
            ]
        )
        flows.append(
            {"id": "Flow_to_end", "source_ref": join_gateway_id, "target_ref": end_id}
        )

        return {"nodes": nodes, "flows": flows}

    def create_exclusive_flow(self, conditions: Dict[str, str]) -> dict:
        """Create an exclusive gateway process graph with conditions.

        Args:
            conditions: Dictionary mapping task IDs to their conditions

        Returns:
            dict: Process graph definition with exclusive gateway
        """
        start_id = "Start_1"
        gateway_id = "Gateway_1"
        end_id = "End_1"

        nodes = [
            Event(
                id=start_id,
                type="event",
                event_type=EventType.START,
                outgoing=["Flow_to_gateway"],
            ),
            Gateway(
                id=gateway_id,
                type="gateway",
                gateway_type=GatewayType.EXCLUSIVE,
                incoming=["Flow_to_gateway"],
                outgoing=[f"Flow_to_{task}" for task in conditions.keys()],
            ),
        ]

        flows = [
            {"id": "Flow_to_gateway", "source_ref": start_id, "target_ref": gateway_id}
        ]

        # Add conditional paths
        for task_id, condition in conditions.items():
            nodes.append(
                Task(
                    id=task_id,
                    type="task",
                    incoming=[f"Flow_to_{task_id}"],
                    outgoing=[f"Flow_from_{task_id}"],
                )
            )
            flows.extend(
                [
                    {
                        "id": f"Flow_to_{task_id}",
                        "source_ref": gateway_id,
                        "target_ref": task_id,
                        "condition_expression": condition,
                    },
                    {
                        "id": f"Flow_from_{task_id}",
                        "source_ref": task_id,
                        "target_ref": end_id,
                    },
                ]
            )

        nodes.append(
            Event(
                id=end_id,
                type="event",
                event_type=EventType.END,
                incoming=[f"Flow_from_{task}" for task in conditions.keys()],
            )
        )

        return {"nodes": nodes, "flows": flows}

    def create_subprocess_flow(
        self, subprocess_id: str = "Subprocess_1", next_task_id: str = "Task_1"
    ) -> dict:
        """Create a process graph with a subprocess.

        Args:
            subprocess_id: ID for the subprocess task
            next_task_id: ID for the task after subprocess

        Returns:
            dict: Process graph definition with subprocess
        """
        start_id = "Start_1"
        end_id = "End_1"

        return {
            "nodes": [
                Event(
                    id=start_id,
                    type="event",
                    event_type=EventType.START,
                    outgoing=["Flow_1"],
                ),
                Task(
                    id=subprocess_id,
                    type="task",
                    incoming=["Flow_1"],
                    outgoing=["Flow_2"],
                    extensions={"subprocess": True},
                ),
                Task(
                    id=next_task_id,
                    type="task",
                    incoming=["Flow_2"],
                    outgoing=["Flow_3"],
                ),
                Event(
                    id=end_id,
                    type="event",
                    event_type=EventType.END,
                    incoming=["Flow_3"],
                ),
            ],
            "flows": [
                {"id": "Flow_1", "source_ref": start_id, "target_ref": subprocess_id},
                {
                    "id": "Flow_2",
                    "source_ref": subprocess_id,
                    "target_ref": next_task_id,
                },
                {"id": "Flow_3", "source_ref": next_task_id, "target_ref": end_id},
            ],
        }

    def create_multi_instance_flow(
        self, activity_id: str = "Activity_1", next_task_id: str = "Task_1"
    ) -> dict:
        """Create a process graph with a multi-instance activity.

        Args:
            activity_id: ID for the multi-instance activity
            next_task_id: ID for the task after multi-instance activity

        Returns:
            dict: Process graph definition with multi-instance activity
        """
        start_id = "Start_1"
        end_id = "End_1"

        return {
            "nodes": [
                Event(
                    id=start_id,
                    type="event",
                    event_type=EventType.START,
                    outgoing=["Flow_1"],
                ),
                Task(
                    id=activity_id,
                    type="task",
                    incoming=["Flow_1"],
                    outgoing=["Flow_2"],
                    extensions={"multi_instance": True},
                ),
                Task(
                    id=next_task_id,
                    type="task",
                    incoming=["Flow_2"],
                    outgoing=["Flow_3"],
                ),
                Event(
                    id=end_id,
                    type="event",
                    event_type=EventType.END,
                    incoming=["Flow_3"],
                ),
            ],
            "flows": [
                {"id": "Flow_1", "source_ref": start_id, "target_ref": activity_id},
                {"id": "Flow_2", "source_ref": activity_id, "target_ref": next_task_id},
                {"id": "Flow_3", "source_ref": next_task_id, "target_ref": end_id},
            ],
        }

    async def setup_multi_instance_token(
        self,
        instance_id: str,
        activity_id: str,
        collection_data: List[str],
        is_parallel: bool = True,
    ) -> Token:
        """Helper to set up a multi-instance activity token with collection data.

        Args:
            instance_id: Process instance ID
            activity_id: Activity node ID
            collection_data: List of items to process
            is_parallel: Whether to use parallel execution

        Returns:
            Token: Configured token for multi-instance activity
        """
        token = await self.executor.create_initial_token(instance_id, activity_id)
        token.data["collection"] = collection_data
        token.data["is_parallel"] = is_parallel
        return token
