from datetime import UTC, datetime
from typing import TYPE_CHECKING, Dict, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pythmata.api.schemas import ProcessVariableValue
from pythmata.core.bpmn.parser import BPMNParser
from pythmata.core.engine.transaction import Transaction
from pythmata.core.state import StateManager
from pythmata.core.types import Event, EventType
from pythmata.models.process import (
    ProcessDefinition,
    ProcessInstance,
    ProcessStatus,
    Variable,
)
from pythmata.utils.logger import get_logger

logger = get_logger(__name__)


if TYPE_CHECKING:
    from pythmata.core.engine.executor import ProcessExecutor


class ProcessInstanceError(Exception):
    """Base class for process instance errors."""


class TransactionError(ProcessInstanceError):
    """Raised when transaction operations fail."""


class InvalidProcessDefinitionError(ProcessInstanceError):
    """Raised when process definition is invalid."""


class InvalidVariableError(ProcessInstanceError):
    """Raised when variable data is invalid."""


class InvalidStateTransitionError(ProcessInstanceError):
    """Raised when attempting invalid state transition."""


class ProcessInstanceManager:
    """
    Manages the lifecycle of process instances including creation, state management,
    and control operations.
    """

    VALID_VARIABLE_TYPES = {"string", "integer", "boolean", "float", "json"}

    def __init__(
        self,
        session: AsyncSession,
        executor: "ProcessExecutor",
        state_manager: StateManager,
    ):
        self.session = session
        self.executor = executor
        self.state_manager = state_manager
        self._active_transactions: Dict[str, Transaction] = (
            {}
        )  # instance_id -> Transaction

    def _find_start_event(self, bpmn_xml: str) -> str:
        """
        Find the start event ID from BPMN XML.

        Args:
            bpmn_xml: BPMN XML string

        Returns:
            ID of the start event

        Raises:
            InvalidProcessDefinitionError: If no start event found
        """
        parser = BPMNParser()
        process_graph = parser.parse(bpmn_xml)

        # Find start event node
        start_event = next(
            (
                node
                for node in process_graph["nodes"]
                if isinstance(node, Event) and node.event_type == EventType.START
            ),
            None,
        )

        if not start_event:
            raise InvalidProcessDefinitionError("No start event found in BPMN XML")

        return start_event.id

    async def create_instance(
        self,
        process_definition_id: UUID,
        variables: Optional[Dict] = None,
        start_event_id: Optional[str] = None,
    ) -> ProcessInstance:
        """
        Create and initialize a new process instance.

        Args:
            process_definition_id: ID of the process definition
            variables: Optional initial variables
            start_event_id: Optional specific start event ID

        Returns:
            Initialized ProcessInstance

        Raises:
            InvalidProcessDefinitionError: If process definition is invalid
            InvalidVariableError: If variable data is invalid
        """
        # Validate process definition exists
        definition = await self.session.get(ProcessDefinition, process_definition_id)
        if not definition:
            raise InvalidProcessDefinitionError(
                f"Process definition {process_definition_id} not found"
            )

        # Create instance
        instance = ProcessInstance(
            definition_id=process_definition_id,
            status=ProcessStatus.RUNNING,
            start_time=datetime.now(UTC),
        )
        self.session.add(instance)
        await self.session.commit()  # Commit to get instance.id

        # Set up variables if provided
        if variables:
            await self._setup_variables(instance, variables)
            await self.session.commit()  # Commit variables separately
            # Refresh instance to load variables
            await self.session.refresh(instance)

        # Get process definition
        definition = await self.session.get(ProcessDefinition, process_definition_id)
        if not definition:
            raise InvalidProcessDefinitionError(
                f"Process definition {process_definition_id} not found"
            )

        # Find start event if not provided
        if not start_event_id:
            start_event_id = self._find_start_event(definition.bpmn_xml)

        await self.executor.create_initial_token(str(instance.id), start_event_id)

        return instance

    async def _setup_variables(
        self, instance: ProcessInstance, variables: Dict
    ) -> None:
        """
        Set up initial variables for a process instance.

        Args:
            instance: Process instance
            variables: Initial variables to set

        Raises:
            InvalidVariableError: If variable data is invalid
        """
        for name, data in variables.items():
            # Handle ProcessVariableValue format from API
            if isinstance(data, dict) and "value_type" in data and "value_data" in data:
                # Data is already in storage format
                var_type = data["value_type"]
                var_value = data["value_data"]
            elif isinstance(data, dict) and "type" in data and "value" in data:
                # Data is in API format
                var_type = data["type"]
                var_value = data["value"]
            else:
                raise InvalidVariableError(
                    f"Invalid variable format for {name}. Expected ProcessVariableValue format."
                )

            if var_type not in self.VALID_VARIABLE_TYPES:
                raise InvalidVariableError(
                    f"Invalid variable type {var_type} for {name}. "
                    f"Valid types: {', '.join(self.VALID_VARIABLE_TYPES)}"
                )

            # Validate value type matches declared type
            if var_type == "string" and not isinstance(var_value, str):
                raise InvalidVariableError(f"Value for {name} must be a string")
            elif var_type == "integer" and not isinstance(var_value, int):
                raise InvalidVariableError(f"Value for {name} must be an integer")
            elif var_type == "boolean" and not isinstance(var_value, bool):
                raise InvalidVariableError(f"Value for {name} must be a boolean")
            elif var_type == "float" and not isinstance(var_value, (int, float)):
                raise InvalidVariableError(f"Value for {name} must be a number")
            elif var_type == "json" and not isinstance(var_value, (dict, list)):
                raise InvalidVariableError(
                    f"Value for {name} must be a JSON object or array"
                )

            # Store in database - store raw value without wrapping
            variable = Variable(
                instance_id=instance.id,
                name=name,
                value_type=var_type,
                value_data=var_value,
                version=1,
            )
            self.session.add(variable)

            # Store in Redis state manager
            await self.state_manager.set_variable(
                instance_id=str(instance.id),
                name=name,
                variable=ProcessVariableValue(type=var_type, value=var_value),
            )

    async def suspend_instance(self, instance_id: UUID) -> ProcessInstance:
        """
        Suspend a running process instance.

        Args:
            instance_id: ID of the instance to suspend

        Returns:
            Updated ProcessInstance

        Raises:
            InvalidStateTransitionError: If instance is not in RUNNING state
        """
        instance = await self.session.get(ProcessInstance, instance_id)
        if not instance:
            raise ProcessInstanceError(f"Instance {instance_id} not found")

        if instance.status != ProcessStatus.RUNNING:
            raise InvalidStateTransitionError(
                f"Cannot suspend instance in {instance.status} state"
            )

        instance.status = ProcessStatus.SUSPENDED
        await self.session.commit()
        return instance

    async def resume_instance(self, instance_id: UUID) -> ProcessInstance:
        """
        Resume a suspended process instance.

        Args:
            instance_id: ID of the instance to resume

        Returns:
            Updated ProcessInstance

        Raises:
            InvalidStateTransitionError: If instance is not in SUSPENDED state
        """
        instance = await self.session.get(ProcessInstance, instance_id)
        if not instance:
            raise ProcessInstanceError(f"Instance {instance_id} not found")

        if instance.status not in [ProcessStatus.SUSPENDED, ProcessStatus.ERROR]:
            raise InvalidStateTransitionError(
                f"Cannot resume instance in {instance.status} state"
            )

        instance.status = ProcessStatus.RUNNING
        await self.session.commit()
        return instance

    async def terminate_instance(self, instance_id: UUID) -> ProcessInstance:
        """
        Terminate a process instance.

        Args:
            instance_id: ID of the instance to terminate

        Returns:
            Updated ProcessInstance
        """
        instance = await self.session.get(ProcessInstance, instance_id)
        if not instance:
            raise ProcessInstanceError(f"Instance {instance_id} not found")

        # Cancel any active transaction
        if str(instance_id) in self._active_transactions:
            transaction = self._active_transactions[str(instance_id)]
            transaction.cancel()
            del self._active_transactions[str(instance_id)]

        # Remove all tokens
        # Remove all tokens one by one since we don't have a bulk remove method
        tokens = await self.state_manager.get_token_positions(str(instance_id))
        for token in tokens:
            await self.state_manager.remove_token(str(instance_id), token["node_id"])

        instance.status = ProcessStatus.COMPLETED
        instance.end_time = datetime.now(UTC)
        await self.session.commit()
        return instance

    async def start_transaction(
        self, instance_id: UUID, transaction_id: str
    ) -> Transaction:
        """
        Start a new transaction for a process instance.

        Args:
            instance_id: ID of the process instance
            transaction_id: ID of the transaction element

        Returns:
            New Transaction instance

        Raises:
            TransactionError: If instance already has an active transaction
        """
        instance_str = str(instance_id)
        if instance_str in self._active_transactions:
            raise TransactionError(
                f"Instance {instance_id} already has an active transaction"
            )

        transaction = Transaction.start(transaction_id, instance_str)
        self._active_transactions[instance_str] = transaction
        return transaction

    async def complete_transaction(self, instance_id: UUID) -> None:
        """
        Complete the active transaction for a process instance.

        Args:
            instance_id: ID of the process instance

        Raises:
            TransactionError: If instance has no active transaction
        """
        instance_str = str(instance_id)
        if instance_str not in self._active_transactions:
            raise TransactionError(f"Instance {instance_id} has no active transaction")

        transaction = self._active_transactions[instance_str]
        transaction.complete()
        del self._active_transactions[instance_str]

    def get_active_transaction(self, instance_id: UUID) -> Optional[Transaction]:
        """
        Get the active transaction for a process instance if one exists.

        Args:
            instance_id: ID of the process instance

        Returns:
            Active Transaction instance or None if no active transaction
        """
        return self._active_transactions.get(str(instance_id))

    async def set_error_state(
        self, instance_id: UUID, error_message: Optional[str] = None
    ) -> ProcessInstance:
        """
        Set a process instance to error state.

        Args:
            instance_id: ID of the instance
            error_message: Optional error message to store

        Returns:
            Updated ProcessInstance
        """
        instance = await self.session.get(ProcessInstance, instance_id)
        if not instance:
            raise ProcessInstanceError(f"Instance {instance_id} not found")

        instance.status = ProcessStatus.ERROR
        # TODO: Add error message storage
        await self.session.commit()
        return instance

    async def handle_error(
        self, instance_id: str, error: Exception, node_id: Optional[str] = None
    ) -> None:
        """
        Handle process instance errors by setting error state and cleaning up.

        Args:
            instance_id: ID of the instance where error occurred
            error: The exception that was raised
            node_id: Optional ID of the node where error occurred
        """
        from pythmata.utils.logger import get_logger

        logger = get_logger(__name__)

        logger.error(
            f"Error in process instance {instance_id} at node {node_id}: {str(error)}"
        )

        try:
            # Set instance to error state
            await self.set_error_state(UUID(instance_id), str(error))

            # Clean up any stale Redis state
            keys = await self.state_manager.redis.keys(f"process:{instance_id}:*")
            logger.info(f"[ErrorCleanup] Found Redis keys to clean: {keys}")

            # Remove any stale locks
            lock_key = f"lock:process:{instance_id}"
            if await self.state_manager.redis.exists(lock_key):
                logger.info(f"[ErrorCleanup] Removing stale lock: {lock_key}")
                await self.state_manager.redis.delete(lock_key)

            # Log final state for debugging
            tokens = await self.state_manager.get_token_positions(instance_id)
            logger.info(f"[ErrorState] Final token positions: {tokens}")

        except Exception as e:
            logger.error(f"Error during error handling: {str(e)}")
            # Don't raise here - we don't want to mask the original error

    async def get_instance_variables(
        self, instance_id: UUID, scope_id: Optional[str] = None
    ) -> Dict:
        """
        Get all variables for a process instance.

        Args:
            instance_id: ID of the instance
            scope_id: Optional scope ID to filter variables

        Returns:
            Dictionary of variable name to value
        """
        query = select(Variable).where(Variable.instance_id == instance_id)
        if scope_id:
            query = query.where(Variable.scope_id == scope_id)

        result = await self.session.execute(query)
        variables = result.scalars().all()

        return {var.name: var.value_data for var in variables}

    async def complete_instance(self, instance_id: UUID) -> ProcessInstance:
        """
        Complete a process instance.

        Args:
            instance_id: ID of the instance to complete

        Returns:
            Updated ProcessInstance
        """

        instance = await self.session.get(ProcessInstance, instance_id)
        if not instance:
            raise ProcessInstanceError(f"Instance {instance_id} not found")

        # Clean up Redis state
        instance_str = str(instance_id)
        logger.info(f"[Completion] Cleaning up Redis state for instance {instance_str}")

        # Remove all tokens
        tokens = await self.state_manager.get_token_positions(instance_str)
        for token in tokens:
            logger.debug(f"[Completion] Removing token: {token}")
            await self.state_manager.remove_token(instance_str, token["node_id"])

        # Remove any locks
        lock_key = f"lock:process:{instance_str}"
        if await self.state_manager.redis.exists(lock_key):
            logger.debug(f"[Completion] Removing lock: {lock_key}")
            await self.state_manager.redis.delete(lock_key)

        # Remove all Redis keys for this instance
        keys = await self.state_manager.redis.keys(f"process:{instance_str}:*")
        if keys:
            logger.debug(f"[Completion] Removing Redis keys: {keys}")
            await self.state_manager.redis.delete(*keys)

        # Update instance status
        instance.status = ProcessStatus.COMPLETED
        instance.end_time = datetime.now(UTC)
        await self.session.commit()

        logger.info(f"[Completion] Instance {instance_str} completed successfully")
        return instance

    async def start_instance(
        self,
        instance: ProcessInstance,
        bpmn_xml: str,
        variables: Optional[Dict] = None,
        start_event_id: Optional[str] = None,
    ) -> ProcessInstance:
        """
        Start a process instance by initializing its execution state.

        Args:
            instance: The process instance to start
            bpmn_xml: BPMN XML definition for the process
            variables: Optional initial variables
            start_event_id: ID of the start event (defaults to "Start_1")

        Returns:
            The started ProcessInstance

        Raises:
            InvalidProcessDefinitionError: If process definition is invalid
            InvalidVariableError: If variable data is invalid
        """
        # Set up variables if provided
        if variables:
            await self._setup_variables(instance, variables)

        # Find start event if not provided
        if not start_event_id:
            start_event_id = self._find_start_event(bpmn_xml)

        # Initialize process state with start event
        await self.executor.create_initial_token(str(instance.id), start_event_id)

        # Update instance status
        instance.status = ProcessStatus.RUNNING
        instance.start_time = datetime.now(UTC)

        return instance
