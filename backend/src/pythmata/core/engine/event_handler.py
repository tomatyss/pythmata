from typing import Dict

from pythmata.core.engine.token import Token, TokenState
from pythmata.core.state import StateManager
from pythmata.core.types import Event, EventType
from pythmata.utils.logger import get_logger

logger = get_logger(__name__)


class EventHandler:
    """
    Handles event-related operations including event processing and subprocess triggering.
    """

    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager

    async def handle_event(
        self, token: Token, event: Event, process_graph: Dict = None
    ) -> None:
        """
        Handle process event.

        Args:
            token: Current token
            event: Event to handle
            process_graph: Process graph for flow resolution
        """
        if event.event_type == EventType.END:
            await self._handle_end_event(token)
        else:
            await self._handle_intermediate_event(token, event, process_graph)

    async def trigger_event_subprocess(
        self, token: Token, event_subprocess_id: str, event_data: Dict
    ) -> Token:
        """
        Trigger an event subprocess when a matching event occurs.

        Args:
            token: Token from the parent process
            event_subprocess_id: ID of the event subprocess to trigger
            event_data: Event data including type, name, and interrupting flag

        Returns:
            New token in the event subprocess scope
        """
        # Create new token in event subprocess scope
        start_event_id = f"StartEvent_{event_subprocess_id.split('_')[-1]}"
        new_token = token.copy(
            node_id=start_event_id,
            scope_id=event_subprocess_id,
            data={"event_data": event_data},
        )

        # If interrupting event, cancel the parent token
        if event_data.get("interrupting", False):
            await self._handle_interrupting_event(token)

        # Add the new token
        await self.state_manager.add_token(
            instance_id=new_token.instance_id,
            node_id=new_token.node_id,
            data=new_token.to_dict(),
        )

        return new_token

    async def _handle_end_event(self, token: Token) -> None:
        """Handle end event processing."""
        # Mark token as completed before consuming
        await self.state_manager.update_token_state(
            instance_id=token.instance_id,
            node_id=token.node_id,
            state=TokenState.COMPLETED,
        )

        # Remove token and clear cache
        await self.state_manager.remove_token(
            instance_id=token.instance_id, node_id=token.node_id
        )
        await self.state_manager.redis.delete(f"tokens:{token.instance_id}")

    async def _handle_intermediate_event(
        self, token: Token, event: Event, process_graph: Dict
    ) -> None:
        """Handle intermediate event processing."""
        if event.outgoing:
            # Mark current token as completed
            await self.state_manager.update_token_state(
                instance_id=token.instance_id,
                node_id=token.node_id,
                state=TokenState.COMPLETED,
            )

            # Find flow and move to target node
            flow = next(
                (
                    flow
                    for flow in process_graph["flows"]
                    if flow["id"] == event.outgoing[0]
                ),
                None,
            )
            if flow:
                new_token = await self._move_token(token, flow["target_ref"])
                await self.state_manager.update_token_state(
                    instance_id=new_token.instance_id,
                    node_id=new_token.node_id,
                    state=TokenState.ACTIVE,
                )
            else:
                logger.error(f"Flow {event.outgoing[0]} not found in process graph")

    async def _handle_interrupting_event(self, token: Token) -> None:
        """Handle interrupting event processing."""
        await self.state_manager.update_token_state(
            instance_id=token.instance_id,
            node_id=token.node_id,
            state=TokenState.CANCELLED,
        )

        # Remove the cancelled token
        await self.state_manager.remove_token(
            instance_id=token.instance_id, node_id=token.node_id
        )
        await self.state_manager.redis.delete(f"tokens:{token.instance_id}")

    async def _move_token(self, token: Token, target_node_id: str) -> Token:
        """Move token to a new node."""
        # Remove token from current node
        await self.state_manager.remove_token(
            instance_id=token.instance_id, node_id=token.node_id
        )
        await self.state_manager.redis.delete(f"tokens:{token.instance_id}")

        # Create new token at target node
        new_token = token.copy(node_id=target_node_id)
        await self.state_manager.add_token(
            instance_id=new_token.instance_id,
            node_id=new_token.node_id,
            data=new_token.to_dict(),
        )

        return new_token
