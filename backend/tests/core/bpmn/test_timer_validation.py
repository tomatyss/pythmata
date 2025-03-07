"""Tests for BPMN timer event validation."""

import pytest

from pythmata.core.bpmn.validator import BPMNValidator


@pytest.fixture
def validator():
    """Create a BPMN validator instance."""
    return BPMNValidator()


@pytest.fixture
def timer_start_event_xml():
    """XML with a timer start event using tFormalExpression."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" 
                 xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" 
                 xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" 
                 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
                 xmlns:di="http://www.omg.org/spec/DD/20100524/DI" 
                 xmlns:pythmata="http://pythmata.org/schema/1.0/bpmn" 
                 id="Definitions_1" 
                 targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="Process_1" isExecutable="true">
    <bpmn:task id="Activity_05e1eri">
      <bpmn:incoming>Flow_1q1av4g</bpmn:incoming>
      <bpmn:outgoing>Flow_0ty55fc</bpmn:outgoing>
    </bpmn:task>
    <bpmn:sequenceFlow id="Flow_1q1av4g" sourceRef="StartEvent_1" targetRef="Activity_05e1eri" />
    <bpmn:endEvent id="Event_0dau7ja">
      <bpmn:incoming>Flow_0ty55fc</bpmn:incoming>
    </bpmn:endEvent>
    <bpmn:sequenceFlow id="Flow_0ty55fc" sourceRef="Activity_05e1eri" targetRef="Event_0dau7ja" />
    <bpmn:startEvent id="StartEvent_1" name="5 min">
      <bpmn:extensionElements>
        <pythmata:timerEventConfig timerType="duration" timerValue="PT5M" />
      </bpmn:extensionElements>
      <bpmn:outgoing>Flow_1q1av4g</bpmn:outgoing>
      <bpmn:timerEventDefinition id="TimerEventDefinition_09xb6xg">
        <bpmn:timeDuration xsi:type="bpmn:tFormalExpression">PT5M</bpmn:timeDuration>
      </bpmn:timerEventDefinition>
    </bpmn:startEvent>
  </bpmn:process>
  <bpmndi:BPMNDiagram id="BPMNDiagram_1">
    <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Process_1">
      <bpmndi:BPMNShape id="Activity_05e1eri_di" bpmnElement="Activity_05e1eri">
        <dc:Bounds x="250" y="59" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Event_0dau7ja_di" bpmnElement="Event_0dau7ja">
        <dc:Bounds x="412" y="81" width="36" height="36" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Event_08240fh_di" bpmnElement="StartEvent_1">
        <dc:Bounds x="156" y="81" width="36" height="36" />
        <bpmndi:BPMNLabel>
          <dc:Bounds x="161" y="124" width="27" height="14" />
        </bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNEdge id="Flow_1q1av4g_di" bpmnElement="Flow_1q1av4g">
        <di:waypoint x="192" y="99" />
        <di:waypoint x="250" y="99" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_0ty55fc_di" bpmnElement="Flow_0ty55fc">
        <di:waypoint x="350" y="99" />
        <di:waypoint x="412" y="99" />
      </bpmndi:BPMNEdge>
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</bpmn:definitions>"""


def test_timer_start_event_validation(validator, timer_start_event_xml):
    """Test that a timer start event with tFormalExpression is validated correctly."""
    result = validator.validate(timer_start_event_xml)
    assert result.is_valid, f"Validation failed with errors: {result.errors}"


def test_timer_event_extraction():
    """Test that timer event definitions can be extracted from BPMN XML."""
    from pythmata.core.engine.events.timer_parser import extract_timer_definition

    # Test XML with a timer start event
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" 
                 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                 xmlns:pythmata="http://pythmata.org/schema/1.0/bpmn"
                 id="Definitions_1" 
                 targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="Process_1" isExecutable="true">
    <bpmn:startEvent id="StartEvent_1">
      <bpmn:timerEventDefinition id="TimerEventDefinition_1">
        <bpmn:timeDuration xsi:type="bpmn:tFormalExpression">PT5M</bpmn:timeDuration>
      </bpmn:timerEventDefinition>
    </bpmn:startEvent>
  </bpmn:process>
</bpmn:definitions>"""

    # Extract timer definition using the standalone function
    timer_def = extract_timer_definition(xml, "StartEvent_1")
    assert timer_def == "PT5M", f"Expected PT5M, got {timer_def}"
