# Compensation Transactions in Pythmata

Compensation transactions in BPMN provide a mechanism for "canceling" or "rolling back" successfully completed actions when problems occur at later stages of the process.

## Core Concepts

### Compensation Events

Pythmata supports the following types of compensation events:

- **Compensation Boundary Event** - attached to an activity and defines a compensation handler
- **Intermediate Throw Compensation Event** - explicitly triggers compensation
- **End Compensation Event** - triggers compensation and ends the process

### Compensation Tasks

Compensation tasks (tasks with the attribute `isForCompensation="true"`) are executed only when compensation is triggered and are not executed in the normal process flow.

## How It Works

### Registration of Compensation Handlers

When executing an activity with an attached compensation boundary event:

1. The activity itself is executed
2. The compensation handler is registered in the system but not executed
3. Process execution continues along the normal path

### Triggering Compensation

Compensation can be triggered:

1. Explicitly through an intermediate compensation event
2. Explicitly through an end compensation event
3. Automatically when a transaction error occurs

When compensation is triggered:

1. The system finds all registered compensation handlers
2. Handlers are executed in reverse order of their registration (LIFO)
3. Each handler gets access to the data of the corresponding activity

## Usage Example

Below is an example of a travel booking business process with compensation:

```xml
<bpmn:task id="Task_BookHotel" name="Book Hotel">
  <bpmn:incoming>Flow_1</bpmn:incoming>
  <bpmn:outgoing>Flow_2</bpmn:outgoing>
</bpmn:task>

<bpmn:boundaryEvent id="BoundaryEvent_Hotel" attachedToRef="Task_BookHotel">
  <bpmn:compensateEventDefinition />
  <bpmn:outgoing>Flow_Comp_Hotel</bpmn:outgoing>
</bpmn:boundaryEvent>

<bpmn:task id="Task_CancelHotel" name="Cancel Hotel Booking" isForCompensation="true">
  <bpmn:incoming>Flow_Comp_Hotel</bpmn:incoming>
</bpmn:task>

<!-- Trigger compensation when payment fails -->
<bpmn:intermediateThrowEvent id="ThrowEvent_Compensation">
  <bpmn:incoming>Flow_PaymentFailed</bpmn:incoming>
  <bpmn:outgoing>Flow_AfterCompensation</bpmn:outgoing>
  <bpmn:compensateEventDefinition />
</bpmn:intermediateThrowEvent>
```

In this example:
1. First, a hotel is booked (Task_BookHotel)
2. A compensation boundary event (BoundaryEvent_Hotel) is attached to the booking activity
3. When Task_BookHotel completes successfully, the process continues, but a compensation handler is registered
4. If a payment error occurs later, the intermediate compensation event (ThrowEvent_Compensation) triggers compensation
5. The system finds all registered handlers and executes them, including Task_CancelHotel

## Implementation Details

### Processing Compensation Boundary Events

When a compensation boundary event is encountered:

1. The system finds the corresponding compensation handler (the task connected to the boundary event)
2. Information about the compensation handler is stored in the state storage (Redis)

### Executing Compensation

When compensation is triggered:

1. If a specific activity is specified (via the activityRef attribute), only its compensation handler is executed
2. If no activity is specified, all compensation handlers in the current scope are executed in reverse order

### Passing Data to Compensation Handlers

Compensation handlers receive the following data:
- Identifier of the compensated activity
- Data that was available to the compensated activity
- Identifier of the compensation boundary event

## Limitations and Special Features

1. Compensation tasks should not have incoming control flows, except for flows from compensation boundary events
2. Compensation tasks are not executed in the normal process flow
3. Compensation handlers are executed in LIFO (last registered - first executed) order

## Recommendations for Usage

1. Use compensation for operations that require explicit rollback (e.g., external API calls)
2. Ensure compensation handler idempotency
3. Consider using database transactions for operations that can be automatically rolled back
4. Include logging in compensation handlers for process tracking 