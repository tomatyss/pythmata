"""Test utilities and common functionality."""
from typing import Dict, List

from pythmata.api.schemas import ProcessVariableValue
from pythmata.core.engine.saga import SagaOrchestrator, SagaStatus
from pythmata.core.state import StateManager

from .constants import (
    DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES,
    DEFAULT_ALGORITHM,
    DEFAULT_CLEANUP_INTERVAL,
    DEFAULT_DB_MAX_OVERFLOW,
    DEFAULT_DB_POOL_SIZE,
    DEFAULT_DEBUG,
    DEFAULT_MAX_INSTANCES,
    DEFAULT_REDIS_POOL_SIZE,
    DEFAULT_REDIS_URL,
    DEFAULT_RABBITMQ_URL,
    DEFAULT_RABBITMQ_CONNECTION_ATTEMPTS,
    DEFAULT_RABBITMQ_RETRY_DELAY,
    DEFAULT_SCRIPT_TIMEOUT,
    DEFAULT_SECRET_KEY,
    DEFAULT_SERVER_HOST,
    DEFAULT_SERVER_PORT,
)

__all__ = [
    # Constants
    "DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES",
    "DEFAULT_ALGORITHM",
    "DEFAULT_CLEANUP_INTERVAL",
    "DEFAULT_DB_MAX_OVERFLOW",
    "DEFAULT_DB_POOL_SIZE",
    "DEFAULT_DEBUG",
    "DEFAULT_MAX_INSTANCES",
    "DEFAULT_REDIS_POOL_SIZE",
    "DEFAULT_REDIS_URL",
    "DEFAULT_RABBITMQ_URL",
    "DEFAULT_RABBITMQ_CONNECTION_ATTEMPTS",
    "DEFAULT_RABBITMQ_RETRY_DELAY",
    "DEFAULT_SCRIPT_TIMEOUT",
    "DEFAULT_SECRET_KEY",
    "DEFAULT_SERVER_HOST",
    "DEFAULT_SERVER_PORT",
    # Assertion Functions
    "assert_token_state",
    "assert_saga_state",
    "assert_process_variables",
]


async def assert_token_state(
    state_manager: StateManager,
    instance_id: str,
    expected_count: int,
    expected_node_ids: List[str] = None,
) -> None:
    """Assert the token state for a process instance.
    
    Args:
        state_manager: State manager instance
        instance_id: Process instance ID
        expected_count: Expected number of tokens
        expected_node_ids: Expected node IDs for tokens (optional)
        
    Raises:
        AssertionError: If token state does not match expectations
    """
    tokens = await state_manager.get_token_positions(instance_id)
    assert (
        len(tokens) == expected_count
    ), f"Expected {expected_count} tokens, got {len(tokens)}"
    if expected_node_ids:
        token_node_ids = {t["node_id"] for t in tokens}
        assert token_node_ids == set(
            expected_node_ids
        ), f"Expected tokens at {expected_node_ids}, got {token_node_ids}"


async def assert_saga_state(
    saga: SagaOrchestrator,
    expected_status: SagaStatus,
    expected_completed_steps: int,
    compensation_required: bool = False,
) -> None:
    """Assert the state of a saga orchestrator.
    
    Args:
        saga: Saga orchestrator instance
        expected_status: Expected saga status
        expected_completed_steps: Expected number of completed steps
        compensation_required: Whether compensation is required
        
    Raises:
        AssertionError: If saga state does not match expectations
    """
    assert (
        saga.status == expected_status
    ), f"Expected saga status {expected_status}, got {saga.status}"
    assert (
        len(saga.completed_steps) == expected_completed_steps
    ), f"Expected {expected_completed_steps} completed steps, got {len(saga.completed_steps)}"
    assert (
        saga.compensation_required == compensation_required
    ), f"Expected compensation_required={compensation_required}, got {saga.compensation_required}"


async def assert_process_variables(
    state_manager: StateManager,
    instance_id: str,
    expected_variables: Dict[str, ProcessVariableValue],
) -> None:
    """Assert process variables match expected values.
    
    Args:
        state_manager: State manager instance
        instance_id: Process instance ID
        expected_variables: Dictionary of expected variable values
        
    Raises:
        AssertionError: If process variables do not match expectations
    """
    for name, expected in expected_variables.items():
        actual = await state_manager.get_variable(instance_id, name)
        assert actual.type == expected.type, f"Variable {name} type mismatch"
        assert actual.value == expected.value, f"Variable {name} value mismatch"
