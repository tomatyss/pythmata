from typing import Dict, List

from pythmata.core.engine.token import Token, TokenState
from pythmata.core.state import StateManager
from pythmata.core.types import Gateway, GatewayType
from pythmata.utils.logger import get_logger

logger = get_logger(__name__)


class GatewayHandler:
    """
    Handles gateway logic including exclusive, parallel, and inclusive gateways.
    """

    def __init__(self, state_manager: StateManager, token_manager=None):
        self.state_manager = state_manager
        self.token_manager = token_manager
        self.process_graph = None  # Will be set during handle_gateway

    async def handle_gateway(
        self, token: Token, gateway: Gateway, process_graph: Dict
    ) -> None:
        """
        Handle gateway logic based on gateway type.

        Args:
            token: Current token
            gateway: Gateway to handle
            process_graph: Process graph for flow evaluation
        """
        self.process_graph = process_graph  # Store for use in helper methods
        if gateway.gateway_type == GatewayType.EXCLUSIVE:
            await self._handle_exclusive_gateway(token, gateway, process_graph)
        elif gateway.gateway_type == GatewayType.PARALLEL:
            await self._handle_parallel_gateway(token, gateway)
        elif gateway.gateway_type == GatewayType.INCLUSIVE:
            await self._handle_inclusive_gateway(token, gateway, process_graph)

    async def _handle_exclusive_gateway(
        self, token: Token, gateway: Gateway, process_graph: Dict
    ) -> None:
        """
        Handle exclusive (XOR) gateway.

        Args:
            token: Current token
            gateway: Gateway to handle
            process_graph: Process graph for condition evaluation
        """
        # Get process variables for condition evaluation
        variables = await self.state_manager.get_variables(
            instance_id=token.instance_id, scope_id=token.scope_id
        )

        # Create evaluation context
        context = self._create_evaluation_context(token, variables)
        default_flow = None

        # Find sequence flow with true condition
        for flow in process_graph["flows"]:
            source_ref = flow["source_ref"] if isinstance(flow, dict) else flow.source_ref
            flow_id = flow["id"] if isinstance(flow, dict) else flow.id
            condition_expr = flow.get("condition_expression") if isinstance(flow, dict) else getattr(flow, "condition_expression", None)
            
            if source_ref == gateway.id:
                if not condition_expr:
                    # Store default flow for later if no conditions are true
                    default_flow = flow
                    continue

                try:
                    # Evaluate condition in restricted environment
                    condition_result = eval(
                        condition_expr,
                        {"__builtins__": {}},  # No built-ins
                        context,  # Our safe context
                    )

                    if condition_result:
                        await self._move_token(token, flow_id)
                        return

                except Exception as e:
                    logger.error(
                        f"Error evaluating condition for flow {flow_id}: {str(e)}"
                    )
                    raise

        # If no conditions were true, take default flow if it exists
        if default_flow:
            flow_id = default_flow["id"] if isinstance(default_flow, dict) else default_flow.id
            await self._move_token(token, flow_id)
            return

        logger.warning(f"No valid path found at gateway {gateway.id}")

    async def _handle_parallel_gateway(self, token: Token, gateway: Gateway) -> None:
        """
        Handle parallel (AND) gateway.

        Args:
            token: Current token
            gateway: Gateway to handle
        """
        if len(gateway.incoming) > 1:
            # Join: Wait for all incoming tokens
            tokens = await self.state_manager.get_token_positions(token.instance_id)
            active_tokens = [
                t
                for t in tokens
                if t["node_id"] == gateway.id and t["state"] == TokenState.ACTIVE.value
            ]
            if len(active_tokens) == len(gateway.incoming):
                # All tokens arrived, continue with one token
                for t in active_tokens[1:]:
                    await self.state_manager.remove_token(token.instance_id, gateway.id)
                if gateway.outgoing:
                    await self._move_token(token, gateway.outgoing[0])
        else:
            # Split: Create tokens for all outgoing paths
            await self._split_token(token, gateway.outgoing)

    async def _handle_inclusive_gateway(
        self, token: Token, gateway: Gateway, process_graph: Dict
    ) -> None:
        """
        Handle inclusive (OR) gateway.

        Args:
            token: Current token
            gateway: Gateway to handle
            process_graph: Process graph for condition evaluation
        """
        if len(gateway.incoming) > 1:
            await self._handle_inclusive_join(token, gateway)
        else:
            await self._handle_inclusive_split(token, gateway, process_graph)

    async def _handle_inclusive_join(self, token: Token, gateway: Gateway) -> None:
        """Handle inclusive gateway join logic."""
        # Get all tokens
        tokens = await self.state_manager.get_token_positions(token.instance_id)
        active_tokens = [
            t
            for t in tokens
            if t["node_id"] == gateway.id and t["state"] == TokenState.ACTIVE.value
        ]

        # Get all incoming flows that were activated
        active_flows = set()
        for t in tokens:
            if t.get("active_flows"):
                active_flows.update(t["active_flows"])

        # Only proceed if we have tokens from all active paths
        if len(active_tokens) == len(active_flows):
            # Remove extra tokens
            for t in active_tokens[1:]:
                await self.state_manager.remove_token(token.instance_id, gateway.id)
            # Continue with one token
            if gateway.outgoing:
                await self._move_token(token, gateway.outgoing[0])

    async def _handle_inclusive_split(
        self, token: Token, gateway: Gateway, process_graph: Dict
    ) -> None:
        """Handle inclusive gateway split logic."""
        # Get process variables for condition evaluation
        variables = await self.state_manager.get_variables(
            instance_id=token.instance_id, scope_id=token.scope_id
        )

        # Create evaluation context
        context = self._create_evaluation_context(token, variables)

        # Find all flows with true conditions
        active_paths = []
        default_flow = None

        for flow in process_graph["flows"]:
            source_ref = flow["source_ref"] if isinstance(flow, dict) else flow.source_ref
            flow_id = flow["id"] if isinstance(flow, dict) else flow.id
            condition_expr = flow.get("condition_expression") if isinstance(flow, dict) else getattr(flow, "condition_expression", None)
            
            if source_ref == gateway.id:
                if not condition_expr:
                    default_flow = flow
                    continue

                try:
                    # Evaluate condition in restricted environment
                    condition_result = eval(
                        condition_expr,
                        {"__builtins__": {}},  # No built-ins
                        context,  # Our safe context
                    )

                    if condition_result:
                        active_paths.append(flow_id)

                except Exception as e:
                    logger.error(
                        f"Error evaluating condition for flow {flow_id}: {str(e)}"
                    )
                    raise

        # If no conditions were true, take default flow if it exists
        if not active_paths and default_flow:
            flow_id = default_flow["id"] if isinstance(default_flow, dict) else default_flow.id
            active_paths.append(flow_id)

        if not active_paths:
            logger.warning(f"No valid paths found at gateway {gateway.id}")
            return

        # Store active flows in token data for join synchronization
        token.data["active_flows"] = active_paths

        # Create tokens for all active paths
        await self._split_token(token, active_paths)

    def _create_evaluation_context(self, token: Token, variables: Dict) -> Dict:
        """Create safe context for condition evaluation."""
        return {
            "token": token,
            "variables": variables,
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

    async def _move_token(self, token: Token, flow_id: str) -> None:
        """Move token using sequence flow."""
        # Find flow in process graph
        flow = next(
            (flow for flow in self.process_graph["flows"] 
             if (flow["id"] if isinstance(flow, dict) else flow.id) == flow_id),
            None
        )
        if not flow:
            logger.error(f"Flow {flow_id} not found in process graph")
            return

        # Use token manager to move token
        if self.token_manager:
            target_ref = flow["target_ref"] if isinstance(flow, dict) else flow.target_ref
            logger.info(f"Moving token {token.id} to {target_ref} via gateway")
            await self.token_manager.move_token(token, target_ref)
        else:
            logger.error("TokenManager not available for gateway token movement")

    async def _split_token(self, token: Token, target_node_ids: List[str]) -> None:
        """Split token into multiple tokens."""
        if self.token_manager:
            await self.token_manager.split_token(token, target_node_ids)
        else:
            logger.error("TokenManager not available for gateway token splitting")
