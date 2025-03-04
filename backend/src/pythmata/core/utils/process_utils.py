"""Process execution utilities."""

from datetime import UTC, datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import select

from pythmata.core.bpmn.parser import BPMNParser
from pythmata.core.engine.executor import ProcessExecutor
from pythmata.core.engine.instance import ProcessInstanceManager
from pythmata.core.state import StateManager
from pythmata.models.process import ProcessDefinition as ProcessDefinitionModel
from pythmata.models.process import ProcessInstance, ProcessStatus
from pythmata.utils.logger import get_logger

logger = get_logger(__name__)


async def create_process_instance(
    session, instance_id: str, definition_id: str
) -> ProcessInstance:
    """Create or get a process instance.

    Args:
        session: Database session
        instance_id: The process instance ID
        definition_id: The process definition ID

    Returns:
        The created or existing process instance
    """
    # Check if process instance already exists in database
    instance_uuid = UUID(instance_id)
    instance_result = await session.execute(
        select(ProcessInstance).filter(ProcessInstance.id == instance_uuid)
    )
    instance = instance_result.scalar_one_or_none()

    # If instance doesn't exist, create it
    if not instance:
        logger.info(
            f"Process instance {instance_id} not found in database, creating it"
        )
        instance = ProcessInstance(
            id=instance_uuid,
            definition_id=UUID(definition_id),
            status=ProcessStatus.RUNNING,
            start_time=datetime.now(UTC),
        )
        session.add(instance)
        await session.commit()
        logger.info(f"Process instance {instance_id} created in database")
    else:
        logger.info(f"Process instance {instance_id} already exists in database")

    return instance


async def load_process_definition(
    session, definition_id: str
) -> Optional[ProcessDefinitionModel]:
    """Load process definition from database.

    Args:
        session: Database session
        definition_id: The process definition ID

    Returns:
        The process definition or None if not found
    """
    logger.info("Loading process definition...")
    stmt = select(ProcessDefinitionModel).filter(
        ProcessDefinitionModel.id == definition_id
    )
    logger.debug(f"Executing query: {stmt}")
    result = await session.execute(stmt)
    logger.debug(f"Query result type: {type(result)}")

    definition = result.scalar_one_or_none()
    logger.debug(f"Definition type: {type(definition)}, value: {definition}")

    if not definition:
        logger.error(f"Process definition {definition_id} not found")
        return None

    logger.info(f"Definition loaded successfully: {definition_id}")
    return definition


def parse_bpmn(bpmn_xml: str) -> Dict[str, Any]:
    """Parse BPMN XML into a process graph.

    Args:
        bpmn_xml: The BPMN XML string

    Returns:
        The parsed process graph

    Raises:
        ValueError: If BPMN XML is invalid or parsing fails
    """
    try:
        parser = BPMNParser()
        process_graph = parser.parse(bpmn_xml)
        logger.info("BPMN XML parsed successfully")
        return process_graph
    except ValueError as e:
        # Normalize validation error message
        if "Invalid BPMN XML" in str(e):
            logger.error(f"Failed to parse BPMN XML: Invalid format - {e}")
            raise ValueError("Invalid BPMN XML")
        logger.error(f"Failed to parse BPMN XML: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to parse BPMN XML: {e}")
        raise


def validate_start_event(process_graph: Dict[str, Any]) -> str:
    """Validate that the process graph has a start event.

    Args:
        process_graph: The parsed process graph

    Returns:
        The ID of the start event

    Raises:
        ValueError: If no start event is found
    """
    start_event = next(
        (
            node
            for node in process_graph["nodes"]
            if hasattr(node, "event_type") and node.event_type == "start"
        ),
        None,
    )
    if not start_event:
        logger.error("No start event found in process definition")
        raise ValueError("No start event found in process definition")

    logger.info(f"Validated start event: {start_event.id}")
    return start_event.id


async def execute_process_with_graph(
    instance_id: str,
    process_graph: Dict[str, Any],
    state_manager: StateManager,
    session,
) -> None:
    """Execute a process with the given graph.

    Args:
        instance_id: The process instance ID
        process_graph: The parsed process graph
        state_manager: The state manager
        session: Database session
    """
    # Create instance manager with proper initialization
    instance_manager = ProcessInstanceManager(session, None, state_manager)
    executor = ProcessExecutor(
        state_manager=state_manager, instance_manager=instance_manager
    )
    instance_manager.executor = executor

    # Check for existing tokens
    logger.debug("Checking for existing tokens...")
    existing_tokens = await state_manager.get_token_positions(instance_id)
    logger.debug(
        f"Token check result type: {type(existing_tokens)}, value: {existing_tokens}"
    )

    # Create initial token if none exist
    start_event_id = validate_start_event(process_graph)
    if existing_tokens is not None and len(existing_tokens) > 0:
        logger.info(
            f"Found existing tokens for instance {instance_id}: {existing_tokens}"
        )
        logger.debug("Skipping token creation due to existing tokens")
    else:
        logger.debug("No existing tokens found, creating initial token")
        initial_token = await executor.create_initial_token(instance_id, start_event_id)
        logger.info(f"Created initial token: {initial_token.id} at {start_event_id}")

    # Execute process
    logger.debug(f"Preparing to execute process with graph: {process_graph}")
    logger.info(f"Starting process execution for instance {instance_id}")
    await executor.execute_process(instance_id, process_graph)
    logger.info(f"Process {instance_id} execution completed successfully")
