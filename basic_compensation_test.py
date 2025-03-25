import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from pythmata.core.engine.events.compensation import (
    CompensationActivity,
    CompensationBoundaryEvent,
    CompensationScope
)
from pythmata.core.engine.token import Token, TokenState


class MockRedis:
    def __init__(self):
        self.data = {}
        
    async def set(self, key, value):
        self.data[key] = value
        
    async def get(self, key):
        return self.data.get(key)
        
    async def delete(self, key):
        if key in self.data:
            del self.data[key]
            
    async def rpush(self, key, *values):
        if key not in self.data:
            self.data[key] = []
        self.data[key].extend(values)
        
    async def lrange(self, key, start, end):
        if key not in self.data:
            return []
        return self.data[key][start:end if end != -1 else None]


class MockStateManager:
    def __init__(self):
        self.redis = MockRedis()
        
    async def store_compensation_handler(self, instance_id, activity_id, handler_data):
        key = f"compensation:{instance_id}:{activity_id}"
        await self.redis.set(key, json.dumps(handler_data))
        
        # Also add this to the list of all compensation handlers for this instance
        all_handlers_key = f"compensation:{instance_id}:all"
        await self.redis.rpush(all_handlers_key, json.dumps({
            "activity_id": activity_id,
            **handler_data
        }))
    
    async def get_compensation_handler(self, instance_id, activity_id):
        key = f"compensation:{instance_id}:{activity_id}"
        handler_json = await self.redis.get(key)
        if handler_json:
            return json.loads(handler_json)
        return None
    
    async def get_all_compensation_handlers(self, instance_id):
        key = f"compensation:{instance_id}:all"
        handlers_json = await self.redis.lrange(key, 0, -1)
        return [json.loads(handler) for handler in handlers_json]
    
    async def clear_compensation_handlers(self, instance_id):
        # Get all handler keys
        all_handlers_key = f"compensation:{instance_id}:all"
        handlers_json = await self.redis.lrange(all_handlers_key, 0, -1)
        handlers = [json.loads(handler) for handler in handlers_json]
        
        # Delete individual handler mappings
        for handler in handlers:
            activity_id = handler.get("activity_id")
            if activity_id:
                key = f"compensation:{instance_id}:{activity_id}"
                await self.redis.delete(key)
        
        # Delete the list of all handlers
        await self.redis.delete(all_handlers_key)
        
    async def add_token(self, instance_id, node_id, data):
        # Stub method, not needed for testing
        pass


@pytest.mark.asyncio
async def test_compensation_boundary_event():
    """Test that compensation boundary events register handlers correctly."""
    # Create a compensation scope
    process_scope = CompensationScope(scope_id="Process_1")
    
    # Create a handler for Task_1
    handler_id = "CompensationHandler_1"
    boundary_event = CompensationBoundaryEvent(
        event_id="BoundaryEvent_1",
        attached_to_id="Task_1",
        handler_id=handler_id,
        scope=process_scope
    )
    
    # Verify handler was added to scope
    assert len(process_scope.handlers) == 1
    assert process_scope.handlers[0].handler_id == handler_id
    assert process_scope.handlers[0].attached_to_id == "Task_1"
    
    # Create a token for compensation
    token = Token(
        instance_id="test_instance",
        node_id="Task_1",
        state=TokenState.COMPENSATION,
        data={"compensate_scope_id": "Process_1"}
    )
    
    # Execute the boundary event
    result = await boundary_event.execute(token)
    
    # Verify the result
    assert result.state == TokenState.ACTIVE
    assert result.node_id == handler_id
    assert result.data["compensated_activity_id"] == "Task_1"
    assert result.data["compensation_scope_id"] == "Process_1"


@pytest.mark.asyncio
async def test_compensation_scope_handlers():
    """Test that compensation scope properly manages handlers."""
    # Create scopes
    parent_scope = CompensationScope(scope_id="Parent")
    child_scope = CompensationScope(scope_id="Child", parent_scope=parent_scope)
    
    # Create handlers
    handler1 = CompensationBoundaryEvent(
        event_id="BoundaryEvent_1",
        attached_to_id="Task_1",
        handler_id="Handler_1",
        scope=parent_scope
    )
    
    handler2 = CompensationBoundaryEvent(
        event_id="BoundaryEvent_2",
        attached_to_id="Task_2",
        handler_id="Handler_2",
        scope=child_scope
    )
    
    # Verify handlers were added to correct scopes
    assert len(parent_scope.handlers) == 1
    assert len(child_scope.handlers) == 1
    
    # Test get_handler_for_activity
    parent_handler = parent_scope.get_handler_for_activity("Task_1")
    assert parent_handler and parent_handler.handler_id == "Handler_1"
    
    child_handler = child_scope.get_handler_for_activity("Task_2")
    assert child_handler and child_handler.handler_id == "Handler_2"
    
    # Test is_ancestor_of
    assert parent_scope.is_ancestor_of(child_scope)
    assert not child_scope.is_ancestor_of(parent_scope)


@pytest.mark.asyncio
async def test_compensation_activity_execute():
    """Test the execution of a compensation activity."""
    # Create a compensation activity
    activity = CompensationActivity(
        event_id="CompensationActivity_1",
        compensate_activity_id="Task_1",
        scope=CompensationScope(scope_id="Process_1")
    )
    
    # Create a token
    token = Token(
        instance_id="test_instance",
        node_id="CompensationActivity_1",
        state=TokenState.ACTIVE,
        data={}
    )
    
    # Execute the activity
    result = await activity.execute(token)
    
    # Verify the result
    assert result.state == TokenState.COMPENSATION
    assert result.data["compensate_activity_id"] == "Task_1"
    assert result.data["compensate_scope_id"] == "Process_1"


if __name__ == "__main__":
    import asyncio
    
    # Run the tests
    asyncio.run(test_compensation_boundary_event())
    asyncio.run(test_compensation_scope_handlers())
    asyncio.run(test_compensation_activity_execute())
    
    print("All tests passed!") 