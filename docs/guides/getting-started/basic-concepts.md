# BPMN Basic Concepts in Pythmata

This guide introduces the fundamental BPMN (Business Process Model and Notation) concepts as implemented in Pythmata.

## Introduction to BPMN

BPMN is a standardized graphical notation for specifying business processes. Pythmata implements BPMN 2.0, providing a robust engine for executing these process definitions.

## Core BPMN Elements

### 1. Flow Objects

#### Tasks
- **User Task**: Requires human interaction to complete
- **Service Task**: Automated activity executed by the system
- **Script Task**: Executes a script in the process context
- **Send Task**: Sends a message to an external participant
- **Receive Task**: Waits for a message from an external participant

#### Events
- **Start Events**: Indicate where a process begins
  - Simple start event
  - Message start event
  - Timer start event
  
- **End Events**: Indicate where a process ends
  - Simple end event
  - Error end event
  - Terminate end event
  
- **Intermediate Events**: Represent events that occur during process execution
  - Timer events
  - Message events
  - Signal events
  - Error events

#### Gateways
- **Exclusive Gateway (XOR)**: Routes the flow to exactly one path
- **Parallel Gateway (AND)**: Splits flow into parallel paths
- **Inclusive Gateway (OR)**: Routes the flow to one or more paths
- **Event-Based Gateway**: Routes based on occurring events

### 2. Connecting Objects

#### Sequence Flow
- Connects flow objects in a process
- Defines the execution order
- Can include conditions for gateways

#### Message Flow
- Shows message exchange between participants
- Crosses pool boundaries
- Represents asynchronous communication

### 3. Containers

#### Pools
- Represents a participant in a process
- Contains one or more lanes
- Used in collaboration diagrams

#### Lanes
- Subdivisions within a pool
- Often represents roles or departments
- Organizes and categorizes activities

### 4. Advanced Concepts

#### Subprocesses
- **Embedded Subprocess**: Contained within the parent process
- **Call Activity**: Calls an external process
- **Event Subprocess**: Triggered by events
- **Transaction**: Groups activities that must complete together

#### Multi-Instance Activities
- **Parallel**: Executes instances simultaneously
- **Sequential**: Executes instances in order
- Configurable cardinality and completion conditions

#### Boundary Events
- Attached to activities
- Handle exceptions and timeouts
- Can be interrupting or non-interrupting

## Implementation in Pythmata

### Token-Based Execution
```python
# Example of token movement
async def move_token(self, token: Token, target_node_id: str) -> Token:
    # Remove token from current node
    await self.state_manager.remove_token(
        instance_id=token.instance_id,
        node_id=token.node_id
    )
    
    # Create new token at target node
    new_token = token.copy(node_id=target_node_id)
    await self.state_manager.add_token(
        instance_id=new_token.instance_id,
        node_id=new_token.node_id,
        data=new_token.to_dict()
    )
    
    return new_token
```

### State Management
- Process instance tracking
- Token lifecycle management
- Variable scoping
- Event correlation

### Event Handling
- Event subscription
- Event correlation
- Timer management
- Error propagation

## Best Practices

### Process Design
1. Use clear and meaningful names
2. Keep processes focused and manageable
3. Use appropriate level of detail
4. Document process purpose and behavior

### Implementation
1. Handle all possible paths
2. Implement proper error handling
3. Use appropriate event types
4. Consider transaction boundaries

### Testing
1. Test happy path scenarios
2. Test error conditions
3. Verify timer behavior
4. Check boundary conditions

## Common Patterns

### Sequential Flow
```xml
<bpmn:sequenceFlow id="Flow_1" sourceRef="Task_1" targetRef="Task_2" />
```

### Parallel Processing
```xml
<bpmn:parallelGateway id="Gateway_1" />
<bpmn:sequenceFlow id="Flow_1" sourceRef="Gateway_1" targetRef="Task_1" />
<bpmn:sequenceFlow id="Flow_2" sourceRef="Gateway_1" targetRef="Task_2" />
```

### Error Handling
```xml
<bpmn:boundaryEvent id="Error_1" attachedToRef="Task_1">
    <bpmn:errorEventDefinition errorRef="Error_Code" />
</bpmn:boundaryEvent>
```

## Next Steps

1. Try the [Getting Started Tutorial](../tutorials/getting-started.md)
2. Explore [Example Workflows](../../examples/basic/)
3. Learn about [Advanced Features](../../reference/bpmn/advanced-features.md)
