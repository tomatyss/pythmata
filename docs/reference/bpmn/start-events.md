# Start Events in Pythmata

Start events are the entry points for process execution in BPMN. They define how and when a process instance is created. This guide explains the different types of start events supported by Pythmata and how to use them effectively.

## Types of Start Events

Pythmata supports several types of start events:

1. **None Start Event**: The default start event that creates a process instance when triggered manually
2. **Timer Start Event**: Creates process instances based on time-related conditions
3. **Message Start Event**: Creates a process instance when a specific message is received
4. **Signal Start Event**: Creates a process instance when a broadcast signal is detected

## None Start Event

The None Start Event is the simplest form of start event. It doesn't have any specific trigger condition and is used to manually start a process instance.

```xml
<bpmn:startEvent id="StartEvent_1">
  <bpmn:outgoing>Flow_1</bpmn:outgoing>
</bpmn:startEvent>
```

To start a process with a None Start Event, you can use the API to create a new process instance.

## Timer Start Event

Timer Start Events automatically create process instances based on time-related conditions. They are particularly useful for scheduled processes like daily reports, monthly billing cycles, or any time-based automation.

### How Timer Start Events Work

Timer Start Events in Pythmata are implemented through a sophisticated system that ensures reliability and persistence:

1. **Detection**: When a BPMN process with Timer Start Events is deployed, the system automatically detects and registers these events
2. **Scheduling**: The Timer Scheduler component schedules the events using APScheduler with Redis persistence
3. **Triggering**: When a timer triggers, a new process instance is automatically created
4. **Recovery**: Timer state is persisted in Redis, ensuring timers survive application restarts

### Timer Types

Timer Start Events support three timing mechanisms:

#### 1. Duration Timer

Creates a process instance after a specified time period from deployment:

```xml
<bpmn:startEvent id="StartEvent_1">
  <bpmn:timerEventDefinition>
    <bpmn:timeDuration xsi:type="bpmn:tFormalExpression">PT1H</bpmn:timeDuration>
  </bpmn:timerEventDefinition>
</bpmn:startEvent>
```

This example creates a process instance 1 hour after deployment.

#### 2. Date Timer

Creates a process instance at a specific date and time:

```xml
<bpmn:startEvent id="StartEvent_1">
  <bpmn:timerEventDefinition>
    <bpmn:timeDate xsi:type="bpmn:tFormalExpression">2025-03-15T09:00:00</bpmn:timeDate>
  </bpmn:timerEventDefinition>
</bpmn:startEvent>
```

This example creates a process instance on March 15, 2025, at 9:00 AM.

#### 3. Cycle Timer

Creates process instances repeatedly at specified intervals:

```xml
<bpmn:startEvent id="StartEvent_1">
  <bpmn:timerEventDefinition>
    <bpmn:timeCycle xsi:type="bpmn:tFormalExpression">R/PT24H</bpmn:timeCycle>
  </bpmn:timerEventDefinition>
</bpmn:startEvent>
```

This example creates a new process instance every 24 hours indefinitely.

### Timer Format

All timer values use the ISO 8601 format:

- **Duration**: `PT[hours]H[minutes]M[seconds]S`
  - Example: `PT1H30M` (1 hour and 30 minutes)
  - Example: `PT30M` (30 minutes)
  - Example: `PT10S` (10 seconds)

- **Date**: `YYYY-MM-DDThh:mm:ss`
  - Example: `2025-03-15T09:00:00` (March 15, 2025, at 9:00 AM)

- **Cycle**: `R[repetitions]/[interval]`
  - Example: `R3/PT1H` (repeat 3 times, every hour)
  - Example: `R/P1D` (repeat indefinitely, every day)

### Implementation Details

Under the hood, Timer Start Events in Pythmata work through several components:

1. **Timer Parser**: Extracts and parses timer definitions from BPMN XML
   - Converts ISO 8601 format into structured `TimerDefinition` objects
   - Creates appropriate APScheduler triggers based on timer type

2. **Timer Scheduler**: Manages scheduling and triggering of timers
   - Scans all process definitions for Timer Start Events
   - Generates unique timer IDs for each Timer Start Event
   - Stores timer metadata in Redis for persistence
   - Creates APScheduler jobs with appropriate triggers

3. **Persistence and Recovery**:
   - Timer state is stored in Redis with a key pattern: `{timer_prefix}{definition_id}:{node_id}:metadata`
   - On system restart, the `recover_from_crash` method retrieves all timer metadata
   - Each timer is rescheduled based on its stored definition
   - This ensures no timers are lost during system downtime

4. **Timer Triggering Process**:
   - When a timer triggers, the `timer_callback` function is called
   - A `process.timer_triggered` event is published to the event bus
   - The main application creates a new process instance
   - The process execution begins from the Timer Start Event

### Best Practices for Timer Start Events

1. **Choose the right timer type**:
   - Use duration for relative time periods
   - Use date for specific points in time
   - Use cycle for recurring events

2. **Include the xsi:type attribute**:
   - Always include `xsi:type="bpmn:tFormalExpression"` for timer definitions
   - This ensures compatibility with the BPMN 2.0 specification

3. **Consider time zones**:
   - Date timers are interpreted in UTC unless specified otherwise
   - Be aware of daylight saving time changes

4. **Test timer behavior**:
   - Use short durations for testing
   - Verify timer behavior in different scenarios

5. **Handle timer failures**:
   - Implement error handling for timer-related issues
   - Consider what happens if the system is down when a timer should trigger

6. **Monitor timer execution**:
   - Use logging to track timer creation and execution
   - Set up alerts for timer failures

## Message Start Event

Message Start Events create a process instance when a specific message is received. This is useful for processes that should start in response to external events.

```xml
<bpmn:startEvent id="StartEvent_1">
  <bpmn:messageEventDefinition messageRef="Message_1" />
</bpmn:startEvent>
```

To use Message Start Events effectively, you need to:
1. Define the message that will trigger the process
2. Configure the message correlation
3. Send the message through the appropriate channel

## Signal Start Event

Signal Start Events create a process instance when a broadcast signal is detected. Unlike messages, signals are not targeted at a specific recipient but are broadcast to all processes that can receive them.

```xml
<bpmn:startEvent id="StartEvent_1">
  <bpmn:signalEventDefinition signalRef="Signal_1" />
</bpmn:startEvent>
```

Signals are useful when:
1. Multiple processes need to react to the same event
2. The sender doesn't need to know who will receive the signal
3. You need a broadcast mechanism rather than point-to-point communication

## Combining Start Events

You can define multiple start events in a single process to provide different ways to initiate the process. Each start event can have its own outgoing sequence flow, allowing different initialization paths depending on how the process was started.

## Best Practices

1. **Use descriptive names**: Give your start events meaningful names that describe their purpose
2. **Document trigger conditions**: Add documentation about what triggers each start event
3. **Consider security implications**: Ensure that automatically triggered processes have appropriate security controls
4. **Test all start paths**: Verify that all start events correctly initialize the process
5. **Monitor start event activity**: Track which start events are being triggered and how often
