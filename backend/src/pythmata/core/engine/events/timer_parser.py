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
    # Try parsing as duration (e.g., PT1H)
    if timer_def.startswith("PT"):
        duration = _parse_duration(timer_def)
        if not duration:
            return None
            
        # Calculate run date
        run_date = datetime.now(timezone.utc) + duration
        
        return TimerDefinition(
            timer_type="duration",
            trigger=DateTrigger(run_date=run_date),
            duration=duration
        )

    # Try parsing as cycle (e.g., R3/PT1H)
    if timer_def.startswith("R"):
        # Parse ISO 8601 recurring interval
        match = re.match(r"R(\d*)/PT(.+)$", timer_def)
        if not match:
            return None

        repetitions = int(match.group(1)) if match.group(1) else None
        interval_str = f"PT{match.group(2)}"

        # Parse the interval part
        interval = _parse_duration(interval_str)
        if not interval:
            return None

        # Create an interval trigger
        return TimerDefinition(
            timer_type="cycle",
            trigger=IntervalTrigger(
                seconds=interval.total_seconds(),
                start_date=datetime.now(timezone.utc)
            ),
            repetitions=repetitions,
            interval=interval
        )

    # Try parsing as date
    try:
        run_date = datetime.fromisoformat(timer_def)
        return TimerDefinition(
            timer_type="date",
            trigger=DateTrigger(run_date=run_date),
            target_date=run_date
        )
    except ValueError:
        pass

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
    
    timer_events = []
    
    # First try to extract timer events directly from XML
    root = ET.fromstring(bpmn_xml)
    ns = {
        "bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL",
        "pythmata": "http://pythmata.org/schema/1.0/bpmn",
        "xsi": "http://www.w3.org/2001/XMLSchema-instance"
    }

    # Find all start events with timer definitions
    timer_events_found = False
    for start_event in root.findall(".//bpmn:startEvent", ns):
        # Check if it has a timer definition
        timer_def_elem = start_event.find(".//bpmn:timerEventDefinition", ns)
        if timer_def_elem is not None:
            timer_events_found = True
            node_id = start_event.get("id")

            # Generate a unique ID for this timer
            timer_id = f"{timer_prefix}{definition_id}:{node_id}"

            # Find timer definition
            timer_def = extract_timer_definition(bpmn_xml, node_id)
            if not timer_def:
                logger.warning(f"No timer definition found for {node_id} in {definition_id}")
                continue

            timer_events.append((timer_id, node_id, timer_def))

    # If no timer events were found via direct XML parsing, try using the parser
    if not timer_events_found:
        try:
            from pythmata.core.bpmn.parser import BPMNParser
            parser = BPMNParser()
            process_graph = parser.parse(bpmn_xml)

            # Find timer start events
            for node in process_graph["nodes"]:
                if (hasattr(node, "event_type") and
                    node.event_type == "start" and
                    node.event_definition == "timer"):

                    # Generate a unique ID for this timer
                    timer_id = f"{timer_prefix}{definition_id}:{node.id}"

                    # Find timer definition in XML
                    timer_def = extract_timer_definition(bpmn_xml, node.id)
                    if not timer_def:
                        logger.warning(f"No timer definition found for {node.id} in {definition_id}")
                        continue

                    timer_events.append((timer_id, node.id, timer_def))
        except ValueError as e:
            # If parsing fails due to validation errors, we've already tried direct XML extraction
            logger.debug(f"Parser error for {definition_id}: {e}")
            
    return timer_events
