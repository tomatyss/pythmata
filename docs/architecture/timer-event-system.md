# Timer Event System Architecture

This document provides a detailed technical overview of the Timer Event System in Pythmata, focusing on the implementation details, component interactions, and design decisions.

## System Overview

The Timer Event System is responsible for detecting, scheduling, and triggering timer events in BPMN processes. It's particularly important for Timer Start Events, which automatically create process instances based on time-related conditions.

```
+-------------------+     +-------------------+     +-------------------+
|                   |     |                   |     |                   |
|  BPMN Definition  |---->|  Timer Scheduler  |---->|  Process Engine   |
|                   |     |                   |     |                   |
+-------------------+     +-------------------+     +-------------------+
                               |         ^
                               v         |
                          +-------------------+
                          |                   |
                          |  Redis Storage    |
                          |                   |
                          +-------------------+
```

## Core Components

### 1. Timer Parser

**Location**: `backend/src/pythmata/core/engine/events/timer_parser.py`

**Responsibilities**:
- Extract timer definitions from BPMN XML
- Parse ISO 8601 format strings into structured objects
- Create appropriate APScheduler triggers based on timer type

**Key Functions**:
- `parse_timer_definition()`: Converts ISO 8601 strings to `TimerDefinition` objects
- `extract_timer_definition()`: Extracts timer values from BPMN XML
- `find_timer_events_in_definition()`: Locates all timer events in a process definition

**Data Structures**:
```python
@dataclass
class TimerDefinition:
    timer_type: str  # "duration", "date", or "cycle"
    trigger: Union[DateTrigger, IntervalTrigger]
    repetitions: Optional[int] = None
    duration: Optional[timedelta] = None
    target_date: Optional[datetime] = None
    interval: Optional[timedelta] = None
```

### 2. Timer Scheduler

**Location**: `backend/src/pythmata/core/engine/events/timer_scheduler.py`

**Responsibilities**:
- Scan process definitions for timer events
- Schedule timers using APScheduler
- Persist timer state in Redis
- Recover timer state after system restarts
- Trigger process instances when timers fire

**Key Methods**:
- `start()`: Initialize and start the scheduler
- `recover_from_crash()`: Restore timer state after system restart
- `_scan_for_timer_start_events()`: Find and schedule timer events
- `_schedule_timer()`: Create APScheduler jobs for timers

**Implementation Details**:
- Uses APScheduler with Redis job store for persistence
- Generates unique timer IDs based on process definition and node ID
- Stores timer metadata in Redis for recovery
- Periodically scans for changes in process definitions

### 3. Timer Event Implementation

**Location**: `backend/src/pythmata/core/engine/events/timer.py`

**Responsibilities**:
- Execute timer behavior
- Handle timer cancellation
- Manage timer state
- Support different timer types (duration, date, cycle)

**Key Classes**:
- `TimerEvent`: Base implementation for all timer events
- `TimerBoundaryEvent`: Specialized implementation for boundary events

**Key Methods**:
- `execute()`: Execute timer behavior based on type
- `start()`: Initialize timer and save state
- `cancel()`: Cancel a running timer
- `restore()`: Restore timer from saved state

### 4. Event Handler

**Location**: `backend/src/pythmata/core/engine/event_handler.py`

**Responsibilities**:
- Process BPMN events including timer events
- Move tokens through the process based on event outcomes
- Trigger event subprocesses

**Key Methods**:
- `handle_event()`: Process different event types
- `trigger_event_subprocess()`: Start event subprocess execution

## Process Flow

### Timer Start Event Lifecycle

1. **Detection**:
   - When a BPMN process with Timer Start Events is deployed
   - The `TimerScheduler._scan_for_timer_start_events()` method detects timer definitions
   - `find_timer_events_in_definition()` extracts timer information

2. **Scheduling**:
   - `_schedule_timer()` creates an APScheduler job
   - Timer metadata is stored in Redis with key: `{timer_prefix}{definition_id}:{node_id}:metadata`
   - APScheduler job is configured with appropriate trigger (DateTrigger or IntervalTrigger)

3. **Persistence**:
   - Timer state is stored in Redis for recovery
   - APScheduler uses RedisJobStore for job persistence
   - Timer metadata includes definition ID, node ID, timer type, and timer definition

4. **Triggering**:
   - When a timer fires, APScheduler calls the `timer_callback()` function
   - A new event loop is created for the callback
   - A `process.timer_triggered` event is published to the event bus

5. **Process Instance Creation**:
   - The main application receives the `process.timer_triggered` event
   - A new process instance is created with the provided instance ID
   - The process execution begins from the Timer Start Event

6. **Recovery**:
   - On system restart, `recover_from_crash()` retrieves timer metadata from Redis
   - Each timer is rescheduled based on its stored definition
   - This ensures no timers are lost during system downtime

### Timer Types Implementation

#### Duration Timer
```python
# Implementation in timer.py
async def _execute_duration(self, token: Token) -> None:
    await self.start(token)
    try:
        await asyncio.sleep(self.duration.total_seconds())
    except asyncio.CancelledError:
        raise TimerCancelled()
    finally:
        await self._cleanup(token.instance_id)
```

#### Date Timer
```python
# Implementation in timer.py
async def _execute_date(self, token: Token) -> None:
    await self.start(token)
    now = datetime.now(timezone.utc)
    if self.target_date > now:
        try:
            await asyncio.sleep((self.target_date - now).total_seconds())
        except asyncio.CancelledError:
            raise TimerCancelled()
    await self._cleanup(token.instance_id)
```

#### Cycle Timer
```python
# Implementation in timer.py
async def _execute_cycle(self, token: Token) -> None:
    await self.start(token)
    try:
        for _ in range(self.repetitions):
            await asyncio.sleep(self.interval.total_seconds())
    except asyncio.CancelledError:
        raise TimerCancelled()
    finally:
        await self._cleanup(token.instance_id)
```

## Design Decisions

### 1. APScheduler with Redis JobStore

**Decision**: Use APScheduler with Redis JobStore for timer scheduling and persistence.

**Rationale**:
- APScheduler provides a robust scheduling framework
- Redis JobStore enables persistence across system restarts
- Redis is already used for state management in the system
- Supports distributed deployment scenarios

### 2. Event Bus for Timer Triggering

**Decision**: Use an event bus to decouple timer triggering from process instance creation.

**Rationale**:
- Decouples the timer system from the process engine
- Allows for distributed deployment
- Provides a clean separation of concerns
- Enables better error handling and recovery

### 3. Separate Event Loop for Timer Callbacks

**Decision**: Create a new event loop for timer callbacks.

**Rationale**:
- Prevents conflicts with the main event loop
- Isolates timer execution from other system operations
- Ensures clean resource management
- Avoids potential deadlocks

### 4. Redis for Timer Metadata Storage

**Decision**: Store timer metadata in Redis separate from APScheduler's JobStore.

**Rationale**:
- Provides additional recovery capabilities
- Enables custom timer management operations
- Allows for more detailed timer state tracking
- Simplifies timer inspection and debugging

## Error Handling and Recovery

### Timer Execution Errors

- All timer operations are wrapped in try/except blocks
- Errors are logged with detailed information
- Failed timers don't affect other timers
- System can continue operating even if some timers fail

### System Crash Recovery

1. On system startup, `recover_from_crash()` is called
2. Redis is queried for all timer metadata keys
3. Each timer is reconstructed from its metadata
4. Timers are rescheduled with APScheduler
5. Normal operation resumes

### Timer Cancellation

- Timers can be explicitly cancelled via the `cancel()` method
- Cancellation is handled gracefully with proper cleanup
- Cancelled timers are removed from both APScheduler and Redis

## Performance Considerations

### Scalability

- The timer system can handle thousands of timers
- Redis provides efficient storage and retrieval
- APScheduler efficiently manages timer execution
- The event bus enables distributed processing

### Optimization

- Periodic scanning rather than continuous monitoring
- Efficient timer state storage
- Minimal memory footprint
- Clean resource management

## Security Considerations

- Timer events can only be defined in authorized process definitions
- Timer execution is subject to the same security controls as manual process execution
- Redis security best practices should be followed
- Event bus communications should be secured

## Future Enhancements

- Enhanced monitoring and metrics for timer execution
- More sophisticated timer recovery strategies
- Support for dynamic timer definitions
- Integration with external time sources
- Advanced timer failure handling
