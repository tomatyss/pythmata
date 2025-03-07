from typing import Dict

from pythmata.core.engine.token import Token
from pythmata.core.state import StateManager
from pythmata.core.types import Event, EventType
from pythmata.utils.logger import get_logger

logger = get_logger(__name__)


class EventHandler:
    """
    Handles event-related operations including event processing and subprocess triggering.
    """

    def __init__(
        self, state_manager: StateManager, token_manager=None, instance_manager=None
    ):
        self.state_manager = state_manager
        self.token_manager = token_manager
        self.instance_manager = instance_manager

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
        if event.event_type == EventType.START:
            # For start events, mark as completed and move to next node
            logger.info(f"Handling start event for token {token.id}")
            if event.outgoing:
                # Find flow and move to target node
                flow = next(
                    (
                        flow
                        for flow in process_graph["flows"]
                        if (flow["id"] if isinstance(flow, dict) else flow.id)
                        == event.outgoing[0]
                    ),
                    None,
                )
                if flow:
                    if self.token_manager:
                        target_ref = (
                            flow["target_ref"]
                            if isinstance(flow, dict)
                            else flow.target_ref
                        )
                        logger.info(
                            f"Moving token {token.id} to {target_ref} via start event"
                        )
                        await self.token_manager.move_token(
                            token, target_ref, self.instance_manager
                        )
                    else:
                        logger.error(
                            "TokenManager not available for event token movement"
                        )
                else:
                    logger.error(f"Flow {event.outgoing[0]} not found in process graph")
        elif event.event_type == EventType.END:
            # For end events, consume the token
            logger.info(f"Handling end event for token {token.id}")
            await self._handle_end_event(token)
        else:
            # For intermediate events, move to next node
            logger.info(f"Handling intermediate event for token {token.id}")
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
        if self.token_manager:
            await self.token_manager.consume_token(token)
        else:
            logger.error("TokenManager not available for event token consumption")

    async def _handle_intermediate_event(
        self, token: Token, event: Event, process_graph: Dict
    ) -> None:
        """Handle intermediate event processing."""
        if event.outgoing:
            # Find flow and move to target node
            flow = next(
                (
                    flow
                    for flow in process_graph["flows"]
                    if (flow["id"] if isinstance(flow, dict) else flow.id)
                    == event.outgoing[0]
                ),
                None,
            )
            if flow:
                if self.token_manager:
                    # Move token to next node
                    target_ref = (
                        flow["target_ref"]
                        if isinstance(flow, dict)
                        else flow.target_ref
                    )
                    logger.info(f"Moving token {token.id} to {target_ref} via event")
                    await self.token_manager.move_token(
                        token, target_ref, self.instance_manager
                    )
                else:
                    logger.error("TokenManager not available for event token movement")
            else:
                logger.error(f"Flow {event.outgoing[0]} not found in process graph")

    async def _handle_interrupting_event(self, token: Token) -> None:
        """Handle interrupting event processing."""
        if self.token_manager:
            await self.token_manager.consume_token(token)
        else:
            logger.error("TokenManager not available for event token consumption")
