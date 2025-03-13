"""Process XML samples for testing."""

# Basic process with single start event, task, and end event
SIMPLE_PROCESS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
                  xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
                  xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
                  id="Definitions_1"
                  targetNamespace="http://bpmn.io/schema/bpmn"
                  exporter="Pythmata"
                  exporterVersion="1.0">
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

# Process with multiple start events for testing event selection
MULTI_START_PROCESS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
                  xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
                  xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
                  id="Definitions_2"
                  targetNamespace="http://bpmn.io/schema/bpmn"
                  exporter="Pythmata"
                  exporterVersion="1.0">
  <bpmn:process id="Process_1" isExecutable="true">
    <bpmn:startEvent id="StartEvent_1">
      <bpmn:outgoing>Flow_1</bpmn:outgoing>
    </bpmn:startEvent>
    <bpmn:startEvent id="StartEvent_2">
      <bpmn:outgoing>Flow_2</bpmn:outgoing>
    </bpmn:startEvent>
    <bpmn:task id="Task_1">
      <bpmn:incoming>Flow_1</bpmn:incoming>
      <bpmn:incoming>Flow_2</bpmn:incoming>
      <bpmn:outgoing>Flow_3</bpmn:outgoing>
    </bpmn:task>
    <bpmn:endEvent id="EndEvent_1">
      <bpmn:incoming>Flow_3</bpmn:incoming>
    </bpmn:endEvent>
    <bpmn:sequenceFlow id="Flow_1" sourceRef="StartEvent_1" targetRef="Task_1" />
    <bpmn:sequenceFlow id="Flow_2" sourceRef="StartEvent_2" targetRef="Task_1" />
    <bpmn:sequenceFlow id="Flow_3" sourceRef="Task_1" targetRef="EndEvent_1" />
  </bpmn:process>
</bpmn:definitions>"""

# Sample BPMN XML with a service task
SERVICE_TASK_BPMN = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
                  xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
                  xmlns:pythmata="http://pythmata.org/schema/1.0/bpmn"
                  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                  id="Definitions_1"
                  targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="Process_1" isExecutable="true">
    <bpmn:startEvent id="StartEvent_1">
      <bpmn:outgoing>Flow_1</bpmn:outgoing>
    </bpmn:startEvent>
    <bpmn:sequenceFlow id="Flow_1" sourceRef="StartEvent_1" targetRef="ServiceTask_1" />
    <bpmn:serviceTask id="ServiceTask_1" name="Test Service Task">
      <bpmn:extensionElements>
        <pythmata:serviceTaskConfig taskName="test_task">
          <pythmata:properties>
            <pythmata:property name="test_prop" value="test_value" />
          </pythmata:properties>
        </pythmata:serviceTaskConfig>
      </bpmn:extensionElements>
      <bpmn:incoming>Flow_1</bpmn:incoming>
      <bpmn:outgoing>Flow_2</bpmn:outgoing>
    </bpmn:serviceTask>
    <bpmn:sequenceFlow id="Flow_2" sourceRef="ServiceTask_1" targetRef="EndEvent_1" />
    <bpmn:endEvent id="EndEvent_1">
      <bpmn:incoming>Flow_2</bpmn:incoming>
    </bpmn:endEvent>
  </bpmn:process>
</bpmn:definitions>"""


# Process with variable passing between nodes
VARIABLE_PASSING_PROCESS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
                  xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
                  xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
                  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                  xmlns:pythmata="http://pythmata.org/schema/1.0/bpmn"
                  id="Definitions_3"
                  targetNamespace="http://bpmn.io/schema/bpmn"
                  exporter="Pythmata"
                  exporterVersion="1.0">
  <bpmn:process id="Process_Variables" isExecutable="true">
    <!-- Start event -->
    <bpmn:startEvent id="StartEvent_1">
      <bpmn:outgoing>Flow_to_init</bpmn:outgoing>
    </bpmn:startEvent>
    
    <!-- Script task to initialize variables -->
    <bpmn:task id="InitVariables" name="Initialize Variables">
      <bpmn:incoming>Flow_to_init</bpmn:incoming>
      <bpmn:outgoing>Flow_to_gateway</bpmn:outgoing>
      <bpmn:script>
# Set initial variables
set_variable("value", 5)
set_variable("message", "Initial message")
print(f"Initialized variables: value={variables.get('value').value}, message={variables.get('message').value}")
      </bpmn:script>
    </bpmn:task>
    
    <!-- Exclusive gateway to route based on variable value -->
    <bpmn:exclusiveGateway id="ValueCheckGateway" name="Check Value">
      <bpmn:incoming>Flow_to_gateway</bpmn:incoming>
      <bpmn:outgoing>Flow_high_path</bpmn:outgoing>
      <bpmn:outgoing>Flow_low_path</bpmn:outgoing>
    </bpmn:exclusiveGateway>
    
    <!-- Path for high values -->
    <bpmn:task id="IncrementTask" name="Increment Value">
      <bpmn:incoming>Flow_high_path</bpmn:incoming>
      <bpmn:outgoing>Flow_from_increment</bpmn:outgoing>
      <bpmn:script>
# Increment the value
current_value = variables.get("value").value
new_value = current_value + 10
set_variable("value", new_value)
set_variable("path_taken", "high")
print(f"Incremented value from {current_value} to {new_value}")
      </bpmn:script>
    </bpmn:task>
    
    <!-- Path for low values -->
    <bpmn:task id="DoubleTask" name="Double Value">
      <bpmn:incoming>Flow_low_path</bpmn:incoming>
      <bpmn:outgoing>Flow_from_double</bpmn:outgoing>
      <bpmn:script>
# Double the value
current_value = variables.get("value").value
new_value = current_value * 2
set_variable("value", new_value)
set_variable("path_taken", "low")
print(f"Doubled value from {current_value} to {new_value}")
      </bpmn:script>
    </bpmn:task>
    
    <!-- Final task that uses the modified variables -->
    <bpmn:task id="FinalTask" name="Use Final Value">
      <bpmn:incoming>Flow_from_increment</bpmn:incoming>
      <bpmn:incoming>Flow_from_double</bpmn:incoming>
      <bpmn:outgoing>Flow_to_end</bpmn:outgoing>
      <bpmn:script>
# Use the final value
final_value = variables.get("value").value
path_taken = variables.get("path_taken").value
message = variables.get("message").value

# Create a summary message
summary = f"Final value: {final_value}, Path taken: {path_taken}, Original message: {message}"
set_variable("summary", summary)
print(summary)

# Store the result for verification
result = {"final_value": final_value, "path_taken": path_taken}
      </bpmn:script>
    </bpmn:task>
    
    <!-- End event -->
    <bpmn:endEvent id="EndEvent_1">
      <bpmn:incoming>Flow_to_end</bpmn:incoming>
    </bpmn:endEvent>
    
    <!-- Sequence flows -->
    <bpmn:sequenceFlow id="Flow_to_init" sourceRef="StartEvent_1" targetRef="InitVariables" />
    <bpmn:sequenceFlow id="Flow_to_gateway" sourceRef="InitVariables" targetRef="ValueCheckGateway" />
    
    <!-- Conditional flows from gateway -->
    <bpmn:sequenceFlow id="Flow_high_path" sourceRef="ValueCheckGateway" targetRef="IncrementTask">
      <bpmn:conditionExpression xsi:type="bpmn:tFormalExpression">variables.get("value").value &gt; 10</bpmn:conditionExpression>
    </bpmn:sequenceFlow>
    <bpmn:sequenceFlow id="Flow_low_path" sourceRef="ValueCheckGateway" targetRef="DoubleTask">
      <bpmn:conditionExpression xsi:type="bpmn:tFormalExpression">variables.get("value").value &lt;= 10</bpmn:conditionExpression>
    </bpmn:sequenceFlow>
    
    <!-- Flows to final task -->
    <bpmn:sequenceFlow id="Flow_from_increment" sourceRef="IncrementTask" targetRef="FinalTask" />
    <bpmn:sequenceFlow id="Flow_from_double" sourceRef="DoubleTask" targetRef="FinalTask" />
    
    <!-- Flow to end event -->
    <bpmn:sequenceFlow id="Flow_to_end" sourceRef="FinalTask" targetRef="EndEvent_1" />
  </bpmn:process>
</bpmn:definitions>"""


def create_test_bpmn_xml(start_event_id: str = "StartEvent_1") -> str:
    """Create a test BPMN XML with specified start event ID.

    Args:
        start_event_id: ID to use for the start event node. Defaults to "StartEvent_1".

    Returns:
        str: Complete BPMN XML document with the specified start event ID.
    """
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL">
  <bpmn:process id="Process_1" isExecutable="true">
    <bpmn:startEvent id="{start_event_id}">
      <bpmn:outgoing>Flow_1</bpmn:outgoing>
    </bpmn:startEvent>
    <bpmn:task id="Task_1">
      <bpmn:incoming>Flow_1</bpmn:incoming>
      <bpmn:outgoing>Flow_2</bpmn:outgoing>
    </bpmn:task>
    <bpmn:endEvent id="EndEvent_1">
      <bpmn:incoming>Flow_2</bpmn:incoming>
    </bpmn:endEvent>
    <bpmn:sequenceFlow id="Flow_1" sourceRef="{start_event_id}" targetRef="Task_1" />
    <bpmn:sequenceFlow id="Flow_2" sourceRef="Task_1" targetRef="EndEvent_1" />
  </bpmn:process>
</bpmn:definitions>"""
