"""Timer definition parsing and extraction utilities."""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple, Union

from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from pythmata.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TimerDefinition:
    """Timer definition with parsed information."""

    timer_type: str
    trigger: Union[DateTrigger, IntervalTrigger]
    repetitions: Optional[int] = None
    duration: Optional[timedelta] = None
    target_date: Optional[datetime] = None
    interval: Optional[timedelta] = None


def parse_timer_definition(timer_def: str) -> Optional[TimerDefinition]:
    """
    Parse timer definition and create appropriate APScheduler trigger.

    Args:
        timer_def: Timer definition string in ISO 8601 format

    Returns:
        TimerDefinition object with parsed information or None if parsing fails
    """
    logger.info(f"Parsing timer definition: {timer_def}")

    # Try parsing as duration (e.g., PT1H)
    if timer_def.startswith("PT"):
        duration = _parse_duration(timer_def)
        if not duration:
            logger.error(f"Failed to parse duration: {timer_def}")
            return None

        # Calculate run date
        run_date = datetime.now(timezone.utc) + duration
        logger.info(f"Parsed duration timer: {duration}, will run at {run_date}")

        return TimerDefinition(
            timer_type="duration",
            trigger=DateTrigger(run_date=run_date),
            duration=duration,
        )

    # Try parsing as cycle (e.g., R3/PT1H)
    if timer_def.startswith("R"):
        # Parse ISO 8601 recurring interval
        match = re.match(r"R(\d*)/PT(.+)$", timer_def)
        if not match:
            logger.error(f"Failed to parse cycle: {timer_def}")
            return None

        repetitions = int(match.group(1)) if match.group(1) else None
        interval_str = f"PT{match.group(2)}"

        # Parse the interval part
        interval = _parse_duration(interval_str)
        if not interval:
            logger.error(f"Failed to parse cycle interval: {interval_str}")
            return None

        # Create an interval trigger
        logger.info(f"Parsed cycle timer: {interval}, repetitions: {repetitions}")
        return TimerDefinition(
            timer_type="cycle",
            trigger=IntervalTrigger(
                seconds=interval.total_seconds(), start_date=datetime.now(timezone.utc)
            ),
            repetitions=repetitions,
            interval=interval,
        )

    # Try parsing as date
    try:
        run_date = datetime.fromisoformat(timer_def)
        logger.info(f"Parsed date timer: {run_date}")
        return TimerDefinition(
            timer_type="date",
            trigger=DateTrigger(run_date=run_date),
            target_date=run_date,
        )
    except ValueError:
        logger.error(f"Failed to parse date: {timer_def}")

    logger.error(f"Could not parse timer definition: {timer_def}")
    return None


def _parse_duration(duration_str: str) -> Optional[timedelta]:
    """
    Parse ISO 8601 duration string.

    Args:
        duration_str: Duration string in ISO 8601 format (e.g., PT1H30M)

    Returns:
        timedelta object or None if parsing fails
    """
    if not duration_str.startswith("PT"):
        return None

    pattern = r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?"
    match = re.match(pattern, duration_str)
    if not match:
        return None

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)

    return timedelta(hours=hours, minutes=minutes, seconds=seconds)


def extract_timer_definition(bpmn_xml: str, node_id: str) -> Optional[str]:
    """
    Extract timer definition from BPMN XML.

    Args:
        bpmn_xml: BPMN XML string
        node_id: ID of the timer start event

    Returns:
        Timer definition string or None if not found
    """
    logger.info(f"Extracting timer definition for node {node_id}")
    root = ET.fromstring(bpmn_xml)
    ns = {
        "bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL",
        "pythmata": "http://pythmata.org/schema/1.0/bpmn",
        "xsi": "http://www.w3.org/2001/XMLSchema-instance",
    }
    
    # Try to find the event (either startEvent or intermediateCatchEvent)
    event = root.find(f".//bpmn:startEvent[@id='{node_id}']", ns)
    if event is None:
        event = root.find(f".//bpmn:intermediateCatchEvent[@id='{node_id}']", ns)

    if event is None:
        logger.warning(f"No start or intermediate event found with id {node_id}")
        return None

    # Log event name if available
    event_name = event.get("name")
    if event_name:
        logger.info(f"Found start or intermediate event with name: {event_name}")
    
    # Check for extension elements
    ext_elements = event.find("bpmn:extensionElements", ns)
    if ext_elements is not None:
        timer_config = ext_elements.find(".//pythmata:timerEventConfig", ns)
        if timer_config is not None:
            timer_type = timer_config.get("timerType")
            timer_value = timer_config.get("timerValue")
            if timer_type and timer_value:
                logger.info(
                    f"Found timer in extension elements: type={timer_type}, value={timer_value}"
                )
                return timer_value

    # Check for timer event definition
    timer_def = event.find(".//bpmn:timerEventDefinition", ns)
    if timer_def is None:
        logger.warning(f"No timer event definition found for {node_id}")
        return None

    # Check for timer definition elements
    time_date = timer_def.find("bpmn:timeDate", ns)
    if time_date is not None and time_date.text:
        timer_value = time_date.text.strip()
        logger.info(f"Found timeDate: {timer_value}")
        return timer_value

    time_duration = timer_def.find("bpmn:timeDuration", ns)
    if time_duration is not None and time_duration.text:
        timer_value = time_duration.text.strip()
        logger.info(f"Found timeDuration: {timer_value}")
        return timer_value

    time_cycle = timer_def.find("bpmn:timeCycle", ns)
    if time_cycle is not None and time_cycle.text:
        timer_value = time_cycle.text.strip()
        logger.info(f"Found timeCycle: {timer_value}")
        return timer_value

    logger.warning(f"No timer definition found for {node_id}")
    return None


def find_timer_events_in_definition(
    bpmn_xml: str, timer_prefix: str, definition_id: str
) -> List[Tuple[str, str, str]]:
    """
    Find timer start events in a process definition.

    Args:
        bpmn_xml: BPMN XML string
        timer_prefix: Prefix for timer IDs
        definition_id: Process definition ID

    Returns:
        List of tuples containing (timer_id, node_id, timer_definition)
    """
    import xml.etree.ElementTree as ET

    logger.info(f"Finding timer events in definition {definition_id}")
    timer_events = []

    # First try to extract timer events directly from XML
    root = ET.fromstring(bpmn_xml)
    ns = {
        "bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL",
        "pythmata": "http://pythmata.org/schema/1.0/bpmn",
        "xsi": "http://www.w3.org/2001/XMLSchema-instance",
    }

    # Find all start events with timer definitions
    timer_events_found = False
    events = root.findall(".//bpmn:startEvent", ns) + root.findall(".//bpmn:intermediateCatchEvent", ns)

    for event in events:
        # Check if it has a timer definition
        timer_def_elem = event.find(".//bpmn:timerEventDefinition", ns)
        if timer_def_elem is not None:
            timer_events_found = True
            node_id = event.get("id")
            if event.tag.endswith("}startEvent"):
                event_type = 'start'
            else:
                event_type = 'intermediate'
            logger.info(f"Found timer {event_type} event with id: {node_id}")

            # Generate a unique ID for this timer
            timer_id = f"{timer_prefix}{definition_id}:{node_id}"

            # Find timer definition
            timer_def = extract_timer_definition(bpmn_xml, node_id)
            if not timer_def:
                logger.warning(
                    f"No timer definition found for {node_id} in {definition_id}"
                )
                continue

            logger.info(f"Adding timer event: {timer_id}, {node_id}, {timer_def}")
            timer_events.append((timer_id, node_id, timer_def))

    # If no timer events were found via direct XML parsing, try using the parser
    if not timer_events_found:
        logger.info("No timer events found via direct XML parsing, trying parser")
        try:
            from pythmata.core.bpmn.parser import BPMNParser

            parser = BPMNParser()
            process_graph = parser.parse(bpmn_xml)

            # Find timer start events
            for node in process_graph["nodes"]:
                if (
                    hasattr(node, "event_type")
                    and node.event_type == "start"
                    and node.event_definition == "timer"
                ):
                    logger.info(f"Found timer start event in parser: {node.id}")

                    # Generate a unique ID for this timer
                    timer_id = f"{timer_prefix}{definition_id}:{node.id}"

                    # Find timer definition in XML
                    timer_def = extract_timer_definition(bpmn_xml, node.id)
                    if not timer_def:
                        logger.warning(
                            f"No timer definition found for {node.id} in {definition_id}"
                        )
                        continue

                    logger.info(
                        f"Adding timer event from parser: {timer_id}, {node.id}, {timer_def}"
                    )
                    timer_events.append((timer_id, node.id, timer_def))
        except ValueError as e:
            # If parsing fails due to validation errors, we've already tried direct XML extraction
            logger.debug(f"Parser error for {definition_id}: {e}")

    logger.info(f"Found {len(timer_events)} timer events in definition {definition_id}")
    return timer_events
