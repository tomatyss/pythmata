"""Tests for the state management functionality."""

import pytest

from pythmata.api.schemas import ProcessVariableValue
from pythmata.core.state import StateManager


@pytest.fixture(autouse=True)
async def clear_redis(state_manager: StateManager):
    """Clear Redis data between tests."""
    try:
        await state_manager.redis.flushdb()
        yield
    finally:
        await state_manager.redis.flushdb()


@pytest.mark.asyncio
class TestStateManager:
    """Test suite for StateManager class."""

    async def test_get_variables_root_scope(self, state_manager: StateManager):
        """Test getting variables from root scope."""
        # Set up test variables
        instance_id = "test_instance"
        variables = {
            "var1": ProcessVariableValue(type="string", value="test1"),
            "var2": ProcessVariableValue(type="integer", value=42),
        }

        # Set variables
        for name, var in variables.items():
            await state_manager.set_variable(instance_id, name, var)

        # Get all variables
        result = await state_manager.get_variables(instance_id)

        # Verify results
        assert len(result) == 2
        assert result["var1"].value == "test1"
        assert result["var2"].value == 42
        assert result["var1"].type == "string"
        assert result["var2"].type == "integer"

    async def test_get_variables_with_scope(self, state_manager: StateManager):
        """Test getting variables with scope hierarchy."""
        instance_id = "test_instance"
        scope_id = "subprocess_1"
        parent_scope = "parent"
        scope_path = f"{parent_scope}/{scope_id}"

        # Set up variables at different scope levels
        root_var = ProcessVariableValue(type="string", value="root")
        parent_var = ProcessVariableValue(type="integer", value=100)
        scope_var = ProcessVariableValue(type="boolean", value=True)

        await state_manager.set_variable(instance_id, "root_var", root_var)
        await state_manager.set_variable(
            instance_id, "parent_var", parent_var, parent_scope
        )
        await state_manager.set_variable(
            instance_id, "scope_var", scope_var, scope_path
        )

        # Test getting variables at scope level with parent checking
        result = await state_manager.get_variables(
            instance_id, scope_path, check_parent=True
        )

        # Verify results include variables from all levels
        assert len(result) == 3
        assert result["root_var"].value == "root"
        assert result["parent_var"].value == 100
        assert result["scope_var"].value is True

        # Test getting variables at scope level without parent checking
        result = await state_manager.get_variables(
            instance_id, scope_path, check_parent=False
        )

        # Verify results only include variables from specified scope
        assert len(result) == 1
        assert result["scope_var"].value is True

    async def test_get_variables_empty(self, state_manager: StateManager):
        """Test getting variables when none exist."""
        instance_id = "test_instance"
        result = await state_manager.get_variables(instance_id)
        assert len(result) == 0

    async def test_get_variables_scope_isolation(self, state_manager: StateManager):
        """Test that variables in different scopes don't interfere."""
        instance_id = "test_instance"
        scope1 = "scope1"
        scope2 = "scope2"

        # Set variables in different scopes
        var1 = ProcessVariableValue(type="string", value="scope1_value")
        var2 = ProcessVariableValue(type="string", value="scope2_value")

        await state_manager.set_variable(instance_id, "var", var1, scope1)
        await state_manager.set_variable(instance_id, "var", var2, scope2)

        # Get variables from each scope
        result1 = await state_manager.get_variables(
            instance_id, scope1, check_parent=False
        )
        result2 = await state_manager.get_variables(
            instance_id, scope2, check_parent=False
        )

        # Verify scope isolation
        assert len(result1) == 1
        assert len(result2) == 1
        assert result1["var"].value == "scope1_value"
        assert result2["var"].value == "scope2_value"

    async def test_get_variables_complex_values(self, state_manager: StateManager):
        """Test getting variables with complex data types."""
        instance_id = "test_instance"
        variables = {
            "list_var": ProcessVariableValue(type="json", value=[1, 2, 3]),
            "dict_var": ProcessVariableValue(type="json", value={"key": "value"}),
            "nested": ProcessVariableValue(
                type="json", value={"list": [1, 2], "dict": {"nested": "value"}}
            ),
        }

        # Set variables
        for name, var in variables.items():
            await state_manager.set_variable(instance_id, name, var)

        # Get all variables
        result = await state_manager.get_variables(instance_id)

        # Verify complex data types are preserved
        assert len(result) == 3
        assert result["list_var"].value == [1, 2, 3]
        assert result["dict_var"].value == {"key": "value"}
        assert result["nested"].value == {"list": [1, 2], "dict": {"nested": "value"}}
