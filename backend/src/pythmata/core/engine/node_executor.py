from typing import Dict, List, Optional, Union

from pythmata.core.engine.event_handler import EventHandler
from pythmata.core.engine.gateway_handler import GatewayHandler
from pythmata.core.engine.script_executor import ScriptExecutor
from pythmata.core.engine.service_executor import ServiceTaskExecutor
from pythmata.core.engine.token import Token, TokenState
from pythmata.core.engine.transaction import Transaction, TransactionContext
from pythmata.core.state import StateManager
from pythmata.core.types import Event, EventType, Gateway, Task
from pythmata.utils.logger import get_logger

logger = get_logger(__name__)


class CompensationHandler:
    """Handles compensation events and activities."""

    def __init__(self, state_manager: StateManager, token_manager=None, instance_manager=None):
        """
        Initialize compensation handler.

        Args:
            state_manager: Manager for process state
            token_manager: Optional token manager for token operations
            instance_manager: Optional process instance manager
        """
        self.state_manager = state_manager
        self.token_manager = token_manager
        self.instance_manager = instance_manager
        
    async def handle_compensation_event(
        self, token: Token, event: Event, process_graph: Dict
    ) -> None:
        """
        Handle compensation event processing.

        Args:
            token: Current execution token
            event: Compensation event definition
            process_graph: Process graph for flow resolution
        """
        logger.info(f"Handling compensation event: {event.id}")
        
        # Check the type of compensation event
        if event.event_type == EventType.BOUNDARY:
            await self._handle_compensation_boundary_event(token, event, process_graph)
        elif event.event_definition == "compensation":
            if event.event_type == EventType.INTERMEDIATE:
                # This is a compensation throw event - trigger compensation
                await self._handle_compensation_throw_event(token, event, process_graph)
            elif event.event_type == EventType.END:
                # This is a compensation end event - trigger compensation before ending
                await self._handle_compensation_end_event(token, event, process_graph)
                
    async def _handle_compensation_boundary_event(
        self, token: Token, event: Event, process_graph: Dict
    ) -> None:
        """
        Handle a compensation boundary event.
        
        Args:
            token: Current execution token
            event: Compensation boundary event
            process_graph: Process graph for flow resolution
        """
        # Find the compensation handler task (connected to this boundary event)
        compensation_handler = None
        
        # Look for the connected flow
        if event.outgoing:
            flow_id = event.outgoing[0]
            flow = next((f for f in process_graph["flows"] if f["id"] == flow_id), None)
            
            if flow:
                handler_id = flow["target_ref"]
                # Find the handler node
                compensation_handler = next(
                    (n for n in process_graph["nodes"] if n["id"] == handler_id), None
                )
        
        if not compensation_handler:
            logger.warning(f"No compensation handler found for event {event.id}")
            return
            
        logger.info(f"Registering compensation handler {compensation_handler['id']} for {event.attached_to}")
        
        # Store the compensation information in the process state
        compensation_mapping = {
            "activity_id": event.attached_to,
            "handler_id": compensation_handler["id"],
            "boundary_event_id": event.id,
            "wait_for_completion": event.wait_for_completion
        }
        
        # Store this mapping in the state manager
        await self.state_manager.store_compensation_handler(
            instance_id=token.instance_id,
            activity_id=event.attached_to,
            handler_data=compensation_mapping
        )
        
    async def _handle_compensation_throw_event(
        self, token: Token, event: Event, process_graph: Dict
    ) -> None:
        """
        Handle a compensation throw event that triggers compensation.
        
        Args:
            token: Current execution token
            event: Compensation throw event
            process_graph: Process graph for flow resolution
        """
        logger.info(f"Processing compensation throw event: {event.id}")
        
        # Determine compensation scope:
        # 1. If activityRef is specified, compensate only that activity
        # 2. If no activityRef, compensate all activities in the current scope
        if event.activity_ref:
            # Get the specific handler for this activity
            handler_data = await self.state_manager.get_compensation_handler(
                instance_id=token.instance_id,
                activity_id=event.activity_ref
            )
            
            if handler_data:
                await self._trigger_compensation_handler(token, handler_data, process_graph)
            else:
                logger.warning(f"No compensation handler found for activity {event.activity_ref}")
        else:
            # Get all compensation handlers registered in this scope
            handlers = await self.state_manager.get_all_compensation_handlers(
                instance_id=token.instance_id
            )
            
            # Execute handlers in reverse order of registration (LIFO)
            for handler_data in reversed(handlers):
                await self._trigger_compensation_handler(token, handler_data, process_graph)
        
        # After compensation, continue with flow if there's an outgoing sequence flow
        if event.outgoing and self.token_manager:
            flow = next(
                (f for f in process_graph["flows"] if f["id"] == event.outgoing[0]),
                None
            )
            if flow:
                await self.token_manager.move_token(
                    token, flow["target_ref"], self.instance_manager
                )
            
    async def _handle_compensation_end_event(
        self, token: Token, event: Event, process_graph: Dict
    ) -> None:
        """
        Handle a compensation end event.
        
        Args:
            token: Current execution token
            event: Compensation end event
            process_graph: Process graph for flow resolution
        """
        # Similar to throw event, but consumes the token after compensation is complete
        await self._handle_compensation_throw_event(token, event, process_graph)
        
        # Consume the token since this is an end event
        if self.token_manager:
            await self.token_manager.consume_token(token)
        
    async def _trigger_compensation_handler(
        self, token: Token, handler_data: Dict, process_graph: Dict
    ) -> None:
        """
        Trigger a specific compensation handler.
        
        Args:
            token: Current execution token
            handler_data: Compensation handler data with activity_id and handler_id
            process_graph: Process graph for flow resolution
        """
        if not self.token_manager:
            logger.error("TokenManager not available for compensation handling")
            return
            
        logger.info(
            f"Triggering compensation handler {handler_data['handler_id']} "
            f"for activity {handler_data['activity_id']}"
        )
        
        # Create a new token for the compensation handler with COMPENSATION state
        compensation_token = Token(
            instance_id=token.instance_id,
            node_id=handler_data["handler_id"],
            state=TokenState.COMPENSATION,
            data={
                "compensated_activity_id": handler_data["activity_id"],
                "original_token_data": token.data,
                "boundary_event_id": handler_data.get("boundary_event_id")
            }
        )
        
        # Add the compensation token
        await self.state_manager.add_token(
            instance_id=compensation_token.instance_id,
            node_id=compensation_token.node_id,
            data=compensation_token.to_dict()
        )
        
        # Execute the handler
        handler_node = next(
            (n for n in process_graph["nodes"] if n["id"] == handler_data["handler_id"]),
            None
        )
        
        if handler_node and self.instance_manager:
            # Queue the compensation handler for execution
            await self.instance_manager.queue_node_execution(
                compensation_token, handler_node, process_graph
            )


class NodeExecutor:
    """
    Executes individual BPMN nodes based on their type.

    Responsible for task execution, gateway handling, and event processing.
    Delegates to specialized components for specific node types.
    """

    def __init__(
        self, state_manager: StateManager, token_manager=None, instance_manager=None
    ):
        """
        Initialize node executor with required components.

        Args:
            state_manager: Manager for process state
            token_manager: Optional token manager for token operations
            instance_manager: Optional process instance manager
        """
        self.state_manager = state_manager
        self.token_manager = token_manager
        self.instance_manager = instance_manager

        # Initialize specialized handlers
        self.script_executor = ScriptExecutor()
        self.service_executor = ServiceTaskExecutor()
        self.gateway_handler = GatewayHandler(state_manager, token_manager)
        self.event_handler = EventHandler(
            state_manager, token_manager, instance_manager
        )
        self.compensation_handler = CompensationHandler(
            state_manager, token_manager, instance_manager
        )

    async def execute_node(
        self, token: Token, node: Union[Task, Gateway, Event], process_graph: Dict
    ) -> Token:
        """
        Execute a BPMN node based on its type.

        Args:
            token: Current execution token
            node: BPMN node to execute
            process_graph: Process graph for flow resolution

        Returns:
            Updated token after execution
        """
        logger.info(f"Executing node: {node.id} of type {node.type}")

        # Execute based on node type
        if hasattr(node, "type") and "task" in node.type.lower():
            return await self._execute_task(token, node, process_graph)
        elif hasattr(node, "type") and "gateway" in node.type.lower():
            return await self._execute_gateway(token, node, process_graph)
        elif hasattr(node, "type") and "event" in node.type.lower():
            return await self._execute_event(token, node, process_graph)
        else:
            logger.warning(f"Unknown node type: {node.type}")
            return token

    async def _execute_task(
        self, token: Token, task: Task, process_graph: Dict
    ) -> Token:
        """Execute a task node."""
        logger.info(f"Executing task: {task.id}")

        # Check if this is a compensation task
        if task.is_for_compensation and token.state != TokenState.COMPENSATION:
            logger.info(f"Skipping compensation task {task.id} in normal flow")
            # Skip and move to outgoing flow if there is one
            if task.outgoing and self.token_manager:
                flow = next(
                    (f for f in process_graph["flows"] if f["id"] == task.outgoing[0]),
                    None
                )
                if flow:
                    return await self.token_manager.move_token(
                        token, flow["target_ref"], self.instance_manager
                    )
            return token

        # For script tasks
        if task.script:
            # Execute script in isolated environment
            result = await self.script_executor.execute_script(task.script, token.data)
            token.data.update(result)

        # For service tasks (external integrations)
        if (
            task.extensions
            and "serviceTaskConfig" in task.extensions
            and self.service_executor
        ):
            await self.service_executor.execute_service_task(token, task, self.instance_manager)

        # After task execution, move token to next node if there is an outgoing flow
        if task.outgoing and self.token_manager:
            flow = next(
                (f for f in process_graph["flows"] if f["id"] == task.outgoing[0]),
                None,
            )
            if flow:
                token = await self.token_manager.move_token(
                    token, flow["target_ref"], self.instance_manager
                )

        return token

    async def _execute_gateway(
        self, token: Token, gateway: Gateway, process_graph: Dict
    ) -> Token:
        """Execute a gateway node."""
        logger.info(f"Executing gateway: {gateway.id}")
        return await self.gateway_handler.handle_gateway(token, gateway, process_graph)

    async def _execute_event(
        self, token: Token, event: Event, process_graph: Dict
    ) -> Token:
        """Execute an event node."""
        logger.info(f"Executing event: {event.id}")
        
        # Handle compensation events specially
        if event.event_definition == "compensation" or (
            event.event_type == EventType.BOUNDARY and event.event_definition == "compensation"
        ):
            await self.compensation_handler.handle_compensation_event(token, event, process_graph)
            return token
        
        # Use the regular event handler for non-compensation events
        await self.event_handler.handle_event(token, event, process_graph)
        return token
