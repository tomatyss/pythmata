import asyncio
from typing import Dict, List, Optional, Union

from pythmata.core.engine.call_activity_manager import CallActivityManager
from pythmata.core.engine.instance import ProcessInstanceManager
from pythmata.core.engine.multi_instance_manager import MultiInstanceManager
from pythmata.core.engine.node_executor import NodeExecutor
from pythmata.core.engine.subprocess_manager import SubprocessManager
from pythmata.core.engine.token import Token, TokenState
from pythmata.core.engine.token_manager import TokenManager
from pythmata.core.engine.validator import ProcessValidator
from pythmata.core.state import StateManager
from pythmata.core.types import Event, Gateway, Task
from pythmata.utils.logger import get_logger

logger = get_logger(__name__)


class ProcessExecutionLimitError(Exception):
    """Raised when process execution exceeds iteration limits."""


def handle_execution_error(func):
    """
    Decorator for handling execution errors in process methods.

    Args:
        func: The async function to wrap with error handling

    Returns:
        Wrapped function that includes error handling and error propagation to instance manager
    """

    async def wrapper(self, *args, **kwargs):
        try:
            return await func(self, *args, **kwargs)
        except Exception as e:
            # Extract instance_id and node_id from arguments if available
            instance_id = None
            node_id = None

            # First argument after self should be token
            if args and hasattr(args[0], "instance_id"):
                instance_id = args[0].instance_id

            # Second argument might be node or node_id
            if len(args) > 1:
                if hasattr(args[1], "id"):
                    node_id = args[1].id
                else:
                    node_id = args[1]
            # Or it might be explicitly passed as node_id
            elif "node_id" in kwargs:
                node_id = kwargs["node_id"]

            if hasattr(self, "instance_manager") and self.instance_manager:
                await self.instance_manager.handle_error(instance_id, e, node_id)
            raise

    return wrapper


class ProcessExecutor:
    """
    Executes BPMN processes by orchestrating token movement through nodes.

    Coordinates between specialized components:
    - NodeExecutor: Handles execution of individual nodes
    - ProcessValidator: Validates process graph structure
    - TokenManager: Manages token lifecycle
    - Various activity managers for specific process features
    """

    # Maximum number of iterations to prevent infinite loops
    MAX_ITERATIONS = 1000

    def __init__(
        self,
        state_manager: StateManager,
        instance_manager: Optional[ProcessInstanceManager] = None,
    ):
        """
        Initialize process executor with required components.

        Args:
            state_manager: Manager for process state
            instance_manager: Optional manager for process instances
        """
        self.state_manager = state_manager
        self.instance_manager = instance_manager

        # Initialize specialized components
        self.validator = ProcessValidator()
        self.token_manager = TokenManager(state_manager)  # Create token_manager first
        self.node_executor = NodeExecutor(
            state_manager, self.token_manager, instance_manager
        )  # Pass token_manager and instance_manager to node_executor
        self.subprocess_manager = SubprocessManager(state_manager)
        self.call_activity_manager = CallActivityManager(state_manager)
        self.multi_instance_manager = MultiInstanceManager(state_manager)
        self.event_handler = self.node_executor.event_handler

    # Public methods that tests expect (delegating to specialized managers)
    @handle_execution_error
    async def create_initial_token(
        self, instance_id: str, start_event_id: str
    ) -> Token:
        """Create a new token at a start event."""
        return await self.token_manager.create_initial_token(
            instance_id, start_event_id
        )

    @handle_execution_error
    async def move_token(self, token: Token, target_node_id: str) -> Token:
        """Move a token to a new node."""
        return await self.token_manager.move_token(
            token, target_node_id, self.instance_manager
        )

    @handle_execution_error
    async def consume_token(self, token: Token) -> None:
        """Consume a token."""
        await self.token_manager.consume_token(token)

    @handle_execution_error
    async def split_token(
        self, token: Token, target_node_ids: List[str]
    ) -> List[Token]:
        """Split a token into multiple tokens."""
        return await self.token_manager.split_token(token, target_node_ids, self.instance_manager)

    @handle_execution_error
    async def enter_subprocess(self, token: Token, subprocess_id: str) -> Token:
        """Move a token into a subprocess."""
        return await self.subprocess_manager.enter_subprocess(token, subprocess_id)

    @handle_execution_error
    async def exit_subprocess(self, token: Token, next_task_id: str) -> Token:
        """Move a token out of a subprocess."""
        return await self.subprocess_manager.exit_subprocess(token, next_task_id)

    @handle_execution_error
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

    @handle_execution_error
    async def create_call_activity(self, token: Token) -> Token:
        """Create a new process instance for a call activity."""
        return await self.call_activity_manager.create_call_activity(token)

    @handle_execution_error
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

    @handle_execution_error
    async def propagate_call_activity_error(
        self, token: Token, error_boundary_id: str
    ) -> Token:
        """Propagate an error from called process."""
        return await self.call_activity_manager.propagate_call_activity_error(
            token, error_boundary_id
        )

    @handle_execution_error
    async def create_parallel_instances(self, token: Token) -> List[Token]:
        """Create parallel instances for a multi-instance activity."""
        return await self.multi_instance_manager.create_parallel_instances(token)

    @handle_execution_error
    async def create_sequential_instance(self, token: Token, index: int) -> Token:
        """Create a sequential instance for a multi-instance activity."""
        return await self.multi_instance_manager.create_sequential_instance(
            token, index
        )

    @handle_execution_error
    async def complete_parallel_instance(
        self, token: Token, total_instances: int
    ) -> Optional[Token]:
        """Complete a parallel instance."""
        return await self.multi_instance_manager.complete_parallel_instance(
            token, total_instances
        )

    @handle_execution_error
    async def complete_sequential_instance(
        self, token: Token, total_instances: int
    ) -> Token:
        """Complete a sequential instance."""
        return await self.multi_instance_manager.complete_sequential_instance(
            token, total_instances
        )

    @handle_execution_error
    async def handle_empty_collection(self, token: Token, next_task_id: str) -> Token:
        """Handle empty collection in multi-instance activity."""
        return await self.multi_instance_manager.handle_empty_collection(
            token, next_task_id
        )

    @handle_execution_error
    async def trigger_event_subprocess(
        self, token: Token, event_subprocess_id: str, event_data: Dict
    ) -> Token:
        """Trigger an event subprocess."""
        return await self.event_handler.trigger_event_subprocess(
            token, event_subprocess_id, event_data
        )

    # Core execution methods
    @handle_execution_error
    async def execute_process(self, instance_id: str, process_graph: Dict) -> None:
        """
        Execute process instance.

        Args:
            instance_id: ID of the process instance
            process_graph: Process graph definition

        Raises:
            ProcessGraphValidationError: If process graph validation fails
            ProcessExecutionLimitError: If execution exceeds iteration limit
        """
        logger.info(f"Starting process execution for instance {instance_id}")

        # Validate process graph before execution
        logger.info("Validating process graph...")
        self.validator.validate_process_graph(process_graph)
        logger.info("Process graph validation successful")

        # Check if we need to create an initial token
        tokens = await self.state_manager.get_token_positions(instance_id)
        if not tokens:
            logger.info(
                f"No tokens found, creating initial token for instance {instance_id}"
            )
            # Find start event
            start_event = next(
                (
                    node
                    for node in process_graph["nodes"]
                    if hasattr(node, "event_type") and node.event_type == "start"
                ),
                None,
            )
            if not start_event:
                raise ValueError("No start event found in process definition")
            await self.create_initial_token(instance_id, start_event.id)
            logger.info(f"Created initial token at {start_event.id}")

        iteration_count = 0
        while True:
            # Check iteration limit
            iteration_count += 1
            if iteration_count > self.MAX_ITERATIONS:
                raise ProcessExecutionLimitError(
                    f"Process execution exceeded {self.MAX_ITERATIONS} iterations"
                )
            # Get current tokens
            tokens = await self.state_manager.get_token_positions(instance_id)
            if not tokens:
                logger.info(f"No tokens found for instance {instance_id}")
                break

            # Check if all tokens are at end events or in final state
            active_tokens = [
                t for t in tokens if t.get("state") == TokenState.ACTIVE.value
            ]
            logger.info(
                f"Found {len(active_tokens)} active tokens out of {len(tokens)} total tokens"
            )

            if not active_tokens:
                logger.info(
                    f"No active tokens remaining for instance {instance_id}, process complete"
                )
                break

            # Execute each active token
            for token_data in active_tokens:
                token = Token.from_dict(token_data)
                # Get current node and its outgoing flows
                current_node = self._find_node(process_graph, token.node_id)
                if not current_node:
                    logger.error(f"Node {token.node_id} not found in process graph")
                    continue

                # Execute the current node
                logger.info(
                    f"Processing token {token.id} at node {current_node.id} (type: {type(current_node).__name__})"
                )
                await self.execute_node(token, current_node, process_graph)

                # Check if token still exists (hasn't been moved by node execution)
                stored_token = await self.state_manager.get_token(
                    instance_id=token.instance_id, node_id=token.node_id
                )
                if not stored_token:
                    logger.info(f"Token {token.id} already moved by node execution")
                    continue

                # Each node type handler manages its own token movement
                if isinstance(current_node, (Task, Gateway, Event)):
                    logger.info(
                        f"{type(current_node).__name__} {current_node.id} handling its own token movement"
                    )

            # Small delay to prevent tight loop
            await asyncio.sleep(0.1)

        # Process complete
        if self.instance_manager:
            await self.instance_manager.complete_instance(instance_id)

    @handle_execution_error
    async def execute_node(
        self, token: Token, node: Union[Task, Gateway, Event], process_graph: Dict
    ) -> None:
        """
        Execute a process node.

        Args:
            token: Current process token
            node: Node to execute
            process_graph: Complete process graph
        """
        await self.node_executor.execute_node(token, node, process_graph)

    def _find_node(
        self, process_graph: Dict, node_id: str
    ) -> Optional[Union[Task, Gateway, Event]]:
        """Find node in process graph by ID."""
        return next(
            (node for node in process_graph["nodes"] if node.id == node_id), None
        )
