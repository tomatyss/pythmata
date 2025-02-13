import asyncio
import logging
from typing import Dict, List, Optional, Union
from uuid import UUID

from pythmata.api.schemas import ProcessVariableValue
from pythmata.core.engine.call_activity_manager import CallActivityManager
from pythmata.core.engine.event_handler import EventHandler
from pythmata.core.engine.gateway_handler import GatewayHandler
from pythmata.core.engine.multi_instance_manager import MultiInstanceManager
from pythmata.core.engine.subprocess_manager import SubprocessManager
from pythmata.core.engine.token import Token, TokenState
from pythmata.core.engine.token_manager import TokenManager
from pythmata.core.state import StateManager
from pythmata.core.types import Event, Gateway, Task
from pythmata.models.process import ProcessStatus

logger = logging.getLogger(__name__)


class ProcessExecutor:
    """
    Executes BPMN processes by orchestrating token movement through nodes.

    The executor coordinates between specialized managers for different aspects
    of process execution:
    - TokenManager: Basic token operations
    - SubprocessManager: Subprocess handling
    - CallActivityManager: Call activity handling
    - MultiInstanceManager: Multi-instance activities
    - GatewayHandler: Gateway logic
    - EventHandler: Event processing
    """

    def __init__(
        self,
        state_manager: StateManager,
        instance_manager: Optional["ProcessInstanceManager"] = None,
    ):
        self.state_manager = state_manager
        self.instance_manager = instance_manager

        # Initialize specialized managers
        self.token_manager = TokenManager(state_manager)
        self.subprocess_manager = SubprocessManager(state_manager)
        self.call_activity_manager = CallActivityManager(state_manager)
        self.multi_instance_manager = MultiInstanceManager(state_manager)
        self.gateway_handler = GatewayHandler(state_manager)
        self.event_handler = EventHandler(state_manager)

    # Public methods that tests expect (delegating to specialized managers)
    async def create_initial_token(
        self, instance_id: str, start_event_id: str
    ) -> Token:
        """Create a new token at a start event."""
        return await self.token_manager.create_initial_token(
            instance_id, start_event_id
        )

    async def move_token(self, token: Token, target_node_id: str) -> Token:
        """Move a token to a new node."""
        return await self.token_manager.move_token(
            token, target_node_id, self.instance_manager
        )

    async def consume_token(self, token: Token) -> None:
        """Consume a token."""
        await self.token_manager.consume_token(token)

    async def split_token(
        self, token: Token, target_node_ids: List[str]
    ) -> List[Token]:
        """Split a token into multiple tokens."""
        return await self.token_manager.split_token(token, target_node_ids)

    async def enter_subprocess(self, token: Token, subprocess_id: str) -> Token:
        """Move a token into a subprocess."""
        return await self.subprocess_manager.enter_subprocess(token, subprocess_id)

    async def exit_subprocess(self, token: Token, next_task_id: str) -> Token:
        """Move a token out of a subprocess."""
        return await self.subprocess_manager.exit_subprocess(token, next_task_id)

    async def complete_subprocess(
        self,
        token: Token,
        next_task_id: str,
        output_vars: Optional[Dict[str, str]] = None,
    ) -> Token:
        """Complete a subprocess."""
        return await self.subprocess_manager.complete_subprocess(
            token, next_task_id, output_vars
        )

    async def create_call_activity(self, token: Token) -> Token:
        """Create a new process instance for a call activity."""
        return await self.call_activity_manager.create_call_activity(token)

    async def complete_call_activity(
        self,
        token: Token,
        next_task_id: str,
        output_vars: Optional[Dict[str, str]] = None,
    ) -> Token:
        """Complete a call activity."""
        return await self.call_activity_manager.complete_call_activity(
            token, next_task_id, output_vars
        )

    async def propagate_call_activity_error(
        self, token: Token, error_boundary_id: str
    ) -> Token:
        """Propagate an error from called process."""
        return await self.call_activity_manager.propagate_call_activity_error(
            token, error_boundary_id
        )

    async def create_parallel_instances(self, token: Token) -> List[Token]:
        """Create parallel instances for a multi-instance activity."""
        return await self.multi_instance_manager.create_parallel_instances(token)

    async def create_sequential_instance(self, token: Token, index: int) -> Token:
        """Create a sequential instance for a multi-instance activity."""
        return await self.multi_instance_manager.create_sequential_instance(
            token, index
        )

    async def complete_parallel_instance(
        self, token: Token, total_instances: int
    ) -> Optional[Token]:
        """Complete a parallel instance."""
        return await self.multi_instance_manager.complete_parallel_instance(
            token, total_instances
        )

    async def complete_sequential_instance(
        self, token: Token, total_instances: int
    ) -> Token:
        """Complete a sequential instance."""
        return await self.multi_instance_manager.complete_sequential_instance(
            token, total_instances
        )

    async def handle_empty_collection(self, token: Token, next_task_id: str) -> Token:
        """Handle empty collection in multi-instance activity."""
        return await self.multi_instance_manager.handle_empty_collection(
            token, next_task_id
        )

    async def trigger_event_subprocess(
        self, token: Token, event_subprocess_id: str, event_data: Dict
    ) -> Token:
        """Trigger an event subprocess."""
        return await self.event_handler.trigger_event_subprocess(
            token, event_subprocess_id, event_data
        )

    # Core execution methods
    async def execute_process(self, instance_id: str, process_graph: Dict) -> None:
        """Execute process instance."""
        try:
            while True:
                # Get current tokens
                tokens = await self.state_manager.get_token_positions(instance_id)
                if not tokens:
                    logger.info(f"No active tokens for instance {instance_id}")
                    break

                # Check if all tokens are at end events or in final state
                active_tokens = [
                    t for t in tokens if t.get("state") == TokenState.ACTIVE.value
                ]
                if not active_tokens:
                    logger.info(
                        f"No active tokens remaining for instance {instance_id}"
                    )
                    break

                # Execute each active token
                for token_data in active_tokens:
                    token = Token.from_dict(token_data)
                    node = self._find_node(process_graph, token.node_id)
                    if node:
                        await self.execute_node(token, node, process_graph)
                    else:
                        logger.error(f"Node {token.node_id} not found in process graph")

                # Small delay to prevent tight loop
                await asyncio.sleep(0.1)

            # Process complete
            if self.instance_manager:
                await self.instance_manager.complete_instance(instance_id)

        except Exception as e:
            logger.error(f"Error executing process instance {instance_id}: {str(e)}")
            if self.instance_manager:
                await self.instance_manager.handle_error(instance_id, e)
            raise

    async def execute_node(
        self, token: Token, node: Union[Task, Gateway, Event], process_graph: Dict
    ) -> None:
        """Execute a process node."""
        try:
            if isinstance(node, Task):
                await self.execute_task(token, node)
            elif isinstance(node, Gateway):
                await self.gateway_handler.handle_gateway(token, node, process_graph)
            elif isinstance(node, Event):
                await self.event_handler.handle_event(token, node)
            else:
                logger.warning(f"Unknown node type: {type(node)}")

        except Exception as e:
            logger.error(
                f"Error executing node {node.id} for instance {token.instance_id}: {str(e)}"
            )
            if self.instance_manager:
                await self.instance_manager.handle_error(token.instance_id, e, node.id)
            raise

    async def execute_task(self, token: Token, task: Task) -> None:
        """Execute a task."""
        try:
            if task.script:
                await self._execute_script_task(token, task)

            # Move token to next node
            outgoing = task.outgoing[0] if task.outgoing else None
            if outgoing:
                await self.token_manager.move_token(token, outgoing)
            else:
                logger.warning(f"Task {task.id} has no outgoing flows")

        except Exception as e:
            logger.error(f"Error executing task {task.id}: {str(e)}")
            raise

    async def _execute_script_task(self, token: Token, task: Task) -> None:
        """Execute a script task."""
        # Get process variables for script context
        variables = await self.state_manager.get_variables(
            instance_id=token.instance_id, scope_id=token.scope_id
        )

        # Create safe execution context
        context = {
            "token": token,
            "variables": variables,
            "result": None,  # For script output
            "set_variable": lambda name, value: self.state_manager.set_variable(
                instance_id=token.instance_id,
                name=name,
                variable=ProcessVariableValue(type=type(value).__name__, value=value),
                scope_id=token.scope_id,
            ),
            # Safe built-ins
            "len": len,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "sum": sum,
            "min": min,
            "max": max,
        }

        # Execute script in restricted environment
        try:
            exec(
                task.script,
                {"__builtins__": {}},  # No built-ins
                context,  # Our safe context
            )

            # Store script result if any
            if context["result"] is not None:
                await self.state_manager.set_variable(
                    instance_id=token.instance_id,
                    name=f"{task.id}_result",
                    variable=ProcessVariableValue(
                        type=type(context["result"]).__name__,
                        value=context["result"],
                    ),
                    scope_id=token.scope_id,
                )
        except Exception as script_error:
            logger.error(
                f"Script execution error in task {task.id}: {str(script_error)}"
            )
            if self.instance_manager:
                await self.instance_manager.handle_error(
                    token.instance_id, script_error, task.id
                )
            raise

    def _find_node(
        self, process_graph: Dict, node_id: str
    ) -> Optional[Union[Task, Gateway, Event]]:
        """Find node in process graph by ID."""
        return next(
            (node for node in process_graph["nodes"] if node.id == node_id), None
        )
