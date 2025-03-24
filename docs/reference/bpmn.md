# BPMN Reference

## Overview

This document provides detailed information about Pythmata's BPMN implementation.

## Variables

### Process Variables
Process variables are used to store and manage data within a process instance.

```python
# Set a variable
context.set_variable('order_id', '12345')

# Get a variable
order_id = context.get_variable('order_id')
```

### Variable Scopes
Variables can be scoped to:
- Process instance
- Subprocess
- Activity

## Error Handling

### Error Events
Error events can be used to handle business errors and technical exceptions:

```xml
<bpmn:boundaryEvent id="Error_1" attachedToRef="Task_1">
    <bpmn:errorEventDefinition errorRef="Error_Code" />
</bpmn:boundaryEvent>
```

### Error Handling in Scripts
```python
# Raise a business error
raise BusinessError("INVALID_ORDER", "Order amount exceeds limit")

# Handle technical errors
try:
    external_service.call()
except Exception as e:
    context.set_variable('error_details', str(e))
    raise TechnicalError("SERVICE_ERROR")
```

## Advanced Features

### Multi-Instance Activities
Configure activities to execute multiple times in parallel or sequence:

```xml
<bpmn:serviceTask id="Task_1">
    <bpmn:multiInstanceLoopCharacteristics>
        <bpmn:loopCardinality>3</bpmn:loopCardinality>
    </bpmn:multiInstanceLoopCharacteristics>
</bpmn:serviceTask>
```

### Timer Events
Schedule activities or handle timeouts:

```xml
<bpmn:intermediateCatchEvent id="Timer_1">
    <bpmn:timerEventDefinition>
        <bpmn:timeDuration>PT15M</bpmn:timeDuration>
    </bpmn:timerEventDefinition>
</bpmn:intermediateCatchEvent>
```

For detailed information on configuring and using timer events, see the [Timer Events](bpmn/timer-events.md) documentation.

### Message Correlation
Handle asynchronous communication between processes:

```xml
<bpmn:intermediateCatchEvent id="Message_1">
    <bpmn:messageEventDefinition messageRef="Payment_Received" />
</bpmn:intermediateCatchEvent>
```

## Testing

### Unit Testing Processes
```python
class TestOrderProcess(ProcessTestCase):
    async def test_happy_path(self):
        instance = await self.engine.start_process(
            'OrderProcess',
            variables={'amount': 100}
        )
        self.assertTrue(await instance.is_completed())
```

### Integration Testing
```python
async def test_external_service_integration(self):
    with mock.patch('services.payment.process') as mock_payment:
        mock_payment.return_value = True
        instance = await self.engine.start_process(
            'OrderProcess',
            variables={'amount': 100}
        )
        self.assertTrue(mock_payment.called)
```

## Best Practices

1. Process Design
   - Keep processes focused and manageable
   - Use appropriate error boundaries
   - Consider transaction boundaries
   - Document process purpose and behavior

2. Variable Management
   - Use clear naming conventions
   - Document variable purposes
   - Consider variable scoping
   - Clean up temporary variables

3. Error Handling
   - Use specific error events
   - Implement proper compensation
   - Log error details
   - Consider retry strategies

4. Testing
   - Test happy path scenarios
   - Test error conditions
   - Verify timer behavior
   - Check boundary conditions
