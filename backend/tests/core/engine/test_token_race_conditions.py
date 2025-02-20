"""Tests for token state race condition handling."""

import asyncio

import pytest

from pythmata.core.engine.executor import ProcessExecutor
from pythmata.core.engine.token import TokenState
from pythmata.core.engine.token_manager import TokenStateError
from tests.core.engine.base import BaseEngineTest
from tests.core.testing import assert_token_state


@pytest.mark.asyncio
class TestTokenStateRaceConditions(BaseEngineTest):
    """Test handling of concurrent token operations."""

    async def test_concurrent_token_moves(self):
        """Test that concurrent token moves maintain consistency."""
        instance_id = "test-concurrent-moves"
        graph = self.create_parallel_flow(tasks=["Task_1", "Task_2"])

        # Create initial token
        token = await self.executor.create_initial_token(instance_id, "Start_1")

        # Attempt concurrent moves
        results = await asyncio.gather(
            self.executor.move_token(token, "Task_1"),
            self.executor.move_token(token, "Task_2"),
            return_exceptions=True,
        )

        # Verify exactly one move succeeded and one failed with TokenStateError
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        error_count = sum(1 for r in results if isinstance(r, TokenStateError))
        
        assert success_count == 1, "Expected exactly one successful token move"
        assert error_count == 1, "Expected exactly one TokenStateError"

        # Verify token is in exactly one location
        tokens = await self.state_manager.get_token_positions(instance_id)
        active_tokens = [t for t in tokens if t.get("state") == TokenState.ACTIVE.value]
        assert len(active_tokens) == 1, "Expected exactly one active token"

    async def test_concurrent_token_splits(self):
        """Test that concurrent token splits maintain consistency."""
        instance_id = "test-concurrent-splits"
        graph = self.create_parallel_flow(
            tasks=["Task_1", "Task_2", "Task_3", "Task_4"]
        )

        # Create initial token at gateway
        token = await self.executor.create_initial_token(instance_id, "Gateway_1")

        # Attempt concurrent splits
        results = await asyncio.gather(
            self.executor.split_token(token, ["Task_1", "Task_2"]),
            self.executor.split_token(token, ["Task_3", "Task_4"]),
            return_exceptions=True,
        )

        # Verify only one split operation succeeded
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        assert success_count == 1

    async def test_token_state_transitions(self):
        """Test token state transitions remain consistent."""
        instance_id = "test-state-transitions"
        graph = self.create_sequence_flow()

        # Create initial token
        token = await self.executor.create_initial_token(instance_id, "Start_1")

        # Verify initial state
        await assert_token_state(
            self.state_manager,
            instance_id,
            expected_count=1,
            expected_node_ids=["Start_1"],
        )

        # Move token
        moved_token = await self.executor.move_token(token, "Task_1")

        # Verify moved state
        await assert_token_state(
            self.state_manager,
            instance_id,
            expected_count=1,
            expected_node_ids=["Task_1"],
        )

        # Attempt concurrent operations on moved token
        results = await asyncio.gather(
            self.executor.move_token(moved_token, "End_1"),
            self.executor.consume_token(moved_token),
            return_exceptions=True,
        )

        # Verify exactly one operation succeeded and one failed with TokenStateError
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        error_count = sum(1 for r in results if isinstance(r, TokenStateError))
        
        assert success_count == 1, "Expected exactly one successful operation"
        assert error_count == 1, "Expected exactly one TokenStateError"

        # Verify final token state
        tokens = await self.state_manager.get_token_positions(instance_id)
        active_tokens = [t for t in tokens if t.get("state") == TokenState.ACTIVE.value]
        
        # Should have exactly one token, either at End_1 or consumed
        assert len(active_tokens) <= 1, "Expected at most one active token"

    async def test_token_consumption_consistency(self):
        """Test token consumption remains consistent under concurrent attempts."""
        instance_id = "test-consumption"

        # Create token at end event
        token = await self.executor.create_initial_token(instance_id, "End_1")

        # Attempt concurrent consumption
        results = await asyncio.gather(
            self.executor.consume_token(token),
            self.executor.consume_token(token),
            return_exceptions=True,
        )

        # Verify only one consumption succeeded
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        assert success_count == 1

        # Verify token is actually consumed
        await assert_token_state(self.state_manager, instance_id, expected_count=0)
