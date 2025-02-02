import pytest
from uuid import UUID, uuid4
from datetime import datetime
from typing import Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from pythmata.core.engine.executor import ProcessExecutor
from pythmata.core.engine.instance import ProcessInstanceManager
from pythmata.core.engine.token import Token
from pythmata.core.engine.transaction import TransactionStatus
from pythmata.core.state import StateManager
from pythmata.models.process import ProcessDefinition, ProcessStatus

# Test Data
TRANSACTION_PROCESS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL">
    <bpmn:process id="Process_1">
        <bpmn:startEvent id="Start_1" />
        <bpmn:sequenceFlow id="Flow_1" sourceRef="Start_1" targetRef="Transaction_1" />
        <bpmn:transaction id="Transaction_1">
            <bpmn:incoming>Flow_1</bpmn:incoming>
            <bpmn:outgoing>Flow_2</bpmn:outgoing>
            <bpmn:startEvent id="Transaction_Start" />
            <bpmn:sequenceFlow id="Flow_3" sourceRef="Transaction_Start" targetRef="Task_1" />
            <bpmn:task id="Task_1" name="Task in Transaction">
                <bpmn:incoming>Flow_3</bpmn:incoming>
                <bpmn:outgoing>Flow_4</bpmn:outgoing>
            </bpmn:task>
            <bpmn:sequenceFlow id="Flow_4" sourceRef="Task_1" targetRef="Transaction_End" />
            <bpmn:endEvent id="Transaction_End" />
        </bpmn:transaction>
        <bpmn:sequenceFlow id="Flow_2" sourceRef="Transaction_1" targetRef="End_1" />
        <bpmn:endEvent id="End_1" />
    </bpmn:process>
</bpmn:definitions>
"""

@pytest.fixture
async def process_executor(state_manager: StateManager) -> ProcessExecutor:
    """Create a test process executor."""
    executor = ProcessExecutor(state_manager)
    return executor

@pytest.fixture
async def instance_manager(
    session: AsyncSession,
    process_executor: ProcessExecutor,
    state_manager: StateManager
) -> ProcessInstanceManager:
    """Create a test process instance manager."""
    manager = ProcessInstanceManager(session, process_executor, state_manager)
    process_executor.instance_manager = manager  # Set up circular reference
    return manager

@pytest.fixture
async def transaction_process_definition(session: AsyncSession) -> ProcessDefinition:
    """Create a test process definition with a transaction."""
    definition = ProcessDefinition(
        id=uuid4(),
        name="Transaction Test Process",
        version=1,
        bpmn_xml=TRANSACTION_PROCESS_XML
    )
    session.add(definition)
    await session.commit()
    return definition

async def test_basic_transaction_boundaries(
    session: AsyncSession,
    transaction_process_definition: ProcessDefinition,
    state_manager: StateManager,
    process_executor: ProcessExecutor,
    instance_manager: ProcessInstanceManager
):
    """
    Test basic transaction start and completion.
    
    Should:
    1. Create instance with transaction
    2. Start transaction when token reaches it
    3. Execute task within transaction scope
    4. Complete transaction successfully
    5. Complete overall process
    """
    # Create instance
    instance = await instance_manager.create_instance(transaction_process_definition.id)
    
    # Verify instance is running
    assert instance.status == ProcessStatus.RUNNING
    
    # Get initial token position at Start_1
    tokens = await state_manager.get_token_positions(str(instance.id))
    assert len(tokens) == 1
    assert tokens[0]["node_id"] == "Start_1"
    
    # Move token to Transaction_1
    token = Token.from_dict(tokens[0])
    await process_executor.move_token(token, "Transaction_1")
    
    # Verify transaction was started
    transaction = instance_manager.get_active_transaction(instance.id)
    assert transaction is not None
    assert transaction.id == "Transaction_1"
    assert transaction.status == TransactionStatus.ACTIVE
    
    # Verify token is at Transaction_Start
    tokens = await state_manager.get_token_positions(str(instance.id))
    assert len(tokens) == 1
    assert tokens[0]["node_id"] == "Transaction_Start"
    
    # Move token to Task_1
    token = Token.from_dict(tokens[0])
    await process_executor.move_token(token, "Task_1")
    
    # Move token to Transaction_End (this will trigger transaction completion and move to End_1)
    tokens = await state_manager.get_token_positions(str(instance.id))
    assert len(tokens) == 1
    assert tokens[0]["node_id"] == "Task_1"
    token = Token.from_dict(tokens[0])
    await process_executor.move_token(token, "Transaction_End")
    
    # Get final token position
    tokens = await state_manager.get_token_positions(str(instance.id))
    assert len(tokens) == 1
    assert tokens[0]["node_id"] == "End_1"
    
    # Verify transaction was completed
    assert instance_manager.get_active_transaction(instance.id) is None
    assert transaction.status == TransactionStatus.COMPLETED
    
    # Refresh instance to get latest state
    await session.refresh(instance)
    assert instance.status == ProcessStatus.COMPLETED
