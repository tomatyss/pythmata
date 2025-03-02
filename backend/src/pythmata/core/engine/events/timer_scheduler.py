"""Timer scheduler for handling timer start events."""

import asyncio
import datetime
import json
import logging
import uuid
from typing import Dict, List, Optional, Set, Tuple, Union

from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from pythmata.core.bpmn.parser import BPMNParser
from pythmata.core.engine.events.timer import TimerEvent
from pythmata.core.events import EventBus
from pythmata.core.state import StateManager
from pythmata.models.process import ProcessDefinition
from pythmata.utils.logger import get_logger

logger = get_logger(__name__)


class TimerScheduler:
    """
    Robust scheduler for timer start events.
    
    This class is responsible for:
    1. Scanning process definitions for timer start events
    2. Scheduling timers based on their definitions using APScheduler
    3. Persisting timer state in Redis for fault tolerance
    4. Triggering process instances when timers expire
    5. Supporting distributed timer execution
    
    Features:
    - Persistent job storage using Redis
    - Efficient scheduling using APScheduler
    - Support for all timer types (duration, date, cycle)
    - Fault tolerance with automatic recovery
    - Distributed timer execution support
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
        self._scheduler = None
        self._scan_task = None
        self._timer_prefix = "pythmata:timer:"
        self._process_definitions_hash = None  # Hash of process definitions to detect changes
        
        # Set of timer IDs that are currently scheduled
        self._scheduled_timer_ids: Set[str] = set()

    async def start(self) -> None:
        """Start the timer scheduler."""
        if self._running:
            return
        
        # Initialize APScheduler with Redis job store
        self._scheduler = AsyncIOScheduler(
            jobstores={
                'default': RedisJobStore(
                    jobs_key='pythmata:jobs',
                    run_times_key='pythmata:run_times',
                    host=self.state_manager.redis.connection_pool.connection_kwargs['host'],
                    port=self.state_manager.redis.connection_pool.connection_kwargs['port'],
                    db=self.state_manager.redis.connection_pool.connection_kwargs.get('db', 0)
                )
            },
            executors={
                'default': AsyncIOExecutor()
            },
            job_defaults={
                'coalesce': True,  # Combine multiple pending executions into one
                'max_instances': 1,  # Only allow one instance of each job to run at a time
                'misfire_grace_time': 60  # Allow jobs to be 60 seconds late
            }
        )
        
        # Start the scheduler
        self._scheduler.start()
        logger.info("APScheduler started with Redis job store")
        
        # Start the scanner task
        self._running = True
        self._scan_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Timer scheduler started")
        
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

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop that periodically scans for timer start events."""
        while self._running:
            try:
                # Check if process definitions have changed
                current_hash = await self._get_process_definitions_hash()
                if current_hash != self._process_definitions_hash:
                    logger.info("Process definitions changed, rescanning for timer events")
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
            async with self.state_manager.db.session() as session:
                result = await session.execute(select(ProcessDefinition.id, ProcessDefinition.updated_at))
                definitions = result.all()
                
                # Create a string representation of all definition IDs and update timestamps
                definitions_str = "|".join(f"{d.id}:{d.updated_at.isoformat()}" for d in definitions)
                
                # Use a simple hash function
                import hashlib
                return hashlib.md5(definitions_str.encode()).hexdigest()
        except Exception as e:
            logger.error(f"Error getting process definitions hash: {e}", exc_info=True)
            return ""

    async def _scan_for_timer_start_events(self) -> None:
        """
        Scan all process definitions for timer start events.
        
        This method:
        1. Retrieves all process definitions from the database
        2. Parses each definition to find timer start events
        3. Schedules or updates timers for each timer start event
        4. Removes timers for deleted process definitions
        """
        logger.info("Scanning for timer start events")
        
        # Track timer IDs found in this scan
        found_timer_ids = set()
        
        # Get all process definitions from database
        async with self.state_manager.db.session() as session:
            result = await session.execute(select(ProcessDefinition))
            definitions = result.scalars().all()
            
            for definition in definitions:
                try:
                    # Parse BPMN XML
                    process_graph = self.parser.parse(definition.bpmn_xml)
                    
                    # Find timer start events
                    for node in process_graph["nodes"]:
                        if (hasattr(node, "event_type") and 
                            node.event_type == "start" and 
                            node.event_definition == "timer"):
                            
                            # Generate a unique ID for this timer
                            timer_id = f"{self._timer_prefix}{definition.id}:{node.id}"
                            found_timer_ids.add(timer_id)
                            
                            # Find timer definition in XML
                            timer_def = self._extract_timer_definition(definition.bpmn_xml, node.id)
                            if not timer_def:
                                logger.warning(f"No timer definition found for {node.id} in {definition.id}")
                                continue
                            
                            # Schedule or update the timer
                            await self._schedule_timer(timer_id, definition.id, node.id, timer_def)
                            
                except Exception as e:
                    logger.error(f"Error processing definition {definition.id}: {e}", exc_info=True)
        
        # Remove timers for deleted process definitions
        timers_to_remove = self._scheduled_timer_ids - found_timer_ids
        for timer_id in timers_to_remove:
            await self._remove_timer(timer_id)
        
        logger.info(f"Timer scan complete. Active timers: {len(self._scheduled_timer_ids)}")

    def _extract_timer_definition(self, bpmn_xml: str, node_id: str) -> Optional[str]:
        """
        Extract timer definition from BPMN XML.
        
        Args:
            bpmn_xml: BPMN XML string
            node_id: ID of the timer start event
            
        Returns:
            Timer definition string or None if not found
        """
        import xml.etree.ElementTree as ET
        
        root = ET.fromstring(bpmn_xml)
        ns = {
            "bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL",
            "pythmata": "http://pythmata.org/schema/1.0/bpmn",
        }
        
        # Find the timer start event
        event = root.find(f".//bpmn:startEvent[@id='{node_id}']", ns)
        if event is None:
            return None
        
        # Check for timer event definition
        timer_def = event.find(".//bpmn:timerEventDefinition", ns)
        if timer_def is None:
            return None
        
        # Check for timer definition elements
        time_date = timer_def.find("bpmn:timeDate", ns)
        if time_date is not None and time_date.text:
            return time_date.text.strip()
        
        time_duration = timer_def.find("bpmn:timeDuration", ns)
        if time_duration is not None and time_duration.text:
            return time_duration.text.strip()
        
        time_cycle = timer_def.find("bpmn:timeCycle", ns)
        if time_cycle is not None and time_cycle.text:
            return time_cycle.text.strip()
        
        # Check for extension elements
        ext_elements = event.find("bpmn:extensionElements", ns)
        if ext_elements is not None:
            timer_config = ext_elements.find(".//pythmata:timerEventConfig", ns)
            if timer_config is not None:
                timer_type = timer_config.get("timerType")
                timer_value = timer_config.get("timerValue")
                if timer_type and timer_value:
                    return timer_value
        
        return None

    async def _schedule_timer(self, timer_id: str, definition_id: str, node_id: str, timer_def: str) -> None:
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
            timer_type, trigger = self._parse_timer_definition(timer_def)
            
            if not trigger:
                logger.error(f"Failed to parse timer definition: {timer_def}")
                return
            
            # Store timer metadata in Redis for recovery
            timer_metadata = {
                'definition_id': definition_id,
                'node_id': node_id,
                'timer_def': timer_def,
                'timer_type': timer_type,
                'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
            
            await self.state_manager.redis.set(
                f"{timer_id}:metadata",
                json.dumps(timer_metadata)
            )
            
            # Check if job already exists
            job = self._scheduler.get_job(timer_id)
            if job:
                logger.info(f"Updating existing timer job: {timer_id}")
                job.reschedule(trigger)
            else:
                logger.info(f"Scheduling new timer job: {timer_id} with definition {timer_def}")
                self._scheduler.add_job(
                    self._timer_callback,
                    trigger=trigger,
                    id=timer_id,
                    replace_existing=True,
                    kwargs={
                        'timer_id': timer_id,
                        'definition_id': definition_id,
                        'node_id': node_id,
                        'timer_type': timer_type,
                        'timer_def': timer_def
                    }
                )
            
            # Add to set of scheduled timers
            self._scheduled_timer_ids.add(timer_id)
            
        except Exception as e:
            logger.error(f"Error scheduling timer {timer_id}: {e}", exc_info=True)

    def _parse_timer_definition(self, timer_def: str) -> Tuple[str, Optional[Union[DateTrigger, IntervalTrigger]]]:
        """
        Parse timer definition and create appropriate APScheduler trigger.
        
        Args:
            timer_def: Timer definition string in ISO 8601 format
            
        Returns:
            Tuple of (timer_type, trigger) where trigger is an APScheduler trigger
        """
        import re
        from datetime import datetime, timedelta, timezone
        
        # Try parsing as duration (e.g., PT1H)
        if timer_def.startswith("PT"):
            # Parse ISO 8601 duration
            pattern = r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?"
            match = re.match(pattern, timer_def)
            if not match:
                return "duration", None
            
            hours = int(match.group(1) or 0)
            minutes = int(match.group(2) or 0)
            seconds = int(match.group(3) or 0)
            
            # Calculate total seconds
            total_seconds = hours * 3600 + minutes * 60 + seconds
            
            # Create a date trigger for one-time execution
            run_date = datetime.now(timezone.utc) + timedelta(seconds=total_seconds)
            return "duration", DateTrigger(run_date=run_date)
        
        # Try parsing as cycle (e.g., R3/PT1H)
        if timer_def.startswith("R"):
            # Parse ISO 8601 recurring interval
            match = re.match(r"R(\d*)/PT(.+)$", timer_def)
            if not match:
                return "cycle", None
            
            repetitions = match.group(1)
            interval_str = f"PT{match.group(2)}"
            
            # Parse the interval part
            pattern = r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?"
            interval_match = re.match(pattern, interval_str)
            if not interval_match:
                return "cycle", None
            
            hours = int(interval_match.group(1) or 0)
            minutes = int(interval_match.group(2) or 0)
            seconds = int(interval_match.group(3) or 0)
            
            # Calculate total seconds for interval
            interval_seconds = hours * 3600 + minutes * 60 + seconds
            
            # Create an interval trigger
            return "cycle", IntervalTrigger(
                seconds=interval_seconds,
                start_date=datetime.now(timezone.utc)
            )
        
        # Try parsing as date
        try:
            run_date = datetime.fromisoformat(timer_def)
            return "date", DateTrigger(run_date=run_date)
        except ValueError:
            pass
        
        return "unknown", None

    async def _remove_timer(self, timer_id: str) -> None:
        """
        Remove a scheduled timer.
        
        Args:
            timer_id: ID of the timer to remove
        """
        try:
            # Remove from APScheduler
            self._scheduler.remove_job(timer_id)
            
            # Remove from Redis
            await self.state_manager.redis.delete(f"{timer_id}:metadata")
            
            # Remove from set of scheduled timers
            self._scheduled_timer_ids.discard(timer_id)
            
            logger.info(f"Removed timer: {timer_id}")
        except Exception as e:
            logger.error(f"Error removing timer {timer_id}: {e}", exc_info=True)

    async def _timer_callback(self, timer_id: str, definition_id: str, node_id: str, 
                             timer_type: str, timer_def: str) -> None:
        """
        Callback function executed when a timer expires.
        
        Args:
            timer_id: ID of the timer
            definition_id: Process definition ID
            node_id: Start event node ID
            timer_type: Type of timer (duration, date, cycle)
            timer_def: Timer definition string
        """
        try:
            logger.info(f"Timer {timer_id} triggered for process {definition_id}")
            
            # Start a new process instance
            await self._start_process_instance(definition_id)
            
            # For non-recurring timers, remove from scheduled timers
            if timer_type != "cycle":
                self._scheduled_timer_ids.discard(timer_id)
            
        except Exception as e:
            logger.error(f"Error in timer callback for {timer_id}: {e}", exc_info=True)

    async def _start_process_instance(self, definition_id: str) -> None:
        """
        Start a new process instance for the given definition.
        
        Args:
            definition_id: Process definition ID
        """
        try:
            # Generate a unique instance ID
            instance_id = str(uuid.uuid4())
            
            # Publish process.started event
            await self.event_bus.publish(
                "process.started",
                {
                    "instance_id": instance_id,
                    "definition_id": definition_id,
                    "variables": {},
                    "source": "timer_scheduler",
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
                }
            )
            
            logger.info(f"Started process instance {instance_id} from definition {definition_id}")
            
        except Exception as e:
            logger.error(f"Error starting process instance: {e}", exc_info=True)
    
    async def recover_from_crash(self) -> None:
        """
        Recover timer state after a system crash or restart.
        
        This method:
        1. Checks Redis for timer metadata
        2. Reschedules timers based on stored metadata
        """
        try:
            logger.info("Recovering timer state from Redis")
            
            # Find all timer metadata keys
            pattern = f"{self._timer_prefix}*:metadata"
            keys = await self.state_manager.redis.keys(pattern)
            
            for key in keys:
                try:
                    # Extract timer ID from key
                    timer_id = key.replace(":metadata", "")
                    
                    # Get timer metadata
                    metadata_json = await self.state_manager.redis.get(key)
                    if not metadata_json:
                        continue
                    
                    metadata = json.loads(metadata_json)
                    
                    # Reschedule the timer
                    await self._schedule_timer(
                        timer_id,
                        metadata['definition_id'],
                        metadata['node_id'],
                        metadata['timer_def']
                    )
                    
                except Exception as e:
                    logger.error(f"Error recovering timer {key}: {e}", exc_info=True)
            
            logger.info(f"Recovered {len(keys)} timers from Redis")
            
        except Exception as e:
            logger.error(f"Error recovering timer state: {e}", exc_info=True)
