import pytest
from pythmata.core.engine.gateway import ParallelGateway
from pythmata.core.engine.token import Token, TokenState
from pythmata.core.state import StateManager

@pytest.mark.asyncio
class TestParallelGateway:
    @pytest.fixture(autouse=True)
    async def setup_test(self, test_settings):
        """Setup test environment and cleanup after."""
        self.state_manager = StateManager(test_settings)
        await self.state_manager.connect()
        
        yield
        
        # Cleanup after test
        await self.state_manager.redis.flushdb()
        await self.state_manager.disconnect()

    async def test_split_token_creation(self):
        """Test that split creates correct number of tokens."""
        gateway = ParallelGateway("Gateway_1", self.state_manager)
        token = Token(
            instance_id="test-1",
            node_id="Gateway_1",
            data={"var1": "value1"}
        )
        flows = {
            "Flow_1": {},
            "Flow_2": {},
            "Flow_3": {}
        }
        paths = await gateway.select_paths(token, flows)
        assert len(paths) == 3
        assert set(paths) == {"Flow_1", "Flow_2", "Flow_3"}

    async def test_split_token_data_copying(self):
        """Test that split tokens inherit data correctly."""
        gateway = ParallelGateway("Gateway_1", self.state_manager)
        original_data = {"var1": "value1", "var2": 42}
        token = Token(
            instance_id="test-2",
            node_id="Gateway_1",
            data=original_data
        )
        flows = {"Flow_1": {}, "Flow_2": {}}
        paths = await gateway.select_paths(token, flows)
        # Verify data is copied to all paths
        stored_tokens = await self.state_manager.get_token_positions(token.instance_id)
        assert all(t["data"] == original_data for t in stored_tokens)

    async def test_join_token_synchronization(self):
        """Test that join waits for all incoming tokens."""
        gateway = ParallelGateway("Gateway_1", self.state_manager)
        instance_id = "test-3"
        
        # Create incoming tokens
        token1 = Token(instance_id=instance_id, node_id="Task_1")
        token2 = Token(instance_id=instance_id, node_id="Task_2")
        
        # Register expected tokens
        await gateway.register_incoming_paths(instance_id, ["Task_1", "Task_2"])
        
        # First token arrives
        result = await gateway.try_join(token1)
        assert result is None  # Should wait for other token
        
        # Second token arrives
        result = await gateway.try_join(token2)
        assert result is not None  # Should create merged token

    async def test_join_token_data_merging(self):
        """Test that join merges token data correctly."""
        gateway = ParallelGateway("Gateway_1", self.state_manager)
        instance_id = "test-4"
        
        token1 = Token(
            instance_id=instance_id,
            node_id="Task_1",
            data={"var1": "value1", "shared": "token1"}
        )
        token2 = Token(
            instance_id=instance_id,
            node_id="Task_2",
            data={"var2": "value2", "shared": "token2"}
        )
        
        await gateway.register_incoming_paths(instance_id, ["Task_1", "Task_2"])
        await gateway.try_join(token1)
        merged_token = await gateway.try_join(token2)
        
        assert merged_token.data["var1"] == "value1"
        assert merged_token.data["var2"] == "value2"
        assert merged_token.data["shared"] in ["token1", "token2"]  # Last write wins

    async def test_join_error_handling(self):
        """Test error handling for missing or duplicate tokens."""
        gateway = ParallelGateway("Gateway_1", self.state_manager)
        instance_id = "test-5"
        
        # Test duplicate token
        token = Token(instance_id=instance_id, node_id="Task_1")
        await gateway.register_incoming_paths(instance_id, ["Task_1", "Task_2"])
        await gateway.try_join(token)
        with pytest.raises(ValueError):
            await gateway.try_join(token)  # Should reject duplicate
            
        # Test unregistered path
        unregistered_token = Token(instance_id=instance_id, node_id="Task_3")
        with pytest.raises(ValueError):
            await gateway.try_join(unregistered_token)
