from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from pythmata.core.engine.expressions import ExpressionError, ExpressionEvaluator
from pythmata.core.engine.token import Token
from pythmata.core.state import StateManager
from pythmata.utils.logger import get_logger

logger = get_logger(__name__)


class Gateway(ABC):
    """Base class for BPMN gateways."""

    def __init__(self, gateway_id: str, state_manager: StateManager):
        self.id = gateway_id
        self.state_manager = state_manager

    @abstractmethod
    async def select_path(self, token: Token, flows: Dict[str, Dict]) -> str:
        """Select outgoing path based on gateway type and conditions."""


class ExclusiveGateway(Gateway):
    """
    Implementation of BPMN Exclusive Gateway (XOR).

    Selects exactly one outgoing path based on conditions. If no conditions
    match, selects the default path if available.
    """

    def __init__(self, gateway_id: str, state_manager: StateManager):
        super().__init__(gateway_id, state_manager)
        self.evaluator = ExpressionEvaluator()

    async def evaluate_condition(self, token: Token, condition: Optional[str]) -> bool:
        """Evaluate a condition expression using token data.

        Args:
            token: Process token containing variables
            condition: Condition expression (e.g., ${amount > 1000})

        Returns:
            True if condition evaluates to true, False otherwise
        """
        if not condition:
            return True  # Default path

        try:
            return self.evaluator.evaluate(condition, token.data)
        except ExpressionError as e:
            # Re-raise expression-related errors
            raise
        except Exception as e:
            logger.error(f"Failed to evaluate condition: {condition}. Error: {str(e)}")
            return False

    async def select_path(self, token: Token, flows: Dict[str, Dict]) -> str:
        """
        Select outgoing path based on conditions.

        Args:
            token: Process token
            flows: Dict of flow_id -> flow_data with conditions

        Returns:
            ID of selected flow
        """
        # First check conditional paths
        for flow_id, flow_data in flows.items():
            condition = flow_data.get("condition")
            if await self.evaluate_condition(token, condition):
                return flow_id

        # Find default path (no condition)
        for flow_id, flow_data in flows.items():
            if not flow_data.get("condition"):
                return flow_id

        raise ValueError(
            f"No valid path found for gateway {self.id} and no default path defined"
        )


class ParallelGateway(Gateway):
    """
    Implementation of BPMN Parallel Gateway (AND).

    Splits token into multiple parallel paths and synchronizes
    tokens at join points.
    """

    def __init__(self, gateway_id: str, state_manager: StateManager):
        super().__init__(gateway_id, state_manager)
        # Track join states per instance
        self._join_states: Dict[str, Dict] = {}

    async def select_paths(self, token: Token, flows: Dict[str, Dict]) -> List[str]:
        """
        Return all outgoing paths for parallel split.

        Args:
            token: Process token
            flows: Dict of flow_id -> flow_data

        Returns:
            List of all flow IDs (parallel gateway activates all paths)
        """
        return list(flows.keys())

    async def select_path(self, token: Token, flows: Dict[str, Dict]) -> str:
        """
        Required by Gateway ABC, but parallel gateways use select_paths.
        Returns first path as a default implementation.
        """
        paths = await self.select_paths(token, flows)
        return paths[0]

    async def register_incoming_paths(
        self, instance_id: str, path_ids: List[str]
    ) -> None:
        """
        Register expected incoming paths for an instance.

        Args:
            instance_id: Process instance ID
            path_ids: List of incoming path IDs to expect tokens from
        """
        self._join_states[instance_id] = {
            "expected": set(path_ids),
            "received": set(),
            "tokens": {},
        }

    async def try_join(self, token: Token) -> Optional[Token]:
        """
        Try to join incoming token. Returns merged token if all expected
        tokens have arrived, None otherwise.

        Args:
            token: Incoming token to join

        Returns:
            Merged token if all expected tokens received, None if still waiting

        Raises:
            ValueError: If token is unexpected or duplicate
        """
        instance_id = token.instance_id
        state = self._join_states.get(instance_id)

        if not state:
            raise ValueError(f"No join state registered for instance {instance_id}")

        if token.node_id not in state["expected"]:
            raise ValueError(f"Unexpected token from {token.node_id}")

        if token.node_id in state["received"]:
            raise ValueError(f"Duplicate token from {token.node_id}")

        # Store token
        state["received"].add(token.node_id)
        state["tokens"][token.node_id] = token

        # Check if all tokens received
        if state["received"] == state["expected"]:
            merged_token = await self._merge_tokens(instance_id)
            del self._join_states[instance_id]
            return merged_token

        return None

    async def _merge_tokens(self, instance_id: str) -> Token:
        """
        Merge data from all received tokens.

        Args:
            instance_id: Process instance ID

        Returns:
            New token with merged data from all received tokens
        """
        state = self._join_states[instance_id]
        merged_data = {}

        # Merge data from all tokens (last write wins for conflicts)
        for token in state["tokens"].values():
            merged_data.update(token.data)

        return Token(instance_id=instance_id, node_id=self.id, data=merged_data)


class InclusiveGateway(ExclusiveGateway):
    """
    Implementation of BPMN Inclusive Gateway (OR).

    Selects one or more outgoing paths based on conditions. Multiple paths
    can be activated if their conditions evaluate to true. If no conditions
    match, selects the default path if available.
    """

    async def select_path(self, token: Token, flows: Dict[str, Dict]) -> str:
        """
        Select a single path (required by Gateway ABC).
        This implementation always returns the first valid path.
        For multiple paths, use select_paths instead.
        """
        paths = await self.select_paths(token, flows)
        return paths[0]

    async def select_paths(self, token: Token, flows: Dict[str, Dict]) -> List[str]:
        """
        Select all outgoing paths with conditions that evaluate to true.

        Args:
            token: Process token
            flows: Dict of flow_id -> flow_data with conditions

        Returns:
            List of selected flow IDs
        """
        selected_flows = []
        has_matching_condition = False
        default_flow = None

        # First check all conditional paths
        for flow_id, flow_data in flows.items():
            condition = flow_data.get("condition")
            if condition is None:
                default_flow = flow_id
                continue

            if await self.evaluate_condition(token, condition):
                selected_flows.append(flow_id)
                has_matching_condition = True

        # If no conditions matched and there's a default path, use it
        if not has_matching_condition and default_flow:
            return [default_flow]

        # If no conditions matched and no default path, raise error
        if not selected_flows:
            raise ValueError(
                f"No valid paths found for gateway {self.id} and no default path defined"
            )

        return selected_flows
