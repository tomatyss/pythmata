import pytest

from pythmata.core.bpmn import BPMNValidator, ValidationResult


@pytest.mark.unit
class TestBPMNValidator:
    def test_validate_basic_process(self):
        """
        Test validation of a basic BPMN process with start event, task, and end event.
        """
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <bpmn:definitions 
            xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
            xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
            xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
            xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
            targetNamespace="http://example.org/bpmn">
            <bpmn:process id="Process_1">
                <bpmn:startEvent id="Start_1"/>
                <bpmn:task id="Task_1"/>
                <bpmn:endEvent id="End_1"/>
                <bpmn:sequenceFlow id="Flow_1" sourceRef="Start_1" targetRef="Task_1"/>
                <bpmn:sequenceFlow id="Flow_2" sourceRef="Task_1" targetRef="End_1"/>
            </bpmn:process>
        </bpmn:definitions>
        """
        validator = BPMNValidator()
        result = validator.validate(xml)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_invalid_structure(self):
        """
        Test validation of a BPMN process with invalid structure (missing sequence flow).
        """
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <bpmn:definitions 
            xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
            xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
            xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
            xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
            targetNamespace="http://example.org/bpmn">
            <bpmn:process id="Process_1">
                <bpmn:startEvent id="Start_1"/>
                <bpmn:task id="Task_1"/>
                <!-- Missing sequence flow -->
            </bpmn:process>
        </bpmn:definitions>
        """
        validator = BPMNValidator()
        result = validator.validate(xml)

        assert not result.is_valid
        assert len(result.errors) > 0
        assert any("sequence flow" in str(error).lower() for error in result.errors)

    def test_validate_duplicate_ids(self):
        """
        Test validation of a BPMN process with duplicate IDs.
        """
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <bpmn:definitions 
            xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
            xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
            xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
            xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
            targetNamespace="http://example.org/bpmn">
            <bpmn:process id="Process_1">
                <bpmn:startEvent id="Event_1"/>
                <bpmn:task id="Event_1"/>  <!-- Duplicate ID -->
                <bpmn:sequenceFlow id="Flow_1" sourceRef="Event_1" targetRef="Event_1"/>
            </bpmn:process>
        </bpmn:definitions>
        """
        validator = BPMNValidator()
        result = validator.validate(xml)

        assert not result.is_valid
        assert len(result.errors) > 0
        assert any("duplicate" in str(error).lower() for error in result.errors)

    def test_validate_empty_xml(self):
        """
        Test validation of empty XML content.
        """
        validator = BPMNValidator()
        result = validator.validate("")

        assert not result.is_valid
        assert len(result.errors) == 1
        assert result.errors[0].code == "EMPTY_XML"

    def test_validate_malformed_xml(self):
        """
        Test validation of malformed XML content.
        """
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <bpmn:definitions 
            xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
            xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
            xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
            xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
            targetNamespace="http://example.org/bpmn">
            <unclosed_tag>
        """
        validator = BPMNValidator()
        result = validator.validate(xml)

        assert not result.is_valid
        assert len(result.errors) > 0
        assert any("xml" in str(error).lower() for error in result.errors)

    def test_validate_missing_required_attributes(self):
        """
        Test validation of BPMN elements with missing required attributes.
        """
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <bpmn:definitions 
            xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
            xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
            xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
            xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
            targetNamespace="http://example.org/bpmn">
            <bpmn:process>  <!-- Missing required id attribute -->
                <bpmn:startEvent id="Start_1"/>
            </bpmn:process>
        </bpmn:definitions>
        """
        validator = BPMNValidator()
        result = validator.validate(xml)

        assert not result.is_valid
        assert len(result.errors) > 0
        assert any("required" in str(error).lower() for error in result.errors)
