from datetime import UTC, datetime
from typing import TYPE_CHECKING, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pythmata.core.engine.transaction import Transaction, TransactionStatus
from pythmata.core.state import StateManager
from pythmata.models.process import (
    ProcessDefinition,
    ProcessInstance,
    ProcessStatus,
    Variable,
)

if TYPE_CHECKING:
    from pythmata.core.engine.executor import ProcessExecutor


class ProcessInstanceError(Exception):
    """Base class for process instance errors."""

    pass


class TransactionError(ProcessInstanceError):
    """Raised when transaction operations fail."""

    pass


class InvalidProcessDefinitionError(ProcessInstanceError):
    """Raised when process definition is invalid."""

    pass


class InvalidVariableError(ProcessInstanceError):
    """Raised when variable data is invalid."""

    pass


class InvalidStateTransitionError(ProcessInstanceError):
    """Raised when attempting invalid state transition."""

    pass


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
        self._active_transactions: Dict[
            str, Transaction
        ] = {}  # instance_id -> Transaction

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

        # Initialize with start event
        if not start_event_id:
            start_event_id = "Start_1"  # Default start event

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
            if not isinstance(data, dict) or "type" not in data or "value" not in data:
                raise InvalidVariableError(
                    f"Invalid variable format for {name}. Expected {{'type': str, 'value': any}}"
                )

            if data["type"] not in self.VALID_VARIABLE_TYPES:
                raise InvalidVariableError(
                    f"Invalid variable type {data['type']} for {name}. "
                    f"Valid types: {', '.join(self.VALID_VARIABLE_TYPES)}"
                )

            variable = Variable(
                instance_id=instance.id,
                name=name,
                value_type=data["type"],
                value_data={"value": data["value"]},
                version=1,
            )
            self.session.add(variable)

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

        return {var.name: var.value_data["value"] for var in variables}
