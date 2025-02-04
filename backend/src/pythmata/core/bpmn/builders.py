"""BPMN element builder implementations."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from xml.etree import ElementTree as ET

from pythmata.core.types import (
    FlowNode,
    Task,
    Gateway,
    GatewayType,
    SubProcess,
    SequenceFlow,
    Event,
    EventType,
)


class ElementBuilder(ABC):
    """Abstract base class for BPMN element builders."""
    
    def __init__(self, element: ET.Element, ns: Dict[str, str]):
        self.element = element
        self.ns = ns
        self._validate_required_attributes()
    
    @abstractmethod
    def _validate_required_attributes(self) -> None:
        """Validate that all required attributes are present."""
        if not self.element.get("id"):
            raise ValueError("Missing required attribute: id")
    
    def _get_flows(self) -> tuple[List[str], List[str]]:
        """Get incoming and outgoing flows."""
        incoming = [e.text for e in self.element.findall("bpmn:incoming", self.ns)]
        outgoing = [e.text for e in self.element.findall("bpmn:outgoing", self.ns)]
        return incoming, outgoing


class TaskBuilder(ElementBuilder):
    """Builder for BPMN task elements."""
    
    def _validate_required_attributes(self) -> None:
        """Validate task-specific required attributes."""
        super()._validate_required_attributes()
    
    def _parse_extensions(self) -> Dict[str, Any]:
        """Parse task extension elements."""
        extensions = {}
        script = None
        input_vars = {}
        output_vars = {}
        
        ext_elem = self.element.find("bpmn:extensionElements", self.ns)
        if ext_elem is not None:
            config = ext_elem.find(".//pythmata:taskConfig", self.ns)
            if config is not None:
                script_elem = config.find(".//pythmata:script", self.ns)
                if script_elem is not None:
                    script = script_elem.text.strip()
                    extensions["script"] = script
                
                timeout_elem = config.find(".//pythmata:timeout", self.ns)
                if timeout_elem is not None:
                    extensions["timeout"] = timeout_elem.text
                
                # Parse input variables
                for var in config.findall(
                    ".//pythmata:inputVariables/pythmata:variable", self.ns
                ):
                    input_vars[var.get("name")] = var.get("type")
                
                # Parse output variables
                for var in config.findall(
                    ".//pythmata:outputVariables/pythmata:variable", self.ns
                ):
                    output_vars[var.get("name")] = var.get("type")
        
        return extensions, script, input_vars, output_vars
    
    def build(self) -> Task:
        """Build and return an immutable Task instance."""
        incoming, outgoing = self._get_flows()
        extensions, script, input_vars, output_vars = self._parse_extensions()
        
        return Task(
            id=self.element.get("id"),
            type=self.element.tag.split("}")[-1],
            name=self.element.get("name"),
            incoming=incoming,
            outgoing=outgoing,
            extensions=extensions,
            script=script,
            input_variables=input_vars,
            output_variables=output_vars,
        )


class GatewayBuilder(ElementBuilder):
    """Builder for BPMN gateway elements."""
    
    def _validate_required_attributes(self) -> None:
        """Validate gateway-specific required attributes."""
        super()._validate_required_attributes()
    
    def _determine_gateway_type(self) -> GatewayType:
        """Determine the gateway type from the element tag."""
        tag = self.element.tag.split("}")[-1].lower()
        if "exclusive" in tag:
            return GatewayType.EXCLUSIVE
        elif "parallel" in tag:
            return GatewayType.PARALLEL
        elif "inclusive" in tag:
            return GatewayType.INCLUSIVE
        else:
            raise ValueError(f"Unknown gateway type: {tag}")
    
    def build(self) -> Gateway:
        """Build and return an immutable Gateway instance."""
        incoming, outgoing = self._get_flows()
        
        return Gateway(
            id=self.element.get("id"),
            type="gateway",
            name=self.element.get("name"),
            incoming=incoming,
            outgoing=outgoing,
            gateway_type=self._determine_gateway_type()
        )


class SubProcessBuilder(ElementBuilder):
    """Builder for BPMN subprocess elements."""
    
    def __init__(self, element: ET.Element, ns: Dict[str, str], parser):
        """Initialize with reference to parser for recursive parsing."""
        super().__init__(element, ns)
        self.parser = parser
    
    def _validate_required_attributes(self) -> None:
        """Validate subprocess-specific required attributes."""
        super()._validate_required_attributes()
    
    def _parse_multi_instance(self) -> Dict[str, str]:
        """Parse multi-instance characteristics."""
        multi_instance = {}
        mi_elem = self.element.find("bpmn:multiInstanceLoopCharacteristics", self.ns)
        if mi_elem is not None:
            cardinality = mi_elem.find("bpmn:loopCardinality", self.ns)
            if cardinality is not None:
                multi_instance["cardinality"] = cardinality.text
        return multi_instance
    
    def _parse_subprocess_contents(self) -> tuple[List[FlowNode], List[SequenceFlow]]:
        """Parse subprocess internal elements."""
        nodes = []
        flows = []
        
        for child in self.element:
            if child.tag.endswith("}task"):
                nodes.append(self.parser.parse_element(child))
            elif child.tag.endswith("}startEvent"):
                nodes.append(self.parser._parse_event(child, EventType.START))
            elif child.tag.endswith("}endEvent"):
                nodes.append(self.parser._parse_event(child, EventType.END))
            elif child.tag.endswith("}sequenceFlow"):
                flows.append(self.parser._parse_sequence_flow(child))
        
        return nodes, flows
    
    def build(self) -> SubProcess:
        """Build and return an immutable SubProcess instance."""
        incoming, outgoing = self._get_flows()
        nodes, flows = self._parse_subprocess_contents()
        multi_instance = self._parse_multi_instance()
        
        return SubProcess(
            id=self.element.get("id"),
            type="subprocess",
            name=self.element.get("name"),
            incoming=incoming,
            outgoing=outgoing,
            nodes=nodes,
            flows=flows,
            multi_instance=multi_instance,
        )


class BuilderFactory:
    """Factory for creating appropriate element builders."""
    
    @staticmethod
    def create_builder(element: ET.Element, ns: Dict[str, str], parser=None) -> ElementBuilder:
        """Create appropriate builder based on element type."""
        tag = element.tag.split("}")[-1].lower()
        
        if "task" in tag:
            return TaskBuilder(element, ns)
        elif "gateway" in tag:
            return GatewayBuilder(element, ns)
        elif "subprocess" in tag:
            if parser is None:
                raise ValueError("Parser instance required for subprocess parsing")
            return SubProcessBuilder(element, ns, parser)
        else:
            raise ValueError(f"Unsupported element type: {tag}")
