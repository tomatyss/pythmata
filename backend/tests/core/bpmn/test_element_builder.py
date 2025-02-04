from typing import Any, Dict

import pytest

from pythmata.core.bpmn.parser import BPMNParser
from pythmata.core.types import FlowNode, Gateway, GatewayType, Task


class TestBPMNElementBuilder:
    """Test suite for BPMN element builder pattern implementation"""

    def test_task_builder_basic_attributes(self):
        """Test building a task with basic attributes"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <bpmn:task xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" 
                   id="Task_1" 
                   name="Test Task">
            <bpmn:incoming>Flow_1</bpmn:incoming>
            <bpmn:outgoing>Flow_2</bpmn:outgoing>
        </bpmn:task>
        """
        parser = BPMNParser()
        task = parser.parse_element(xml)

        assert isinstance(task, Task)
        assert task.id == "Task_1"
        assert task.name == "Test Task"
        assert task.incoming == ["Flow_1"]
        assert task.outgoing == ["Flow_2"]

    def test_task_builder_with_extensions(self):
        """Test building a task with extension elements"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <bpmn:task xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                   xmlns:pythmata="http://pythmata.org/schema/1.0/bpmn"
                   id="Task_1" 
                   name="Test Task">
            <bpmn:extensionElements>
                <pythmata:taskConfig>
                    <pythmata:script>print("test")</pythmata:script>
                    <pythmata:timeout>30</pythmata:timeout>
                </pythmata:taskConfig>
            </bpmn:extensionElements>
        </bpmn:task>
        """
        parser = BPMNParser()
        task = parser.parse_element(xml)

        assert isinstance(task, Task)
        assert task.extensions is not None
        assert task.extensions.get("script") == 'print("test")'
        assert task.extensions.get("timeout") == "30"

    def test_gateway_builder_conditions(self):
        """Test building a gateway with conditions"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <bpmn:exclusiveGateway xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                              id="Gateway_1" 
                              name="Test Gateway">
            <bpmn:incoming>Flow_1</bpmn:incoming>
            <bpmn:outgoing>Flow_2</bpmn:outgoing>
            <bpmn:outgoing>Flow_3</bpmn:outgoing>
        </bpmn:exclusiveGateway>
        """
        parser = BPMNParser()
        gateway = parser.parse_element(xml)

        assert isinstance(gateway, Gateway)
        assert gateway.id == "Gateway_1"
        assert gateway.name == "Test Gateway"
        assert gateway.gateway_type == GatewayType.EXCLUSIVE
        assert len(gateway.outgoing) == 2

    def test_builder_validation(self):
        """Test builder validates required attributes"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <bpmn:task xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                   name="Test Task">
            <bpmn:incoming>Flow_1</bpmn:incoming>
            <bpmn:outgoing>Flow_2</bpmn:outgoing>
        </bpmn:task>
        """
        parser = BPMNParser()

        with pytest.raises(ValueError) as exc:
            parser.parse_element(xml)
        assert "Missing required attribute: id" in str(exc.value)

    def test_builder_immutability(self):
        """Test builder creates immutable elements"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <bpmn:task xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                   id="Task_1" 
                   name="Test Task">
            <bpmn:incoming>Flow_1</bpmn:incoming>
            <bpmn:outgoing>Flow_2</bpmn:outgoing>
        </bpmn:task>
        """
        parser = BPMNParser()
        task = parser.parse_element(xml)

        with pytest.raises(AttributeError):
            task.id = "New_ID"

        with pytest.raises(AttributeError):
            task.name = "New Name"
