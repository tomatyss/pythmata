from typing import Dict, Union

from pythmata.core.engine.event_handler import EventHandler
from pythmata.core.engine.gateway_handler import GatewayHandler
from pythmata.core.engine.script_executor import ScriptExecutor
from pythmata.core.engine.token import Token
from pythmata.core.state import StateManager
from pythmata.core.types import Event, Gateway, Task
from pythmata.utils.logger import get_logger

logger = get_logger(__name__)


class NodeExecutor:
    """
    Handles execution of process nodes based on their type.

    Coordinates between different handlers for:
    - Tasks (including script tasks)
    - Gateways
    - Events

    Features:
    - Type-specific node execution
    - Safe state transitions
    - Error handling and logging
    """

    def __init__(self, state_manager: StateManager, token_manager=None):
        """
        Initialize node executor with required handlers.

        Args:
            state_manager: Manager for process state
            token_manager: Optional token manager for token operations
        """
        self.state_manager = state_manager
        self.token_manager = token_manager
        self.script_executor = ScriptExecutor(state_manager)
        self.gateway_handler = GatewayHandler(state_manager, token_manager)
        self.event_handler = EventHandler(state_manager, token_manager)

    async def execute_node(
        self, token: Token, node: Union[Task, Gateway, Event], process_graph: Dict
    ) -> None:
        """
        Execute a process node based on its type.

        Args:
            token: Current process token
            node: Node to execute
            process_graph: Complete process graph

        Raises:
            Exception: If node execution fails
        """
        try:
            if isinstance(node, Task):
                await self._execute_task(token, node, process_graph)
            elif isinstance(node, Gateway):
                await self.gateway_handler.handle_gateway(token, node, process_graph)
            elif isinstance(node, Event):
                await self.event_handler.handle_event(token, node, process_graph)
            else:
                logger.warning(f"Unknown node type: {type(node)}")
        except Exception as e:
            logger.error(f"Node execution failed for {node.id}: {str(e)}")
            raise

    async def _execute_task(
        self, token: Token, task: Task, process_graph: Dict
    ) -> None:
        """
        Execute a task node.

        Args:
            token: Current process token
            task: Task to execute
            process_graph: Complete process graph

        Raises:
            Exception: If task execution fails
        """
        try:
            # Execute script if present
            if task.script:
                await self.script_executor.execute_script(token, task)

            # Move token to next node if there are outgoing flows
            if task.outgoing:
                next_flow = next(
                    (
                        flow
                        for flow in process_graph["flows"]
                        if (flow["id"] if isinstance(flow, dict) else flow.id)
                        == task.outgoing[0]
                    ),
                    None,
                )
                if next_flow:
                    target_ref = (
                        next_flow["target_ref"]
                        if isinstance(next_flow, dict)
                        else next_flow.target_ref
                    )
                    logger.info(f"Moving token {token.id} to {target_ref} via task")
                    if self.token_manager:
                        await self.token_manager.move_token(token, target_ref)
                    else:
                        logger.error(
                            "TokenManager not available for task token movement"
                        )
                else:
                    logger.error(f"Flow {task.outgoing[0]} not found in process graph")
        except Exception as e:
            logger.error(f"Task execution failed for {task.id}: {str(e)}")
            raise
