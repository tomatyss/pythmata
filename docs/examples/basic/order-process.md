# Basic Order Processing Example

This example demonstrates a simple order processing workflow using Pythmata.

## Process Overview

This workflow implements a basic order processing system with the following steps:
1. Receive order
2. Validate order
3. Process payment
4. Fulfill order
5. Send confirmation

## BPMN Diagram

```
[Start] -> [Receive Order] -> [Validate Order] -> (XOR Gateway)
                                                     |
                     [Request Additional Information] <- (Invalid)
                                                     |
                                             (Valid) -> [Process Payment] -> (XOR Gateway)
                                                                               |
                                                     [Handle Payment Failure] <- (Failed)
                                                                               |
                                                                       (Success) -> [Fulfill Order] -> [Send Confirmation] -> [End]
```

## Implementation

### 1. BPMN XML Definition

```xml
<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  xmlns:pythmata="http://pythmata.org/schema/1.0/bpmn"
                  id="OrderProcess"
                  targetNamespace="http://pythmata.org/examples">

  <bpmn:process id="OrderProcessing" name="Order Processing">
    <!-- Start Event -->
    <bpmn:startEvent id="Start_1" name="Order Received">
      <bpmn:outgoing>Flow_1</bpmn:outgoing>
    </bpmn:startEvent>

    <!-- Receive Order -->
    <bpmn:serviceTask id="Task_ReceiveOrder" name="Receive Order">
      <bpmn:incoming>Flow_1</bpmn:incoming>
      <bpmn:outgoing>Flow_2</bpmn:outgoing>
      <bpmn:extensionElements>
        <pythmata:taskConfig>
          <pythmata:script>
            # Store order details
            order_data = context.get_variable('order_data')
            context.set_variable('order_id', order_data['id'])
            context.set_variable('total_amount', order_data['amount'])
          </pythmata:script>
        </pythmata:taskConfig>
      </bpmn:extensionElements>
    </bpmn:serviceTask>

    <!-- Validate Order -->
    <bpmn:serviceTask id="Task_ValidateOrder" name="Validate Order">
      <bpmn:incoming>Flow_2</bpmn:incoming>
      <bpmn:outgoing>Flow_3</bpmn:outgoing>
      <bpmn:extensionElements>
        <pythmata:taskConfig>
          <pythmata:script>
            # Validate order details
            amount = context.get_variable('total_amount')
            is_valid = amount > 0 and amount < 10000
            context.set_variable('order_valid', is_valid)
          </pythmata:script>
        </pythmata:taskConfig>
      </bpmn:extensionElements>
    </bpmn:serviceTask>

    <!-- Validation Gateway -->
    <bpmn:exclusiveGateway id="Gateway_Validation" name="Order Valid?">
      <bpmn:incoming>Flow_3</bpmn:incoming>
      <bpmn:outgoing>Flow_4</bpmn:outgoing>
      <bpmn:outgoing>Flow_5</bpmn:outgoing>
    </bpmn:exclusiveGateway>

    <!-- Process Payment -->
    <bpmn:serviceTask id="Task_ProcessPayment" name="Process Payment">
      <bpmn:incoming>Flow_4</bpmn:incoming>
      <bpmn:outgoing>Flow_6</bpmn:outgoing>
      <bpmn:extensionElements>
        <pythmata:taskConfig>
          <pythmata:script>
            # Process payment
            amount = context.get_variable('total_amount')
            success = payment_service.process(amount)
            context.set_variable('payment_success', success)
          </pythmata:script>
        </pythmata:taskConfig>
      </bpmn:extensionElements>
    </bpmn:serviceTask>

    <!-- Payment Gateway -->
    <bpmn:exclusiveGateway id="Gateway_Payment" name="Payment Successful?">
      <bpmn:incoming>Flow_6</bpmn:incoming>
      <bpmn:outgoing>Flow_7</bpmn:outgoing>
      <bpmn:outgoing>Flow_8</bpmn:outgoing>
    </bpmn:exclusiveGateway>

    <!-- Fulfill Order -->
    <bpmn:serviceTask id="Task_FulfillOrder" name="Fulfill Order">
      <bpmn:incoming>Flow_7</bpmn:incoming>
      <bpmn:outgoing>Flow_9</bpmn:outgoing>
      <bpmn:extensionElements>
        <pythmata:taskConfig>
          <pythmata:script>
            # Fulfill order
            order_id = context.get_variable('order_id')
            fulfillment_service.process(order_id)
          </pythmata:script>
        </pythmata:taskConfig>
      </bpmn:extensionElements>
    </bpmn:serviceTask>

    <!-- Send Confirmation -->
    <bpmn:sendTask id="Task_SendConfirmation" name="Send Confirmation">
      <bpmn:incoming>Flow_9</bpmn:incoming>
      <bpmn:outgoing>Flow_10</bpmn:outgoing>
    </bpmn:sendTask>

    <!-- End Event -->
    <bpmn:endEvent id="End_1" name="Order Completed">
      <bpmn:incoming>Flow_10</bpmn:incoming>
    </bpmn:endEvent>

    <!-- Sequence Flows -->
    <bpmn:sequenceFlow id="Flow_1" sourceRef="Start_1" targetRef="Task_ReceiveOrder" />
    <bpmn:sequenceFlow id="Flow_2" sourceRef="Task_ReceiveOrder" targetRef="Task_ValidateOrder" />
    <bpmn:sequenceFlow id="Flow_3" sourceRef="Task_ValidateOrder" targetRef="Gateway_Validation" />
    <bpmn:sequenceFlow id="Flow_4" sourceRef="Gateway_Validation" targetRef="Task_ProcessPayment">
      <bpmn:conditionExpression>context.get_variable('order_valid')</bpmn:conditionExpression>
    </bpmn:sequenceFlow>
    <bpmn:sequenceFlow id="Flow_6" sourceRef="Task_ProcessPayment" targetRef="Gateway_Payment" />
    <bpmn:sequenceFlow id="Flow_7" sourceRef="Gateway_Payment" targetRef="Task_FulfillOrder">
      <bpmn:conditionExpression>context.get_variable('payment_success')</bpmn:conditionExpression>
    </bpmn:sequenceFlow>
    <bpmn:sequenceFlow id="Flow_9" sourceRef="Task_FulfillOrder" targetRef="Task_SendConfirmation" />
    <bpmn:sequenceFlow id="Flow_10" sourceRef="Task_SendConfirmation" targetRef="End_1" />
  </bpmn:process>
</bpmn:definitions>
```

### 2. Python Implementation

```python
from pythmata.core.engine import ProcessEngine
from pythmata.core.bpmn import BPMNParser

# Initialize engine
engine = ProcessEngine()

# Load and parse BPMN
with open('order_process.bpmn', 'r') as f:
    bpmn_xml = f.read()
    
process = BPMNParser().parse(bpmn_xml)
engine.deploy_process(process)

# Start process instance
order_data = {
    'id': '12345',
    'amount': 99.99,
    'customer': 'John Doe'
}

instance = engine.start_process(
    process_id='OrderProcessing',
    variables={'order_data': order_data}
)
```

## Testing the Process

### 1. Happy Path Test

```python
import pytest
from pythmata.testing import ProcessTestCase

class TestOrderProcess(ProcessTestCase):
    async def test_happy_path(self):
        # Start process
        instance = await self.engine.start_process(
            process_id='OrderProcessing',
            variables={
                'order_data': {
                    'id': '12345',
                    'amount': 99.99
                }
            }
        )
        
        # Verify process completed successfully
        self.assertTrue(await instance.is_completed())
        self.assertEqual(
            await instance.get_variable('payment_success'),
            True
        )
```

### 2. Invalid Order Test

```python
async def test_invalid_order(self):
    # Start process with invalid amount
    instance = await self.engine.start_process(
        process_id='OrderProcessing',
        variables={
            'order_data': {
                'id': '12345',
                'amount': -1  # Invalid amount
            }
        }
    )
    
    # Verify order was rejected
    self.assertFalse(
        await instance.get_variable('order_valid')
    )
```

## Running the Example

1. Save the BPMN XML to `order_process.bpmn`
2. Create a new Python file:

```python
from pythmata.core.engine import ProcessEngine
from pythmata.core.bpmn import BPMNParser

async def main():
    # Initialize engine
    engine = ProcessEngine()
    
    # Load and deploy process
    with open('order_process.bpmn', 'r') as f:
        process = BPMNParser().parse(f.read())
        await engine.deploy_process(process)
    
    # Start process instance
    instance = await engine.start_process(
        process_id='OrderProcessing',
        variables={
            'order_data': {
                'id': '12345',
                'amount': 99.99
            }
        }
    )
    
    # Wait for completion
    await instance.wait_for_completion()
    
    # Print results
    print(f"Order {await instance.get_variable('order_id')} processed")
    print(f"Payment success: {await instance.get_variable('payment_success')}")

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
```

## Next Steps

1. Try modifying the process to add:
   - Error handling
   - Timeout boundaries
   - Email notifications
   
2. Explore more complex patterns:
   - Parallel processing
   - User tasks
   - Message events

3. Learn about:
   - [Process Variables](../../reference/bpmn/variables.md)
   - [Error Handling](../../reference/bpmn/error-handling.md)
   - [Testing Strategies](../../guides/testing.md)
