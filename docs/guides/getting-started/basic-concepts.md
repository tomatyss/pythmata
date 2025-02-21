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

### Connection Management
```python
from pythmata.core.common.connections import ConnectionManager, ensure_connected

class Database(ConnectionManager):
    """Database connection management example."""
    
    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.engine = create_async_engine(
            str(settings.database.url),
            pool_size=settings.database.pool_size,
            max_overflow=settings.database.max_overflow
        )
    
    async def _do_connect(self) -> None:
        """Establish database connection."""
        if not self.engine:
            raise RuntimeError("Database engine not initialized")
        
        # Test connection
        conn = await self.engine.connect()
        try:
            await conn.execute("SELECT 1")
        finally:
            await conn.close()
    
    async def _do_disconnect(self) -> None:
        """Close database connection."""
        if self.engine:
            await self.engine.dispose()
    
    @ensure_connected
    async def execute_query(self, query: str) -> Any:
        """Execute a query with automatic connection management."""
        async with self.engine.connect() as conn:
            return await conn.execute(query)
```

### Using Connection-Managed Services
```python
# Initialize database with connection management
db = Database(settings)

# Connection is automatically established when needed
result = await db.execute_query("SELECT * FROM processes")

# Connection state is tracked
assert db.is_connected

# Automatic reconnection on failures
try:
    await db.execute_query("SELECT * FROM processes")
except ConnectionError:
    # Connection error is handled, retry attempted
    pass

# Clean up resources
await db.disconnect()
```

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

## Connection Management Best Practices

### 1. Resource Management
```python
async with Database(settings) as db:
    # Connection is automatically established
    result = await db.execute_query("SELECT 1")
    # Connection is automatically closed after context
```

### 2. Error Handling
```python
try:
    await db.connect()
except ConnectionError as e:
    logger.error(f"Failed to connect: {e}")
    # Handle connection failure

# Or using the decorator
@ensure_connected
async def my_function(self):
    # Connection is guaranteed here
    pass
```

### 3. State Management
```python
if not db.is_connected:
    await db.connect()

# Check connection before operations
assert db.is_connected
```

## Process Design Best Practices
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

1. Explore [Example Workflows](../../examples/basic/order-process.md)
2. Learn about [Advanced Features](../../reference/bpmn/advanced-features.md)
