import pytest
from uuid import uuid4

from pythmata.core.engine.executor import ProcessExecutor
from pythmata.core.engine.instance import ProcessInstanceManager
from pythmata.core.state import StateManager
from pythmata.models.process import ProcessDefinition, ProcessStatus
from tests.core.engine.base import BaseEngineTest
from tests.data.process_samples import SIMPLE_PROCESS_XML


class TestTokenIdempotency(BaseEngineTest):
    """Test cases for token creation idempotency."""

    async def test_duplicate_token_creation_handling(
        self,
        session,
        state_manager: StateManager,
        test_settings
    ):
        """
        Test that duplicate token creation attempts are handled gracefully.
        
        Should:
        1. Successfully create initial token on first attempt
        2. Skip token creation on subsequent attempts
        3. Maintain consistent token state
        4. Not raise errors on duplicate attempts
        """
        # Create test process definition
        definition = ProcessDefinition(
            id=uuid4(),
            name="Test Process",
            version=1,
            bpmn_xml=SIMPLE_PROCESS_XML
        )
        session.add(definition)
        await session.commit()

        # Create instance manager and executor
        instance_manager = ProcessInstanceManager(session, None, state_manager)
        executor = ProcessExecutor(state_manager, instance_manager)
        instance_manager.executor = executor

        # Create process instance
        instance = await instance_manager.create_instance(definition.id)
        instance_id = str(instance.id)

        # First token creation attempt
        initial_token = await executor.create_initial_token(instance_id, "StartEvent_1")
        assert initial_token is not None
        assert initial_token.node_id == "StartEvent_1"

        # Get token state after first creation
        tokens_after_first = await state_manager.get_token_positions(instance_id)
        assert len(tokens_after_first) == 1
        assert tokens_after_first[0]["node_id"] == "StartEvent_1"
        assert tokens_after_first[0]["state"] == "ACTIVE"

        # Second token creation attempt - should handle gracefully
        await executor.create_initial_token(instance_id, "StartEvent_1")

        # Verify token state remains consistent
        tokens_after_second = await state_manager.get_token_positions(instance_id)
        assert len(tokens_after_second) == 1
        assert tokens_after_second[0]["node_id"] == "StartEvent_1"
        assert tokens_after_second[0]["state"] == "ACTIVE"

        # Verify instance remains in running state
        await session.refresh(instance)
        assert instance.status == ProcessStatus.RUNNING

    async def test_concurrent_token_creation(
        self,
        session,
        state_manager: StateManager,
        test_settings
    ):
        """
        Test that concurrent token creation attempts are handled correctly.
        
        Should:
        1. Handle multiple simultaneous token creation attempts
        2. Maintain data consistency
        3. Not create duplicate tokens
        """
        # Create test process definition
        definition = ProcessDefinition(
            id=uuid4(),
            name="Test Process",
            version=1,
            bpmn_xml=SIMPLE_PROCESS_XML
        )
        session.add(definition)
        await session.commit()

        # Create instance manager and executor
        instance_manager = ProcessInstanceManager(session, None, state_manager)
        executor = ProcessExecutor(state_manager, instance_manager)
        instance_manager.executor = executor

        # Create process instance
        instance = await instance_manager.create_instance(definition.id)
        instance_id = str(instance.id)

        # Simulate concurrent token creation attempts
        import asyncio
        creation_tasks = [
            executor.create_initial_token(instance_id, "StartEvent_1")
            for _ in range(5)
        ]
        await asyncio.gather(*creation_tasks, return_exceptions=True)

        # Verify only one token exists
        final_tokens = await state_manager.get_token_positions(instance_id)
        assert len(final_tokens) == 1
        assert final_tokens[0]["node_id"] == "StartEvent_1"
        assert final_tokens[0]["state"] == "ACTIVE"

        # Verify instance state
        await session.refresh(instance)
        assert instance.status == ProcessStatus.RUNNING

    async def test_redis_state_cleanup_on_completion(
        self,
        session,
        state_manager: StateManager,
        test_settings
    ):
        """
        Test that Redis state is properly cleaned up when process completes.
        
        Should:
        1. Clean up all Redis keys for the instance
        2. Remove all tokens
        3. Remove any locks
        4. Not affect other instance states
        """
        # Create two test process definitions
        definition1 = ProcessDefinition(
            id=uuid4(),
            name="Test Process 1",
            version=1,
            bpmn_xml=SIMPLE_PROCESS_XML
        )
        definition2 = ProcessDefinition(
            id=uuid4(),
            name="Test Process 2",
            version=1,
            bpmn_xml=SIMPLE_PROCESS_XML
        )
        session.add(definition1)
        session.add(definition2)
        await session.commit()

        # Create instance managers and executors
        instance_manager = ProcessInstanceManager(session, None, state_manager)
        executor = ProcessExecutor(state_manager, instance_manager)
        instance_manager.executor = executor

        # Create two process instances
        instance1 = await instance_manager.create_instance(definition1.id)
        instance2 = await instance_manager.create_instance(definition2.id)
        instance1_id = str(instance1.id)
        instance2_id = str(instance2.id)

        # Create initial tokens for both instances
        await executor.create_initial_token(instance1_id, "StartEvent_1")
        await executor.create_initial_token(instance2_id, "StartEvent_1")

        # Verify both instances have tokens
        tokens1 = await state_manager.get_token_positions(instance1_id)
        tokens2 = await state_manager.get_token_positions(instance2_id)
        assert len(tokens1) == 1
        assert len(tokens2) == 1

        # Complete first instance
        await instance_manager.complete_instance(instance1.id)

        # Verify first instance's Redis state is cleaned up
        instance1_keys = await state_manager.redis.keys(f"process:{instance1_id}:*")
        assert len(instance1_keys) == 0, "All Redis keys should be cleaned up"

        # Verify second instance's state remains intact
        tokens2_after = await state_manager.get_token_positions(instance2_id)
        assert len(tokens2_after) == 1, "Second instance's tokens should remain"
        assert tokens2_after[0]["node_id"] == "StartEvent_1"
        assert tokens2_after[0]["state"] == "ACTIVE"

        # Verify lock state
        lock1_exists = await state_manager.redis.exists(f"lock:process:{instance1_id}")
        lock2_exists = await state_manager.redis.exists(f"lock:process:{instance2_id}")
        assert not lock1_exists, "Completed instance should have no locks"
        assert not lock2_exists, "Running instance should have no stale locks"

        # Verify database state
        await session.refresh(instance1)
        await session.refresh(instance2)
        assert instance1.status == ProcessStatus.COMPLETED
        assert instance2.status == ProcessStatus.RUNNING

    async def test_error_handling_and_cleanup(
        self,
        session,
        state_manager: StateManager,
        test_settings
    ):
        """
        Test error handling and state cleanup during token creation.
        
        Should:
        1. Handle errors gracefully
        2. Clean up any partial state
        3. Set appropriate error status
        4. Remove any stale locks
        """
        # Create test process definition
        definition = ProcessDefinition(
            id=uuid4(),
            name="Test Process",
            version=1,
            bpmn_xml=SIMPLE_PROCESS_XML
        )
        session.add(definition)
        await session.commit()

        # Create instance manager and executor
        instance_manager = ProcessInstanceManager(session, None, state_manager)
        executor = ProcessExecutor(state_manager, instance_manager)
        instance_manager.executor = executor

        # Create process instance
        instance = await instance_manager.create_instance(definition.id)
        instance_id = str(instance.id)

        # Force a lock to simulate a failed previous attempt
        lock_key = f"lock:process:{instance_id}"
        await state_manager.redis.set(lock_key, "1", ex=30)

        try:
            # Attempt token creation with existing lock
            await executor.create_initial_token(instance_id, "StartEvent_1")
        except Exception:
            # Verify error handling
            await session.refresh(instance)
            assert instance.status == ProcessStatus.ERROR

            # Verify lock was cleaned up
            lock_exists = await state_manager.redis.exists(lock_key)
            assert not lock_exists, "Lock should be cleaned up after error"

            # Verify no partial token state
            tokens = await state_manager.get_token_positions(instance_id)
            assert len(tokens) == 0, "No tokens should exist after error"

    async def test_process_started_event_idempotency(
        self,
        session,
        state_manager: StateManager,
        test_settings
    ):
        """
        Test that process.started event handling is idempotent.
        
        Should:
        1. Handle duplicate process.started events correctly
        2. Create token only on first event
        3. Skip token creation on subsequent events
        4. Maintain consistent process state
        """
        # Create test process definition
        definition = ProcessDefinition(
            id=uuid4(),
            name="Test Process",
            version=1,
            bpmn_xml=SIMPLE_PROCESS_XML
        )
        session.add(definition)
        await session.commit()

        # Create instance manager and executor
        instance_manager = ProcessInstanceManager(session, None, state_manager)
        executor = ProcessExecutor(state_manager, instance_manager)
        instance_manager.executor = executor

        # Create process instance
        instance = await instance_manager.create_instance(definition.id)
        instance_id = str(instance.id)

        from pythmata.main import handle_process_started

        # First event handling
        await handle_process_started({
            "instance_id": instance_id,
            "definition_id": str(definition.id)
        })

        # Get token state after first event
        tokens_after_first = await state_manager.get_token_positions(instance_id)
        assert len(tokens_after_first) == 1
        first_token_id = tokens_after_first[0]["id"]

        # Second event handling (simulating duplicate/redelivered event)
        await handle_process_started({
            "instance_id": instance_id,
            "definition_id": str(definition.id)
        })

        # Verify token state remains consistent
        tokens_after_second = await state_manager.get_token_positions(instance_id)
        assert len(tokens_after_second) == 1
        assert tokens_after_second[0]["id"] == first_token_id, "Token ID should remain the same"
        assert tokens_after_second[0]["node_id"] == "StartEvent_1"
        assert tokens_after_second[0]["state"] == "ACTIVE"

        # Verify instance state
        await session.refresh(instance)
        assert instance.status == ProcessStatus.RUNNING
