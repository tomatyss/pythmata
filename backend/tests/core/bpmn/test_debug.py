import pytest
from pythmata.core.bpmn import BPMNValidator

def test_debug_schema_validation():
    """Debug test to understand schema validation errors."""
    xml = '''<?xml version="1.0" encoding="UTF-8"?>
    <bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL">
        <bpmn:process id="Process_1">
            <bpmn:startEvent id="Start_1"/>
            <bpmn:task id="Task_1"/>
            <bpmn:endEvent id="End_1"/>
            <bpmn:sequenceFlow id="Flow_1" sourceRef="Start_1" targetRef="Task_1"/>
            <bpmn:sequenceFlow id="Flow_2" sourceRef="Task_1" targetRef="End_1"/>
        </bpmn:process>
    </bpmn:definitions>
    '''
    validator = BPMNValidator()
    validation_errors = list(validator.schema.iter_errors(xml.strip()))
    
    print("\nSchema validation errors:")
    for error in validation_errors:
        print(f"- {error}")
        print(f"  Path: {error.path}")
        if hasattr(error, 'reason'):
            print(f"  Reason: {error.reason}")
    
    print("\nSchema info:")
    print(f"Schema location: {validator.schema.url}")
    print(f"Schema validation mode: {validator.schema.validation}")
    print(f"Schema imports: {validator.schema.imports}")
    print(f"Schema includes: {validator.schema.includes}")
