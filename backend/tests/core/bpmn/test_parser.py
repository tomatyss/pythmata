from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from pythmata.core.bpmn.parser import BPMNParser
from pythmata.core.bpmn.validator import BPMNValidator
from pythmata.core.types import (
    DataObject,
    Event,
    Gateway,
    SequenceFlow,
    SubProcess,
    Task,
)

# Sample BPMN XML for testing basic flow elements
BASIC_PROCESS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
                  xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
                  xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
                  id="Definitions_1"
                  targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="Process_1" isExecutable="true">
    <bpmn:startEvent id="StartEvent_1">
      <bpmn:outgoing>Flow_1</bpmn:outgoing>
    </bpmn:startEvent>
    <bpmn:task id="Task_1">
      <bpmn:incoming>Flow_1</bpmn:incoming>
      <bpmn:outgoing>Flow_2</bpmn:outgoing>
    </bpmn:task>
    <bpmn:endEvent id="EndEvent_1">
      <bpmn:incoming>Flow_2</bpmn:incoming>
    </bpmn:endEvent>
    <bpmn:sequenceFlow id="Flow_1" sourceRef="StartEvent_1" targetRef="Task_1" />
    <bpmn:sequenceFlow id="Flow_2" sourceRef="Task_1" targetRef="EndEvent_1" />
  </bpmn:process>
</bpmn:definitions>"""

# Sample BPMN XML for testing gateways
GATEWAY_PROCESS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
                  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                  id="Definitions_2"
                  targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="Process_2" isExecutable="true">
    <bpmn:startEvent id="StartEvent_1">
      <bpmn:outgoing>Flow_1</bpmn:outgoing>
    </bpmn:startEvent>
    <bpmn:exclusiveGateway id="Gateway_1">
      <bpmn:incoming>Flow_1</bpmn:incoming>
      <bpmn:outgoing>Flow_2</bpmn:outgoing>
      <bpmn:outgoing>Flow_3</bpmn:outgoing>
    </bpmn:exclusiveGateway>
    <bpmn:task id="Task_1">
      <bpmn:incoming>Flow_2</bpmn:incoming>
      <bpmn:outgoing>Flow_4</bpmn:outgoing>
    </bpmn:task>
    <bpmn:task id="Task_2">
      <bpmn:incoming>Flow_3</bpmn:incoming>
      <bpmn:outgoing>Flow_5</bpmn:outgoing>
    </bpmn:task>
    <bpmn:endEvent id="EndEvent_1">
      <bpmn:incoming>Flow_4</bpmn:incoming>
      <bpmn:incoming>Flow_5</bpmn:incoming>
    </bpmn:endEvent>
    <bpmn:sequenceFlow id="Flow_1" sourceRef="StartEvent_1" targetRef="Gateway_1" />
    <bpmn:sequenceFlow id="Flow_2" sourceRef="Gateway_1" targetRef="Task_1">
      <bpmn:conditionExpression>amount &gt; 1000</bpmn:conditionExpression>
    </bpmn:sequenceFlow>
    <bpmn:sequenceFlow id="Flow_3" sourceRef="Gateway_1" targetRef="Task_2">
      <bpmn:conditionExpression>amount &lt;= 1000</bpmn:conditionExpression>
    </bpmn:sequenceFlow>
    <bpmn:sequenceFlow id="Flow_4" sourceRef="Task_1" targetRef="EndEvent_1" />
    <bpmn:sequenceFlow id="Flow_5" sourceRef="Task_2" targetRef="EndEvent_1" />
  </bpmn:process>
</bpmn:definitions>"""

# Sample BPMN XML for testing advanced elements
ADVANCED_PROCESS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
                  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                  id="Definitions_3"
                  targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="Process_3" isExecutable="true">
    <bpmn:startEvent id="StartEvent_1">
      <bpmn:outgoing>Flow_1</bpmn:outgoing>
    </bpmn:startEvent>
    <bpmn:subProcess id="SubProcess_1">
      <bpmn:incoming>Flow_1</bpmn:incoming>
      <bpmn:outgoing>Flow_4</bpmn:outgoing>
      <bpmn:multiInstanceLoopCharacteristics>
        <bpmn:loopCardinality>3</bpmn:loopCardinality>
      </bpmn:multiInstanceLoopCharacteristics>
      <bpmn:startEvent id="SubStart_1">
        <bpmn:outgoing>SubFlow_1</bpmn:outgoing>
      </bpmn:startEvent>
      <bpmn:task id="SubTask_1">
        <bpmn:incoming>SubFlow_1</bpmn:incoming>
        <bpmn:outgoing>SubFlow_2</bpmn:outgoing>
      </bpmn:task>
      <bpmn:endEvent id="SubEnd_1">
        <bpmn:incoming>SubFlow_2</bpmn:incoming>
      </bpmn:endEvent>
      <bpmn:sequenceFlow id="SubFlow_1" sourceRef="SubStart_1" targetRef="SubTask_1" />
      <bpmn:sequenceFlow id="SubFlow_2" sourceRef="SubTask_1" targetRef="SubEnd_1" />
    </bpmn:subProcess>
    <bpmn:dataObjectReference id="DataObject_1" dataObjectRef="Data_1" />
    <bpmn:dataObject id="Data_1" />
    <bpmn:endEvent id="EndEvent_1">
      <bpmn:incoming>Flow_4</bpmn:incoming>
    </bpmn:endEvent>
    <bpmn:sequenceFlow id="Flow_1" sourceRef="StartEvent_1" targetRef="SubProcess_1" />
    <bpmn:sequenceFlow id="Flow_4" sourceRef="SubProcess_1" targetRef="EndEvent_1" />
  </bpmn:process>
</bpmn:definitions>"""

# Sample BPMN XML for testing custom extensions
EXTENSION_PROCESS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  xmlns:pythmata="http://pythmata.org/schema/1.0/bpmn"
                  xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
                  id="Definitions_4"
                  targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="Process_4" isExecutable="true">
    <bpmn:startEvent id="StartEvent_1">
      <bpmn:outgoing>Flow_1</bpmn:outgoing>
    </bpmn:startEvent>
    <bpmn:serviceTask id="Task_1">
      <bpmn:incoming>Flow_1</bpmn:incoming>
      <bpmn:outgoing>Flow_2</bpmn:outgoing>
      <bpmn:extensionElements>
        <pythmata:taskConfig>
          <pythmata:script>
            print("Hello from Python!")
            result = x + y
          </pythmata:script>
          <pythmata:inputVariables>
            <pythmata:variable name="x" type="integer" />
            <pythmata:variable name="y" type="integer" />
          </pythmata:inputVariables>
          <pythmata:outputVariables>
            <pythmata:variable name="result" type="integer" />
          </pythmata:outputVariables>
        </pythmata:taskConfig>
      </bpmn:extensionElements>
    </bpmn:serviceTask>
    <bpmn:endEvent id="EndEvent_1">
      <bpmn:incoming>Flow_2</bpmn:incoming>
    </bpmn:endEvent>
    <bpmn:sequenceFlow id="Flow_1" sourceRef="StartEvent_1" targetRef="Task_1" />
    <bpmn:sequenceFlow id="Flow_2" sourceRef="Task_1" targetRef="EndEvent_1" />
  </bpmn:process>
</bpmn:definitions>"""

# Sample BPMN XML for testing service task config
SERVICE_TASK_PROCESS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  xmlns:pythmata="http://pythmata.org/schema/1.0/bpmn"
                  xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
                  id="Definitions_5"
                  targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="Process_5" isExecutable="true">
    <bpmn:startEvent id="StartEvent_1">
      <bpmn:outgoing>Flow_1</bpmn:outgoing>
    </bpmn:startEvent>
    <bpmn:serviceTask id="Task_1">
      <bpmn:incoming>Flow_1</bpmn:incoming>
      <bpmn:outgoing>Flow_2</bpmn:outgoing>
      <bpmn:extensionElements>
        <pythmata:serviceTaskConfig taskName="logger">
          <pythmata:properties>
            <pythmata:property name="level" value="info" />
            <pythmata:property name="message" value="Test message" />
            <pythmata:property name="include_variables" value="true" />
            <pythmata:property name="variable_filter" value="var1,var2" />
          </pythmata:properties>
        </pythmata:serviceTaskConfig>
      </bpmn:extensionElements>
    </bpmn:serviceTask>
    <bpmn:endEvent id="EndEvent_1">
      <bpmn:incoming>Flow_2</bpmn:incoming>
    </bpmn:endEvent>
    <bpmn:sequenceFlow id="Flow_1" sourceRef="StartEvent_1" targetRef="Task_1" />
    <bpmn:sequenceFlow id="Flow_2" sourceRef="Task_1" targetRef="EndEvent_1" />
  </bpmn:process>
</bpmn:definitions>"""


@pytest.mark.asyncio
class TestBPMNParser:
    @pytest.fixture
    def parser(self):
        return BPMNParser()

    async def test_parse_basic_flow_elements(self, parser):
        """Test parsing of basic BPMN flow elements (start event, task, end event)."""
        # Parse basic process XML
        result = parser.parse(BASIC_PROCESS_XML)

        # Verify nodes were parsed correctly
        nodes = result["nodes"]
        flows = result["flows"]

        # Test start event
        start_event = next(
            n for n in nodes if isinstance(n, Event) and n.event_type == "start"
        )
        assert start_event.id == "StartEvent_1"
        assert len(start_event.outgoing) == 1
        assert len(start_event.incoming) == 0

        # Test task
        task = next(n for n in nodes if isinstance(n, Task))
        assert task.id == "Task_1"
        assert len(task.incoming) == 1
        assert len(task.outgoing) == 1

        # Test end event
        end_event = next(
            n for n in nodes if isinstance(n, Event) and n.event_type == "end"
        )
        assert end_event.id == "EndEvent_1"
        assert len(end_event.incoming) == 1
        assert len(end_event.outgoing) == 0

        # Test sequence flows
        assert len(flows) == 2

        flow1 = next(f for f in flows if f.id == "Flow_1")
        assert flow1.source_ref == "StartEvent_1"
        assert flow1.target_ref == "Task_1"

        flow2 = next(f for f in flows if f.id == "Flow_2")
        assert flow2.source_ref == "Task_1"
        assert flow2.target_ref == "EndEvent_1"

    async def test_parse_gateway_elements(self, parser):
        """Test parsing of gateway structures and conditions."""
        # Parse gateway process XML
        result = parser.parse(GATEWAY_PROCESS_XML)

        nodes = result["nodes"]
        flows = result["flows"]

        # Test exclusive gateway
        gateway = next(n for n in nodes if isinstance(n, Gateway))
        assert gateway.id == "Gateway_1"
        assert gateway.gateway_type == "exclusive"
        assert len(gateway.incoming) == 1
        assert len(gateway.outgoing) == 2

        # Test conditional sequence flows
        assert len(flows) == 5

        # Test flow with condition
        conditional_flow = next(f for f in flows if f.id == "Flow_2")
        assert conditional_flow.condition_expression == "amount > 1000"

        # Test tasks after gateway
        tasks = [n for n in nodes if isinstance(n, Task)]
        assert len(tasks) == 2

        task1 = next(t for t in tasks if t.id == "Task_1")
        assert len(task1.incoming) == 1
        assert len(task1.outgoing) == 1

        task2 = next(t for t in tasks if t.id == "Task_2")
        assert len(task2.incoming) == 1
        assert len(task2.outgoing) == 1

        # Test end event with multiple incoming flows
        end_event = next(
            n for n in nodes if isinstance(n, Event) and n.event_type == "end"
        )
        assert len(end_event.incoming) == 2

    async def test_parse_advanced_elements(self, parser):
        """Test parsing of advanced BPMN elements (subprocesses, multi-instance, data objects)."""
        # Parse advanced process XML
        result = parser.parse(ADVANCED_PROCESS_XML)

        nodes = result["nodes"]
        data_objects = result["data_objects"]

        # Test subprocess
        subprocess = next(n for n in nodes if isinstance(n, SubProcess))
        assert subprocess.id == "SubProcess_1"
        assert len(subprocess.incoming) == 1
        assert len(subprocess.outgoing) == 1

        # Test multi-instance characteristics
        assert subprocess.multi_instance is not None
        assert subprocess.multi_instance["cardinality"] == "3"

        # Test subprocess internal elements
        sub_nodes = subprocess.nodes

        sub_start = next(
            n for n in sub_nodes if isinstance(n, Event) and n.event_type == "start"
        )
        assert sub_start.id == "SubStart_1"

        sub_task = next(n for n in sub_nodes if isinstance(n, Task))
        assert sub_task.id == "SubTask_1"

        sub_end = next(
            n for n in sub_nodes if isinstance(n, Event) and n.event_type == "end"
        )
        assert sub_end.id == "SubEnd_1"

        # Test data objects
        assert len(data_objects) == 1
        data_obj = data_objects[0]
        assert data_obj.id == "Data_1"

    async def test_parse_custom_extensions(self, parser):
        """Test parsing of custom Pythmata extensions."""
        # Parse process with extensions XML
        result = parser.parse(EXTENSION_PROCESS_XML)

        nodes = result["nodes"]

        # Test service task with extensions
        task = next(n for n in nodes if isinstance(n, Task) and n.type == "serviceTask")
        assert task.id == "Task_1"

        # Test script content
        assert task.script is not None
        assert "print(" in task.script
        assert "result = x + y" in task.script

        # Test input variables
        assert task.input_variables is not None
        assert len(task.input_variables) == 2
        assert task.input_variables["x"] == "integer"
        assert task.input_variables["y"] == "integer"

        # Test output variables
        assert task.output_variables is not None
        assert len(task.output_variables) == 1
        assert task.output_variables["result"] == "integer"
        
    async def test_parse_service_task_config(self, parser):
        """Test parsing of service task configuration."""
        # Parse process with service task config XML
        result = parser.parse(SERVICE_TASK_PROCESS_XML)

        nodes = result["nodes"]

        # Test service task with service task config
        task = next(n for n in nodes if isinstance(n, Task) and n.type == "serviceTask")
        assert task.id == "Task_1"
        
        # Test service task config
        assert "serviceTaskConfig" in task.extensions
        service_config = task.extensions["serviceTaskConfig"]
        assert service_config["task_name"] == "logger"
        
        # Test properties
        properties = service_config["properties"]
        assert properties["level"] == "info"
        assert properties["message"] == "Test message"
        assert properties["include_variables"] == "true"
        assert properties["variable_filter"] == "var1,var2"
