from typing import Dict, List, Optional, Set

from pythmata.core.types import Event, EventType
from pythmata.utils.logger import get_logger

logger = get_logger(__name__)


class ProcessGraphValidationError(Exception):
    """
    Raised when process graph validation fails.

    Args:
        message: Description of the validation error
        node_id: Optional ID of the node where validation failed
    """

    def __init__(self, message: str, node_id: Optional[str] = None):
        super().__init__(
            f"Validation error at node {node_id}: {message}" if node_id else message
        )
        self.node_id = node_id


class ProcessValidator:
    """
    Validates process graph structure and connectivity.

    Handles validation of:
    - Graph structure and required sections
    - Node references and connectivity
    - Start/end events presence
    - Cycle detection (allowing self-loops)
    """

    def validate_process_graph(self, process_graph: Dict) -> None:
        """
        Validate process graph structure and connectivity.

        Args:
            process_graph: The process graph to validate

        Raises:
            ProcessGraphValidationError: If validation fails
        """
        self._validate_structure(process_graph)
        self._validate_connectivity(process_graph)
        self._validate_event_nodes(process_graph)

    def _validate_structure(self, process_graph: Dict) -> None:
        """Validate basic graph structure and required sections."""
        if "nodes" not in process_graph:
            raise ProcessGraphValidationError("Missing nodes section in process graph")
        if "flows" not in process_graph:
            raise ProcessGraphValidationError("Missing flows section in process graph")

        # Get all node IDs for reference validation
        node_ids = {node.id for node in process_graph["nodes"]}

        # Validate node references in flows
        for flow in process_graph["flows"]:
            # Handle both dictionary flows and object flows
            source_ref = (
                flow["source_ref"] if isinstance(flow, dict) else flow.source_ref
            )
            target_ref = (
                flow["target_ref"] if isinstance(flow, dict) else flow.target_ref
            )

            if source_ref not in node_ids:
                raise ProcessGraphValidationError(
                    f"Invalid node reference in flow: {source_ref}"
                )
            if target_ref not in node_ids:
                raise ProcessGraphValidationError(
                    f"Invalid node reference in flow: {target_ref}"
                )

    def _validate_event_nodes(self, process_graph: Dict) -> None:
        """Validate presence of required event nodes."""
        has_start = any(
            isinstance(node, Event) and node.event_type == EventType.START
            for node in process_graph["nodes"]
        )
        if not has_start:
            raise ProcessGraphValidationError("No start event found in process graph")

        has_end = any(
            isinstance(node, Event) and node.event_type == EventType.END
            for node in process_graph["nodes"]
        )
        if not has_end:
            raise ProcessGraphValidationError("No end event found in process graph")

    def _validate_connectivity(self, process_graph: Dict) -> None:
        """Validate graph connectivity and detect cycles."""
        # Build flow graph, separating self-loops
        flows_by_source: Dict[str, List[str]] = {}
        self_loops: Set[str] = set()
        for flow in process_graph["flows"]:
            # Handle both dictionary flows and object flows
            source = flow["source_ref"] if isinstance(flow, dict) else flow.source_ref
            target = flow["target_ref"] if isinstance(flow, dict) else flow.target_ref

            if source == target:
                self_loops.add(source)
            else:
                if source not in flows_by_source:
                    flows_by_source[source] = []
                flows_by_source[source].append(target)

        # Check for cycles and connectivity
        visited: Set[str] = set()
        path: Set[str] = set()
        connected_nodes: Set[str] = set()

        def dfs(node_id: str) -> None:
            if node_id in path and node_id not in self_loops:
                raise ProcessGraphValidationError(
                    "Cycle detected in process graph", node_id=node_id
                )

            if node_id in visited:
                return

            visited.add(node_id)
            path.add(node_id)
            connected_nodes.add(node_id)

            # Follow all outgoing flows except self-loops
            for next_node in flows_by_source.get(node_id, []):
                dfs(next_node)

            path.remove(node_id)

        # Start from start events
        for node in process_graph["nodes"]:
            if isinstance(node, Event) and node.event_type == EventType.START:
                dfs(node.id)

        # Check if all nodes are connected
        node_ids = {node.id for node in process_graph["nodes"]}
        disconnected = node_ids - connected_nodes
        if disconnected:
            raise ProcessGraphValidationError(
                f"Disconnected nodes detected: {', '.join(disconnected)}"
            )
