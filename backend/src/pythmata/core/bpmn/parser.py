from dataclasses import dataclass
from typing import Dict, List, Optional, Union
from xml.etree import ElementTree as ET

from pythmata.core.bpmn.validator import BPMNValidator


@dataclass
class FlowNode:
    """Base class for BPMN flow nodes."""
    id: str
    type: str
    incoming: List[str]
    outgoing: List[str]


@dataclass
class Task(FlowNode):
    """Represents a BPMN task."""
    name: Optional[str] = None
    script: Optional[str] = None
    input_variables: Optional[Dict[str, str]] = None
    output_variables: Optional[Dict[str, str]] = None


@dataclass
class Gateway(FlowNode):
    """Represents a BPMN gateway."""
    gateway_type: str  # exclusive, parallel, inclusive
    default_flow: Optional[str] = None


@dataclass
class Event(FlowNode):
    """Represents a BPMN event."""
    event_type: str  # start, end, intermediate
    event_definition: Optional[str] = None  # message, timer, etc.


@dataclass
class SubProcess(FlowNode):
    """Represents a BPMN subprocess."""
    nodes: List[FlowNode]
    flows: List['SequenceFlow']
    multi_instance: Optional[Dict[str, str]] = None


@dataclass
class SequenceFlow:
    """Represents a BPMN sequence flow."""
    id: str
    source_ref: str
    target_ref: str
    condition_expression: Optional[str] = None


@dataclass
class DataObject:
    """Represents a BPMN data object."""
    id: str
    name: Optional[str] = None
    type: Optional[str] = None


class BPMNParser:
    """Parser for BPMN 2.0 XML documents."""

    def __init__(self):
        self.validator = BPMNValidator()
        self.ns = {
            'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
            'pythmata': 'http://pythmata.org/schema/1.0/bpmn'
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
            raise ValueError(f"Invalid BPMN XML: {validation_result.errors}")

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
                nodes.append(self._parse_task(elem))
            elif elem.tag.endswith("}startEvent"):
                nodes.append(self._parse_event(elem, "start"))
            elif elem.tag.endswith("}endEvent"):
                nodes.append(self._parse_event(elem, "end"))
            elif "Gateway" in elem.tag:
                nodes.append(self._parse_gateway(elem))
            elif elem.tag.endswith("}subProcess"):
                nodes.append(self._parse_subprocess(elem))
            elif elem.tag.endswith("}sequenceFlow"):
                flows.append(self._parse_sequence_flow(elem))
            elif elem.tag.endswith("}dataObject"):
                data_objects.append(self._parse_data_object(elem))

        return {
            "nodes": nodes,
            "flows": flows,
            "data_objects": data_objects
        }

    def _parse_task(self, elem: ET.Element) -> Task:
        """Parse a BPMN task element."""
        task_id = elem.get("id")
        task_type = elem.tag.split("}")[-1]
        incoming = [e.text for e in elem.findall("bpmn:incoming", self.ns)]
        outgoing = [e.text for e in elem.findall("bpmn:outgoing", self.ns)]
        name = elem.get("name")

        # Parse extensions if present
        script = None
        input_vars = None
        output_vars = None

        extensions = elem.find("bpmn:extensionElements", self.ns)
        if extensions is not None:
            config = extensions.find(".//pythmata:taskConfig", self.ns)
            if config is not None:
                script_elem = config.find(".//pythmata:script", self.ns)
                if script_elem is not None:
                    script = script_elem.text.strip()

                input_vars = {}
                for var in config.findall(".//pythmata:inputVariables/pythmata:variable", self.ns):
                    input_vars[var.get("name")] = var.get("type")

                output_vars = {}
                for var in config.findall(".//pythmata:outputVariables/pythmata:variable", self.ns):
                    output_vars[var.get("name")] = var.get("type")

        return Task(
            id=task_id,
            type=task_type,
            incoming=incoming,
            outgoing=outgoing,
            name=name,
            script=script,
            input_variables=input_vars,
            output_variables=output_vars
        )

    def _parse_gateway(self, elem: ET.Element) -> Gateway:
        """Parse a BPMN gateway element."""
        gateway_id = elem.get("id")
        gateway_type = elem.tag.split("}")[-1].replace("Gateway", "").lower()
        incoming = [e.text for e in elem.findall("bpmn:incoming", self.ns)]
        outgoing = [e.text for e in elem.findall("bpmn:outgoing", self.ns)]
        default_flow = elem.get("default")

        return Gateway(
            id=gateway_id,
            type="gateway",
            gateway_type=gateway_type,
            incoming=incoming,
            outgoing=outgoing,
            default_flow=default_flow
        )

    def _parse_event(self, elem: ET.Element, event_type: str) -> Event:
        """Parse a BPMN event element."""
        event_id = elem.get("id")
        incoming = [e.text for e in elem.findall("bpmn:incoming", self.ns)]
        outgoing = [e.text for e in elem.findall("bpmn:outgoing", self.ns)]

        # Check for event definitions
        definitions = elem.findall("./bpmn:*Definition", self.ns)
        event_definition = definitions[0].tag.split("}")[-1] if definitions else None

        return Event(
            id=event_id,
            type="event",
            event_type=event_type,
            event_definition=event_definition,
            incoming=incoming,
            outgoing=outgoing
        )

    def _parse_subprocess(self, elem: ET.Element) -> SubProcess:
        """Parse a BPMN subprocess element."""
        subprocess_id = elem.get("id")
        incoming = [e.text for e in elem.findall("bpmn:incoming", self.ns)]
        outgoing = [e.text for e in elem.findall("bpmn:outgoing", self.ns)]

        # Parse multi-instance characteristics if present
        multi_instance = None
        mi_elem = elem.find("bpmn:multiInstanceLoopCharacteristics", self.ns)
        if mi_elem is not None:
            multi_instance = {}
            cardinality = mi_elem.find("bpmn:loopCardinality", self.ns)
            if cardinality is not None:
                multi_instance["cardinality"] = cardinality.text

        # Recursively parse subprocess contents
        nodes = []
        flows = []
        
        for child in elem:
            if child.tag.endswith("}task"):
                nodes.append(self._parse_task(child))
            elif child.tag.endswith("}startEvent"):
                nodes.append(self._parse_event(child, "start"))
            elif child.tag.endswith("}endEvent"):
                nodes.append(self._parse_event(child, "end"))
            elif child.tag.endswith("}sequenceFlow"):
                flows.append(self._parse_sequence_flow(child))

        return SubProcess(
            id=subprocess_id,
            type="subprocess",
            incoming=incoming,
            outgoing=outgoing,
            nodes=nodes,
            flows=flows,
            multi_instance=multi_instance
        )

    def _parse_sequence_flow(self, elem: ET.Element) -> SequenceFlow:
        """Parse a BPMN sequence flow element."""
        flow_id = elem.get("id")
        source_ref = elem.get("sourceRef")
        target_ref = elem.get("targetRef")

        # Parse condition expression if present
        condition = elem.find("bpmn:conditionExpression", self.ns)
        condition_expression = condition.text if condition is not None else None

        return SequenceFlow(
            id=flow_id,
            source_ref=source_ref,
            target_ref=target_ref,
            condition_expression=condition_expression
        )

    def _parse_data_object(self, elem: ET.Element) -> DataObject:
        """Parse a BPMN data object element."""
        data_id = elem.get("id")
        name = elem.get("name")
        data_type = elem.get("itemSubjectRef")

        return DataObject(
            id=data_id,
            name=name,
            type=data_type
        )
