import pytest

from pythmata.core.engine.expressions import ExpressionEvalError, ExpressionSyntaxError
from pythmata.core.engine.gateway import ExclusiveGateway
from pythmata.core.engine.token import Token
from pythmata.core.state import StateManager


@pytest.mark.asyncio
class TestExclusiveGateway:
    @pytest.fixture(autouse=True)
    async def setup_test(self, test_settings):
        """Setup test environment and cleanup after."""
        self.state_manager = StateManager(test_settings)
        await self.state_manager.connect()

        yield

        # Cleanup after test
        await self.state_manager.redis.flushdb()
        await self.state_manager.disconnect()

    async def test_condition_evaluation_with_different_types(self):
        """Test condition evaluation with string, number, boolean types."""
        gateway = ExclusiveGateway(
            gateway_id="Gateway_1", state_manager=self.state_manager
        )

        # Create test token with variables
        token = Token(
            instance_id="test-1",
            node_id="Gateway_1",
            data={"amount": 1500, "status": "approved", "urgent": True},
        )

        # Define outgoing flows with conditions
        flows = {
            "Flow_1": {"condition": "${amount > 1000}"},
            "Flow_2": {"condition": "${status == 'approved'}"},
            "Flow_3": {"condition": "${urgent == true}"},
        }

        # Test number condition
        result = await gateway.evaluate_condition(token, flows["Flow_1"]["condition"])
        assert result is True

        # Test string condition
        result = await gateway.evaluate_condition(token, flows["Flow_2"]["condition"])
        assert result is True

        # Test boolean condition
        result = await gateway.evaluate_condition(token, flows["Flow_3"]["condition"])
        assert result is True

    async def test_default_path_selection(self):
        """Test default path selection when no conditions match."""
        gateway = ExclusiveGateway(
            gateway_id="Gateway_1", state_manager=self.state_manager
        )

        # Create test token with variables
        token = Token(
            instance_id="test-2",
            node_id="Gateway_1",
            data={"amount": 500, "status": "pending"},
        )

        # Define outgoing flows with conditions and default
        flows = {
            "Flow_1": {"condition": "${amount > 1000}"},
            "Flow_2": {"condition": "${status == 'approved'}"},
            "Flow_3": {"condition": None},  # Default path
        }

        selected_flow = await gateway.select_path(token, flows)
        assert selected_flow == "Flow_3"

    async def test_path_selection_with_complex_conditions(self):
        """Test path selection with complex conditions."""
        gateway = ExclusiveGateway(
            gateway_id="Gateway_1", state_manager=self.state_manager
        )

        # Create test token with variables
        token = Token(
            instance_id="test-3",
            node_id="Gateway_1",
            data={
                "amount": 1500,
                "status": "approved",
                "priority": "high",
                "category": "special",
            },
        )

        # Define outgoing flows with complex conditions
        flows = {
            "Flow_1": {"condition": "${amount > 1000 && status == 'approved'}"},
            "Flow_2": {"condition": "${priority == 'high' || category == 'special'}"},
        }

        # First matching condition should be selected
        selected_flow = await gateway.select_path(token, flows)
        assert selected_flow == "Flow_1"

    async def test_invalid_condition_handling(self):
        """Test handling of invalid condition expressions."""
        gateway = ExclusiveGateway(
            gateway_id="Gateway_1", state_manager=self.state_manager
        )

        token = Token(instance_id="test-4", node_id="Gateway_1", data={"amount": 1500})

        # Test invalid syntax
        with pytest.raises(ExpressionSyntaxError):
            await gateway.evaluate_condition(token, "${invalid syntax")

        # Test undefined variable
        with pytest.raises(ExpressionEvalError):
            await gateway.evaluate_condition(token, "${undefined_var > 1000}")
