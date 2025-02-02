import pytest
from pythmata.core.engine.transaction import Transaction, TransactionContext, TransactionStatus
from pythmata.core.engine.events.compensation import CompensationBoundaryEvent
from pythmata.core.engine.token import Token, TokenState

@pytest.mark.asyncio
async def test_basic_transaction_success():
    """Test successful transaction execution and commit"""
    # Setup transaction structure:
    # Transaction_1
    #   ├─ Task_1 (with compensation handler)
    #   └─ Task_2 (with compensation handler)
    
    # Create transaction
    transaction = Transaction.start("Transaction_1", "test_instance")
    
    # Setup compensation handlers
    handler1_id = "CompensationHandler_1"
    handler2_id = "CompensationHandler_2"
    
    boundary_event1 = CompensationBoundaryEvent(
        event_id="CompensationBoundary_1",
        attached_to_id="Task_1",
        handler_id=handler1_id,
        scope=transaction
    )
    
    boundary_event2 = CompensationBoundaryEvent(
        event_id="CompensationBoundary_2",
        attached_to_id="Task_2",
        handler_id=handler2_id,
        scope=transaction
    )
    
    # Create transaction context
    context = TransactionContext(transaction)
    
    # Simulate successful task execution
    token1 = Token(
        instance_id="test_instance",
        node_id="Task_1",
        state=TokenState.ACTIVE,
        data={"task": 1, "value": "first"}
    )
    
    token2 = Token(
        instance_id="test_instance",
        node_id="Task_2",
        state=TokenState.ACTIVE,
        data={"task": 2, "value": "second"}
    )
    
    # Record task completion
    await context.record_completion(token1)
    await context.record_completion(token2)
    
    # Commit transaction
    result = await context.commit()
    
    # Verify successful commit
    assert result.state == TokenState.ACTIVE
    assert context.state == TransactionStatus.COMMITTED
    assert not context.requires_compensation()

@pytest.mark.asyncio
async def test_basic_transaction_rollback():
    """Test transaction rollback with compensation"""
    # Setup transaction structure
    transaction = Transaction.start("Transaction_1", "test_instance")
    
    # Setup compensation handler
    handler_id = "CompensationHandler_1"
    boundary_event = CompensationBoundaryEvent(
        event_id="CompensationBoundary_1",
        attached_to_id="Task_1",
        handler_id=handler_id,
        scope=transaction
    )
    
    # Create transaction context
    context = TransactionContext(transaction)
    
    # Simulate task execution
    token = Token(
        instance_id="test_instance",
        node_id="Task_1",
        state=TokenState.ACTIVE,
        data={"task": 1, "value": "test"}
    )
    
    # Record task completion
    await context.record_completion(token)
    
    # Trigger rollback
    result = await context.rollback()
    
    # Verify compensation was triggered
    assert result.state == TokenState.COMPENSATION
    assert result.node_id == handler_id
    assert context.state == TransactionStatus.COMPENSATING
    assert context.requires_compensation()
    assert result.data["compensated_activity_id"] == "Task_1"
    assert result.data["original_activity_data"] == {"task": 1, "value": "test"}

@pytest.mark.asyncio
async def test_transaction_boundary_tracking():
    """Test transaction boundary and participation tracking"""
    # Setup transaction
    transaction = Transaction.start("Transaction_1", "test_instance")
    context = TransactionContext(transaction)
    
    # Create tokens for different activities
    token1 = Token(
        instance_id="test_instance",
        node_id="Task_1",
        state=TokenState.ACTIVE,
        data={"task": 1}
    )
    
    token2 = Token(
        instance_id="test_instance",
        node_id="Task_2",
        state=TokenState.ACTIVE,
        data={"task": 2}
    )
    
    # Record task participation
    await context.record_completion(token1)
    
    # Verify participation tracking
    assert context.has_participant("Task_1")
    assert not context.has_participant("Task_2")
    
    # Record second task
    await context.record_completion(token2)
    
    # Verify both tasks are tracked
    assert context.has_participant("Task_1")
    assert context.has_participant("Task_2")
    
    # Verify transaction state
    assert context.state == TransactionStatus.ACTIVE
    assert len(context.get_participants()) == 2

@pytest.mark.asyncio
async def test_nested_transaction_rollback():
    """Test rollback behavior with nested transactions"""
    # Setup nested structure:
    # Transaction_1
    #   └─ Transaction_2
    #        └─ Task_1 (with compensation handler)
    
    # Create parent and child transactions
    parent_transaction = Transaction.start("Transaction_1", "test_instance")
    child_transaction = Transaction("Transaction_2", "test_instance", parent_scope=parent_transaction)
    
    # Setup compensation handler in child transaction
    handler_id = "CompensationHandler_1"
    boundary_event = CompensationBoundaryEvent(
        event_id="CompensationBoundary_1",
        attached_to_id="Task_1",
        handler_id=handler_id,
        scope=child_transaction
    )
    
    # Create transaction contexts
    parent_context = TransactionContext(parent_transaction)
    child_context = TransactionContext(child_transaction)
    
    # Simulate task execution in child transaction
    token = Token(
        instance_id="test_instance",
        node_id="Task_1",
        state=TokenState.ACTIVE,
        data={"task": 1, "value": "nested"}
    )
    
    # Record completion in child transaction
    await child_context.record_completion(token)
    
    # Rollback child transaction
    result = await child_context.rollback()
    
    # Verify child transaction compensation
    assert result.state == TokenState.COMPENSATION
    assert result.node_id == handler_id
    assert child_context.state == TransactionStatus.COMPENSATING
    assert child_context.requires_compensation()
    assert result.data["compensated_activity_id"] == "Task_1"
    assert result.data["compensation_scope_id"] == "Transaction_2"
    
    # Verify parent transaction is unaffected
    assert parent_context.state == TransactionStatus.ACTIVE
    assert not parent_context.requires_compensation()
