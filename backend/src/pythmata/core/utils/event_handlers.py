"""Event handlers for process execution."""

from datetime import UTC, datetime

from pythmata.core.utils.error_utils import handle_process_errors
from pythmata.core.utils.process_utils import (
    create_process_instance,
    execute_process_with_graph,
    load_process_definition,
    parse_bpmn,
)
from pythmata.core.utils.service_utils import get_process_services
from pythmata.utils.logger import get_logger

logger = get_logger(__name__)


@handle_process_errors
async def handle_timer_triggered(data: dict) -> None:
    """
    Handle process.timer_triggered event by creating a process instance and publishing a process.started event.

    This function is specifically for handling timer events and avoids the event loop conflicts
    that can occur when creating process instances directly in the timer callback.

    Args:
        data: Dictionary containing instance_id, definition_id, and other timer information
    """
    instance_id = data["instance_id"]
    definition_id = data["definition_id"]
    logger.info(f"Handling process.timer_triggered event for instance {instance_id}")

    async with get_process_services() as (_, _, db, event_bus):
        # Create the process instance in the database
        async with db.session() as session:
            await create_process_instance(session, instance_id, definition_id)

        # Publish process.started event to trigger the normal process execution flow
        await event_bus.publish(
            "process.started",
            {
                "instance_id": instance_id,
                "definition_id": definition_id,
                "variables": {},
                "source": "timer_event",
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
        logger.info(
            f"Published process.started event for timer-triggered instance {instance_id}"
        )


@handle_process_errors
async def handle_process_started(data: dict) -> None:
    """
    Handle process.started event by initializing and executing a new process instance.

    This function follows BPMN lifecycle management best practices:
    1. Process Definition Loading
    2. Instance Initialization
    3. Token Creation and Management
    4. Process Execution

    Args:
        data: Dictionary containing instance_id and definition_id
    """
    instance_id = data["instance_id"]
    definition_id = data["definition_id"]
    logger.info(f"Handling process.started event for instance {instance_id}")

    async with get_process_services() as (_, state_manager, db, _):
        # 1. Load Process Definition
        async with db.session() as session:
            # Load definition
            definition = await load_process_definition(session, definition_id)
            if not definition:
                return

            # Create or get instance
            await create_process_instance(session, instance_id, definition_id)

            # Parse BPMN
            process_graph = parse_bpmn(definition.bpmn_xml)

        # 2. Execute Process
        async with db.session() as session:
            await execute_process_with_graph(
                instance_id, process_graph, state_manager, session
            )


async def register_event_handlers(event_bus) -> None:
    """Register event handlers with the event bus.

    Args:
        event_bus: The event bus to register handlers with
    """
    # Subscribe to process.started events
    await event_bus.subscribe(
        routing_key="process.started",
        callback=handle_process_started,
        queue_name="process_execution",
    )
    logger.info("Subscribed to process.started events")

    # Subscribe to process.timer_triggered events
    await event_bus.subscribe(
        routing_key="process.timer_triggered",
        callback=handle_timer_triggered,
        queue_name="timer_execution",
    )
    logger.info("Subscribed to process.timer_triggered events")
