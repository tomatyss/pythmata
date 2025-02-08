from typing import Any, Dict, Optional

from pythmata.core.state import StateManager
from pythmata.utils.logger import get_logger

logger = get_logger(__name__)


class ProcessExecutor:
    """Executes process instances."""

    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager

    async def create_initial_token(self, instance_id: str, start_node_id: str) -> None:
        """Create initial token at process start event.

        Args:
            instance_id: Process instance ID
            start_node_id: Start event node ID
        """
        await self.state_manager.add_token(
            instance_id=instance_id,
            node_id=start_node_id,
            data={
                "scope_id": None,  # Root scope
                "state": "ACTIVE",
            },
        )
        logger.info(
            f"Created initial token for instance {instance_id} at {start_node_id}"
        )
