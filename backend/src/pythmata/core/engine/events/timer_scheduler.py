"""Timer scheduler for handling timer start events in BPMN processes."""

import asyncio
import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from pythmata.core.bpmn.parser import BPMNParser
from pythmata.core.database import get_db
from pythmata.core.engine.events.timer_parser import (
    find_timer_events_in_definition,
    parse_timer_definition,
)
from pythmata.core.events import EventBus
from pythmata.core.state import StateManager
from pythmata.models.process import ProcessDefinition
from pythmata.utils.logger import get_logger

logger = get_logger(__name__)


class TimerScheduler:
    """
    Scheduler for BPMN timer start events.

    Scans process definitions for timer start events and schedules them
    using APScheduler with Redis persistence.
    """

    def __init__(self, state_manager: StateManager, event_bus: EventBus):
        """
        Initialize timer scheduler.

        Args:
            state_manager: Manager for process state
            event_bus: Event bus for publishing events
        """
        self.state_manager = state_manager
        self.event_bus = event_bus
        self.parser = BPMNParser()
        self._running = False
        self._scan_interval = 60  # Scan for new timer definitions every 60 seconds
        self._scheduler: Optional[AsyncIOScheduler] = None
        self._scan_task: Optional[asyncio.Task] = None
        self._timer_prefix = "pythmata:timer:"
        self._process_definitions_hash: Optional[str] = None
        self._scheduled_timer_ids: Set[str] = set()
        self._recovery_metadata: List[Dict] = []

    async def start(self) -> None:
        """Start the timer scheduler."""
        if self._running:
            return

        # Initialize and start scheduler
        self._scheduler = await self._create_scheduler()
        self._scheduler.start()
        logger.info("Timer scheduler started with Redis job store")

        # Schedule any timers from recovery metadata
        await self._schedule_recovery_timers()

        # Start the scanner task
        self._running = True
        self._scan_task = asyncio.create_task(self._scheduler_loop())

        # Perform initial scan
        await self._scan_for_timer_start_events()

    async def stop(self) -> None:
        """Stop the timer scheduler."""
        if not self._running:
            return

        self._running = False

        # Cancel the scanner task
        if self._scan_task and not self._scan_task.done():
            self._scan_task.cancel()
            try:
                await self._scan_task
            except asyncio.CancelledError:
                pass

        # Shutdown the scheduler
        if self._scheduler:
            self._scheduler.shutdown()
            logger.info("APScheduler shut down")

        logger.info("Timer scheduler stopped")

    async def recover_from_crash(self) -> None:
        """
        Recover timer state after a system crash or restart.

        Loads timer metadata from Redis for rescheduling after start.
        """
        try:
            logger.info("Recovering timer state from Redis")

            # Find all timer metadata keys
            pattern = f"{self._timer_prefix}*:metadata"
            keys = await self.state_manager.redis.keys(pattern)

            # Store metadata for later rescheduling
            self._recovery_metadata = []

            for key in keys:
                try:
                    # Extract timer ID from key
                    timer_id = key.replace(":metadata", "")

                    # Get timer metadata
                    metadata_json = await self.state_manager.redis.get(key)
                    if not metadata_json:
                        continue

                    metadata = json.loads(metadata_json)

                    # Store metadata for later rescheduling after start() is called
                    self._recovery_metadata.append(
                        {
                            "timer_id": timer_id,
                            "definition_id": metadata["definition_id"],
                            "node_id": metadata["node_id"],
                            "timer_def": metadata["timer_def"],
                        }
                    )

                except Exception as e:
                    logger.error(
                        f"Error recovering timer metadata {key}: {e}", exc_info=True
                    )

            logger.info(f"Found {len(self._recovery_metadata)} timers to recover")

            # If scheduler is already initialized, schedule the timers now
            if self._scheduler is not None:
                await self._schedule_recovery_timers()

        except Exception as e:
            logger.error(f"Error recovering timer state: {e}", exc_info=True)

    async def _create_scheduler(self) -> AsyncIOScheduler:
        """
        Create and configure the APScheduler instance.

        Returns:
            Configured AsyncIOScheduler instance
        """
        return AsyncIOScheduler(
            jobstores={
                "default": RedisJobStore(
                    jobs_key="pythmata:jobs",
                    run_times_key="pythmata:run_times",
                    host=self.state_manager.redis.connection_pool.connection_kwargs[
                        "host"
                    ],
                    port=self.state_manager.redis.connection_pool.connection_kwargs[
                        "port"
                    ],
                    db=self.state_manager.redis.connection_pool.connection_kwargs.get(
                        "db", 0
                    ),
                )
            },
            executors={"default": AsyncIOExecutor()},
            job_defaults={
                "coalesce": True,  # Combine multiple pending executions into one
                "max_instances": 1,  # Only allow one instance of each job to run at a time
                "misfire_grace_time": 60,  # Allow jobs to be 60 seconds late
            },
        )

    async def _schedule_recovery_timers(self) -> None:
        """Schedule timers from recovery metadata."""
        if not self._recovery_metadata:
            return

        logger.info(
            f"Scheduling {len(self._recovery_metadata)} timers from recovery metadata"
        )
        for metadata in self._recovery_metadata:
            await self._schedule_timer(
                metadata["timer_id"],
                metadata["definition_id"],
                metadata["node_id"],
                metadata["timer_def"],
            )
        # Clear recovery metadata after scheduling
        self._recovery_metadata = []

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop that periodically scans for timer start events."""
        while self._running:
            try:
                # Check if process definitions have changed
                current_hash = await self._get_process_definitions_hash()
                if current_hash != self._process_definitions_hash:
                    logger.info(
                        "Process definitions changed, rescanning for timer events"
                    )
                    self._process_definitions_hash = current_hash
                    await self._scan_for_timer_start_events()
                else:
                    logger.debug("No changes in process definitions, skipping scan")
            except Exception as e:
                logger.error(f"Error in timer scheduler loop: {e}", exc_info=True)

            # Wait before next scan
            await asyncio.sleep(self._scan_interval)

    async def _get_process_definitions_hash(self) -> str:
        """
        Get a hash of all process definitions to detect changes.

        Returns:
            Hash string representing the current state of process definitions
        """
        try:
            db = get_db()
            async with db.session() as session:
                result = await session.execute(
                    select(ProcessDefinition.id, ProcessDefinition.updated_at)
                )
                definitions = result.all()

                # Create a string representation of all definition IDs and update timestamps
                definitions_str = "|".join(
                    f"{d.id}:{d.updated_at.isoformat()}" for d in definitions
                )

                # Use a simple hash function
                return hashlib.md5(definitions_str.encode()).hexdigest()
        except Exception as e:
            logger.error(f"Error getting process definitions hash: {e}", exc_info=True)
            return ""

    async def _scan_for_timer_start_events(self) -> None:
        """
        Scan all process definitions for timer start events.

        Finds timer start events in all process definitions and schedules them.
        """
        logger.info("Scanning for timer start events")

        # Track timer IDs found in this scan
        found_timer_ids = set()

        # Get all process definitions from database
        db = get_db()
        async with db.session() as session:
            result = await session.execute(select(ProcessDefinition))
            definitions = result.scalars().all()

            for definition in definitions:
                try:
                    # Find timer start events in the definition
                    timer_events = find_timer_events_in_definition(
                        definition.bpmn_xml, self._timer_prefix, str(definition.id)
                    )

                    # Schedule each timer event
                    for timer_id, node_id, timer_def in timer_events:
                        found_timer_ids.add(timer_id)
                        await self._schedule_timer(
                            timer_id, str(definition.id), node_id, timer_def
                        )

                except Exception as e:
                    logger.error(
                        f"Error processing definition {definition.id}: {e}",
                        exc_info=True,
                    )

        # Remove timers for deleted process definitions
        timers_to_remove = self._scheduled_timer_ids - found_timer_ids
        for timer_id in timers_to_remove:
            await self._remove_timer(timer_id)

        logger.info(
            f"Timer scan complete. Active timers: {len(self._scheduled_timer_ids)}"
        )

    async def _schedule_timer(
        self, timer_id: str, definition_id: str, node_id: str, timer_def: str
    ) -> None:
        """
        Schedule a timer for execution using APScheduler.

        Args:
            timer_id: Unique ID for the timer
            definition_id: Process definition ID
            node_id: Start event node ID
            timer_def: Timer definition string
        """
        try:
            # Parse the timer definition
            timer_definition = parse_timer_definition(timer_def)
            if not timer_definition:
                logger.error(f"Failed to parse timer definition: {timer_def}")
                return

            # Store timer metadata in Redis for recovery
            timer_metadata = {
                "definition_id": definition_id,
                "node_id": node_id,
                "timer_def": timer_def,
                "timer_type": timer_definition.timer_type,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            await self.state_manager.redis.set(
                f"{timer_id}:metadata", json.dumps(timer_metadata)
            )

            # If scheduler is not initialized yet, store metadata for later scheduling
            if self._scheduler is None:
                logger.info(
                    f"Scheduler not initialized yet, storing metadata for timer {timer_id}"
                )
                self._recovery_metadata.append(
                    {
                        "timer_id": timer_id,
                        "definition_id": definition_id,
                        "node_id": node_id,
                        "timer_def": timer_def,
                    }
                )
                return

            # Check if job already exists
            job = self._scheduler.get_job(timer_id)
            if job:
                logger.info(f"Updating existing timer job: {timer_id}")
                job.reschedule(timer_definition.trigger)
            else:
                logger.info(
                    f"Scheduling new timer job: {timer_id} with definition {timer_def}"
                )
                # Use the standalone function for the callback
                self._scheduler.add_job(
                    timer_callback,
                    trigger=timer_definition.trigger,
                    id=timer_id,
                    replace_existing=True,
                    kwargs={
                        "timer_id": timer_id,
                        "definition_id": definition_id,
                        "node_id": node_id,
                        "timer_type": timer_definition.timer_type,
                        "timer_def": timer_def,
                    },
                )

            # Add to set of scheduled timers
            self._scheduled_timer_ids.add(timer_id)

        except Exception as e:
            logger.error(f"Error scheduling timer {timer_id}: {e}", exc_info=True)

    async def _remove_timer(self, timer_id: str) -> None:
        """
        Remove a scheduled timer.

        Args:
            timer_id: ID of the timer to remove
        """
        try:
            # If scheduler is not initialized yet, remove from recovery metadata
            if self._scheduler is None:
                self._recovery_metadata = [
                    m for m in self._recovery_metadata if m["timer_id"] != timer_id
                ]
                return

            # Remove from APScheduler
            self._scheduler.remove_job(timer_id)

            # Remove from Redis
            await self.state_manager.redis.delete(f"{timer_id}:metadata")

            # Remove from set of scheduled timers
            self._scheduled_timer_ids.discard(timer_id)

            logger.info(f"Removed timer: {timer_id}")
        except Exception as e:
            logger.error(f"Error removing timer {timer_id}: {e}", exc_info=True)


def timer_callback(
    timer_id: str, definition_id: str, node_id: str, timer_type: str, timer_def: str
) -> None:
    """
    Standalone callback function for timer events.

    Creates a new process instance when a timer is triggered.

    Args:
        timer_id: ID of the timer
        definition_id: Process definition ID
        node_id: Start event node ID
        timer_type: Type of timer (duration, date, cycle)
        timer_def: Timer definition string
    """
    from pythmata.core.config import Settings
    from pythmata.core.database import get_db
    from pythmata.core.events import EventBus
    from pythmata.core.state import StateManager
    from pythmata.models.process import ProcessInstance, ProcessStatus

    logger.info(f"Timer {timer_id} triggered for process {definition_id}")

    # Create a new event loop for this thread
    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)

    try:
        # Get settings from environment
        settings = Settings()

        # Create new instances for this callback
        state_manager = StateManager(settings)
        event_bus = EventBus(settings)
        db = get_db()

        # Connect to services
        new_loop.run_until_complete(state_manager.connect())
        new_loop.run_until_complete(event_bus.connect())
        new_loop.run_until_complete(db.connect())

        try:
            # Generate a unique instance ID
            instance_id = str(uuid.uuid4())

            # Create the process instance in the database
            async def create_process_instance():
                async with db.session() as session:
                    process_instance = ProcessInstance(
                        id=uuid.UUID(instance_id),
                        definition_id=uuid.UUID(definition_id),
                        status=ProcessStatus.RUNNING,
                        start_time=datetime.now(timezone.utc),
                    )
                    session.add(process_instance)
                    await session.commit()
                    logger.info(f"Process instance {instance_id} created in database")
                return instance_id

            # Create the process instance
            instance_id = new_loop.run_until_complete(create_process_instance())

            # Publish process.started event
            async def publish_event():
                await event_bus.publish(
                    "process.started",
                    {
                        "instance_id": instance_id,
                        "definition_id": definition_id,
                        "variables": {},
                        "source": "timer_scheduler",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
                logger.info(
                    f"Started process instance {instance_id} from definition {definition_id}"
                )

            new_loop.run_until_complete(publish_event())

        finally:
            # Disconnect from services
            new_loop.run_until_complete(db.disconnect())
            new_loop.run_until_complete(state_manager.disconnect())
            new_loop.run_until_complete(event_bus.disconnect())

    except Exception as e:
        logger.error(f"Error in timer callback for {timer_id}: {e}", exc_info=True)
    finally:
        new_loop.close()
