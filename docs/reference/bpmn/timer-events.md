# Timer Events in Pythmata

Timer events allow you to control the flow of your process based on time. This guide explains how to configure and use timer events in Pythmata.

## Timer Scheduler

Pythmata includes a robust timer scheduler that automatically triggers timer events based on their configuration. The timer scheduler has the following features:

- **Persistent Storage**: Timer state is stored in Redis, ensuring timers survive application restarts
- **Efficient Scheduling**: Uses APScheduler for efficient timer management
- **Fault Tolerance**: Automatically recovers timer state after system crashes
- **Distributed Execution**: Supports running in a distributed environment
- **Automatic Detection**: Automatically detects and schedules timers from process definitions

## Types of Timer Events

Pythmata supports three types of timer events:

1. **Start Timer Events**: Begin a process at a specific time, after a duration, or on a recurring schedule
2. **Intermediate Timer Events**: Pause the process flow until a specific time condition is met
3. **Boundary Timer Events**: Attached to activities to handle timeouts or schedule additional work

## Timer Configuration

Timer events can be configured using the properties panel in the BPMN modeler. When you select a timer event, you'll see a "Timer" tab in the properties panel with the following options:

### Timer Types

- **Duration**: Specifies a time period (e.g., 1 hour and 30 minutes)
- **Date**: Specifies a specific date and time
- **Cycle**: Specifies a recurring time interval

### Timer Formats

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

## Timer Event Behavior

### Start Timer Events

- **Duration**: The process starts after the specified duration from deployment
- **Date**: The process starts at the specified date and time
- **Cycle**: The process starts repeatedly at the specified intervals

### Intermediate Timer Events

- **Duration**: The process flow continues after the specified duration
- **Date**: The process flow continues at the specified date and time
- **Cycle**: The process flow continues after each cycle interval

### Boundary Timer Events

- **Interrupting**: Cancels the activity when the timer triggers
- **Non-interrupting**: Creates a parallel flow without cancelling the activity

## Examples

### Example 1: Process that starts every day at 9:00 AM

```xml
<bpmn:startEvent id="StartEvent_1">
  <bpmn:timerEventDefinition>
    <bpmn:timeCycle>R/PT24H</bpmn:timeCycle>
  </bpmn:timerEventDefinition>
</bpmn:startEvent>
```

### Example 2: Activity with a 1-hour timeout

```xml
<bpmn:userTask id="UserTask_1" name="Complete Form">
  <bpmn:incoming>Flow_1</bpmn:incoming>
  <bpmn:outgoing>Flow_2</bpmn:outgoing>
</bpmn:userTask>

<bpmn:boundaryEvent id="BoundaryEvent_1" attachedToRef="UserTask_1">
  <bpmn:timerEventDefinition>
    <bpmn:timeDuration>PT1H</bpmn:timeDuration>
  </bpmn:timerEventDefinition>
  <bpmn:outgoing>Flow_3</bpmn:outgoing>
</bpmn:boundaryEvent>
```

## Best Practices

1. **Use appropriate timer types**:
   - Use duration for relative time periods
   - Use date for specific points in time
   - Use cycle for recurring events

2. **Consider time zones**:
   - Date timers are interpreted in UTC unless specified otherwise
   - Be aware of daylight saving time changes

3. **Test timer behavior**:
   - Use short durations for testing
   - Verify timer behavior in different scenarios

4. **Handle timer failures**:
   - Implement error handling for timer-related issues
   - Consider what happens if the system is down when a timer should trigger
