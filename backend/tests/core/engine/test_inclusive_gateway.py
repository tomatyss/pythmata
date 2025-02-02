import pytest
from pythmata.core.engine.gateway import InclusiveGateway
from pythmata.core.engine.token import Token, TokenState
from pythmata.core.state import StateManager

@pytest.mark.asyncio
class TestInclusiveGateway:
    @pytest.fixture(autouse=True)
    async def setup_test(self, test_settings):
        """Setup test environment and cleanup after."""
        self.state_manager = StateManager(test_settings)
        await self.state_manager.connect()
        
        yield
        
        # Cleanup after test
        await self.state_manager.redis.flushdb()
        await self.state_manager.disconnect()

    async def test_multiple_path_activation(self):
        """Test activation of multiple paths based on conditions."""
        gateway = InclusiveGateway(
            gateway_id="Gateway_1",
            state_manager=self.state_manager
        )

        # Create test token with variables
        token = Token(
            instance_id="test-1",
            node_id="Gateway_1",
            data={
                "amount": 1500,
                "urgent": True,
                "category": "special"
            }
        )

        # Define outgoing flows with conditions
        flows = {
            "Flow_1": {"condition": "${amount > 1000}"},
            "Flow_2": {"condition": "${urgent == true}"},
            "Flow_3": {"condition": "${category == 'special'}"}
        }

        # All conditions should match
        selected_flows = await gateway.select_paths(token, flows)
        assert len(selected_flows) == 3
        assert set(selected_flows) == {"Flow_1", "Flow_2", "Flow_3"}

    async def test_no_matching_conditions(self):
        """Test behavior when no conditions match."""
        gateway = InclusiveGateway(
            gateway_id="Gateway_1",
            state_manager=self.state_manager
        )

        token = Token(
            instance_id="test-2",
            node_id="Gateway_1",
            data={
                "amount": 500,
                "urgent": False,
                "category": "normal"
            }
        )

        flows = {
            "Flow_1": {"condition": "${amount > 1000}"},
            "Flow_2": {"condition": "${urgent == true}"},
            "Flow_3": {"condition": "${category == 'special'}"},
            "Flow_4": {"condition": None}  # Default path
        }

        # Only default path should be selected
        selected_flows = await gateway.select_paths(token, flows)
        assert len(selected_flows) == 1
        assert selected_flows[0] == "Flow_4"

    async def test_subset_conditions_matching(self):
        """Test activation of a subset of paths."""
        gateway = InclusiveGateway(
            gateway_id="Gateway_1",
            state_manager=self.state_manager
        )

        token = Token(
            instance_id="test-3",
            node_id="Gateway_1",
            data={
                "amount": 1500,
                "urgent": False,
                "category": "normal"
            }
        )

        flows = {
            "Flow_1": {"condition": "${amount > 1000}"},
            "Flow_2": {"condition": "${urgent == true}"},
            "Flow_3": {"condition": "${category == 'special'}"}
        }

        # Only amount condition should match
        selected_flows = await gateway.select_paths(token, flows)
        assert len(selected_flows) == 1
        assert selected_flows[0] == "Flow_1"

    async def test_complex_conditions(self):
        """Test complex condition evaluation."""
        gateway = InclusiveGateway(
            gateway_id="Gateway_1",
            state_manager=self.state_manager
        )

        token = Token(
            instance_id="test-4",
            node_id="Gateway_1",
            data={
                "amount": 1500,
                "status": "approved",
                "priority": "high",
                "category": "special"
            }
        )

        flows = {
            "Flow_1": {
                "condition": "${amount > 1000 && status == 'approved'}"
            },
            "Flow_2": {
                "condition": "${priority == 'high' || category == 'special'}"
            },
            "Flow_3": {
                "condition": "${amount < 1000 || status != 'approved'}"
            }
        }

        # First two conditions should match
        selected_flows = await gateway.select_paths(token, flows)
        assert len(selected_flows) == 2
        assert set(selected_flows) == {"Flow_1", "Flow_2"}
