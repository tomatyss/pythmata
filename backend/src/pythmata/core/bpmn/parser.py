"""Parser for BPMN 2.0 XML documents."""

from typing import Dict, List, Union
from xml.etree import ElementTree as ET

from pythmata.core.bpmn.builders import BuilderFactory
from pythmata.core.bpmn.validator import BPMNValidator
from pythmata.core.types import DataObject, Event, EventType, FlowNode, SequenceFlow


class BPMNParser:
    """Parser for BPMN 2.0 XML documents."""

    def __init__(self):
        self.validator = BPMNValidator()
        self.ns = {
            "bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL",
            "pythmata": "http://pythmata.org/schema/1.0/bpmn",
        }

    def parse(self, xml: str) -> Dict[str, Union[List[FlowNode], List[SequenceFlow]]]:
        """
        Parse BPMN XML into internal representation.

        Args:
            xml: BPMN XML string

        Returns:
            Dictionary containing parsed nodes and flows
        """
        # Validate XML first
        validation_result = self.validator.validate(xml)
        if not validation_result.is_valid:
            error_details = ", ".join(str(err) for err in validation_result.errors)
            raise ValueError(f"Invalid BPMN XML: {error_details}")

        # Parse XML
        root = ET.fromstring(xml)
        process = root.find(".//bpmn:process", self.ns)
        if process is None:
            raise ValueError("No process found in BPMN XML")

        # Parse all elements
        nodes = []
        flows = []
        data_objects = []

        # Parse flow nodes
        for elem in process.findall("./bpmn:*", self.ns):
            if elem.tag.endswith("}task") or elem.tag.endswith("}serviceTask"):
                nodes.append(self.parse_element(elem))
            elif elem.tag.endswith("}startEvent"):
                nodes.append(self._parse_event(elem, EventType.START))
            elif elem.tag.endswith("}endEvent"):
                nodes.append(self._parse_event(elem, EventType.END))
            elif elem.tag.endswith("}intermediateThrowEvent") or elem.tag.endswith("}intermediateCatchEvent"):
                nodes.append(self._parse_event(elem, EventType.INTERMEDIATE))
            elif elem.tag.endswith("}boundaryEvent"):
                nodes.append(self._parse_boundary_event(elem))
            elif "Gateway" in elem.tag:
                nodes.append(self.parse_element(elem))
            elif elem.tag.endswith("}subProcess"):
                nodes.append(self.parse_element(elem))
            elif elem.tag.endswith("}sequenceFlow"):
                flows.append(self._parse_sequence_flow(elem))
            elif elem.tag.endswith("}dataObject"):
                data_objects.append(self._parse_data_object(elem))

        return {"nodes": nodes, "flows": flows, "data_objects": data_objects}

    def parse_element(self, element: Union[str, ET.Element]) -> FlowNode:
        """
        Parse a single BPMN element using the builder pattern.

        Args:
            element: XML string or ElementTree.Element

        Returns:
            Parsed BPMN element
        """
        if isinstance(element, str):
            element = ET.fromstring(element)

        builder = BuilderFactory.create_builder(element, self.ns, self)
        return builder.build()

    def _parse_event(self, elem: ET.Element, event_type: EventType) -> Event:
        """Parse a BPMN event element."""
        incoming = [e.text for e in elem.findall("bpmn:incoming", self.ns)]
        outgoing = [e.text for e in elem.findall("bpmn:outgoing", self.ns)]

        # Check for event definitions - look for both *Definition and *EventDefinition patterns
        definitions = elem.findall("./bpmn:*Definition", self.ns)
        if not definitions:
            definitions = elem.findall("./bpmn:*EventDefinition", self.ns)

        event_definition = None
        if definitions:
            tag = definitions[0].tag.split("}")[-1]
            # Convert timerEventDefinition to timer, messageEventDefinition to message, etc.
            if tag.endswith("EventDefinition"):
                event_definition = tag[:-14].lower()  # Remove "EventDefinition" suffix
            else:
                event_definition = tag

        # Parse extended properties for compensation events
        activity_ref = None
        if event_definition == "compensation":
            # Look for activityRef in compensation event definition
            if definitions:
                compensation_def = definitions[0]
                activity_ref = compensation_def.get("activityRef")

        return Event(
            id=elem.get("id"),
            type="event",
            name=elem.get("name"),
            event_type=event_type,
            event_definition=event_definition,
            incoming=incoming,
            outgoing=outgoing,
            activity_ref=activity_ref,  # Add activity_ref for compensation events
        )

    def _parse_boundary_event(self, elem: ET.Element) -> Event:
        """Parse a BPMN boundary event element."""
        incoming = []  # Boundary events don't have incoming flows
        outgoing = [e.text for e in elem.findall("bpmn:outgoing", self.ns)]
        
        attached_to = elem.get("attachedToRef")
        cancelling = elem.get("cancelActivity", "true").lower() == "true"
        
        # Check for event definitions
        definitions = elem.findall("./bpmn:*EventDefinition", self.ns)
        
        event_definition = None
        if definitions:
            tag = definitions[0].tag.split("}")[-1]
            if tag.endswith("EventDefinition"):
                event_definition = tag[:-14].lower()
            else:
                event_definition = tag
                
        # Additional data for compensation boundary events
        activity_ref = None
        wait_for_completion = False
        
        if event_definition == "compensation":
            # Look for activityRef in compensation event definition
            if definitions:
                compensation_def = definitions[0]
                activity_ref = compensation_def.get("activityRef")
                wait_for_completion_str = compensation_def.get("waitForCompletion", "false")
                wait_for_completion = wait_for_completion_str.lower() == "true"
        
        return Event(
            id=elem.get("id"),
            type="boundaryEvent",
            name=elem.get("name"),
            event_type=EventType.BOUNDARY,
            event_definition=event_definition,
            incoming=incoming,
            outgoing=outgoing,
            attached_to=attached_to,
            cancelling=cancelling,
            activity_ref=activity_ref,
            wait_for_completion=wait_for_completion,
        )

    def _parse_sequence_flow(self, elem: ET.Element) -> SequenceFlow:
        """Parse a BPMN sequence flow element."""
        condition = elem.find("bpmn:conditionExpression", self.ns)
        condition_expression = condition.text if condition is not None else None

        return SequenceFlow(
            id=elem.get("id"),
            source_ref=elem.get("sourceRef"),
            target_ref=elem.get("targetRef"),
            condition_expression=condition_expression,
        )

    def _parse_data_object(self, elem: ET.Element) -> DataObject:
        """Parse a BPMN data object element."""
        return DataObject(
            id=elem.get("id"), name=elem.get("name"), type=elem.get("itemSubjectRef")
        )
