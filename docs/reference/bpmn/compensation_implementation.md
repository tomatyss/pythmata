# Compensation Transactions Implementation Guide

## Overview

This document provides a detailed description of the compensation transactions implementation in the Pythmata project. It covers the architecture, implementation details, usage examples, and testing procedures.

## Table of Contents

1. [Architecture](#architecture)
2. [Implementation Details](#implementation-details)
3. [Usage Examples](#usage-examples)
4. [Testing](#testing)
5. [Results and Benefits](#results-and-benefits)

## Architecture

### Core Components

1. **CompensationHandler**
   - Main class for handling compensation events and activities
   - Located in `backend/src/pythmata/core/engine/node_executor.py`
   - Manages different types of compensation events and their execution

2. **CompensationScope**
   - Represents a scope that can contain compensation handlers
   - Located in `backend/src/pythmata/core/engine/events/compensation.py`
   - Manages the hierarchy and execution order of compensation handlers

3. **BPMN Parser Extensions**
   - Enhanced parser for compensation-related BPMN elements
   - Located in `backend/src/pythmata/core/bpmn/parser.py`
   - Handles compensation-specific attributes and relationships

### Key Classes

```python
class CompensationHandler:
    """Handles compensation events and activities."""
    
    async def handle_compensation_event(self, token: Token, event: Event, process_graph: Dict):
        """Main entry point for compensation event processing."""
        
    async def _handle_compensation_boundary_event(self, token: Token, event: Event, process_graph: Dict):
        """Handles compensation boundary events."""
        
    async def _handle_compensation_throw_event(self, token: Token, event: Event, process_graph: Dict):
        """Handles compensation throw events."""
```

## Implementation Details

### 1. Changes Made

#### New Classes Created
```python
# backend/src/pythmata/core/engine/events/compensation.py
class CompensationScope:
    """Represents a compensation scope that can contain compensation handlers"""
    def __init__(self, scope_id: str, parent_scope: Optional["CompensationScope"] = None):
        self.scope_id = scope_id
        self.parent_scope = parent_scope
        self.handlers: List[CompensationBoundaryEvent] = []
```

#### NodeExecutor Extensions
```python
# backend/src/pythmata/core/engine/node_executor.py
class CompensationHandler:
    """Handles compensation events and activities."""
    async def handle_compensation_event(self, token: Token, event: Event, process_graph: Dict):
        # Handle different types of compensation events
```

#### BPMN Parser Enhancements
```python
# backend/src/pythmata/core/bpmn/parser.py
def _parse_boundary_event(self, elem: ET.Element) -> Event:
    # Added support for compensation attributes
    if event_definition == "compensation":
        activity_ref = compensation_def.get("activityRef")
        wait_for_completion = wait_for_completion_str.lower() == "true"
```

### 2. How It Works

#### Process Flow

1. **Registration Phase**
   ```python
   # When Task_BookHotel is executed
   await compensation_handler._handle_compensation_boundary_event(token, event, process_graph)
   # Result: Compensation handler information is stored in Redis
   ```

2. **Compensation Trigger**
   ```python
   # When payment error occurs
   await compensation_handler._handle_compensation_throw_event(token, event, process_graph)
   # Result: New token with COMPENSATION state is created
   ```

3. **Compensation Execution**
   ```python
   # Task_CancelHotel is executed
   compensation_token = Token(
       instance_id=token.instance_id,
       node_id=handler_data["handler_id"],
       state=TokenState.COMPENSATION,
       data={
           "compensated_activity_id": handler_data["activity_id"],
           "original_token_data": token.data
       }
   )
   ```

## Usage Examples

### 1. BPMN Process Example

```xml
<bpmn:process id="TravelBooking">
    <!-- Main hotel booking task -->
    <bpmn:task id="Task_BookHotel" name="Book Hotel">
        <bpmn:incoming>Flow_1</bpmn:incoming>
        <bpmn:outgoing>Flow_2</bpmn:outgoing>
    </bpmn:task>

    <!-- Compensation boundary event -->
    <bpmn:boundaryEvent id="BoundaryEvent_Hotel" attachedToRef="Task_BookHotel">
        <bpmn:compensateEventDefinition />
        <bpmn:outgoing>Flow_Comp_Hotel</bpmn:outgoing>
    </bpmn:boundaryEvent>

    <!-- Compensation task -->
    <bpmn:task id="Task_CancelHotel" name="Cancel Hotel Booking" isForCompensation="true">
        <bpmn:incoming>Flow_Comp_Hotel</bpmn:incoming>
    </bpmn:task>

    <!-- Compensation trigger event -->
    <bpmn:intermediateThrowEvent id="ThrowEvent_Compensation">
        <bpmn:incoming>Flow_PaymentFailed</bpmn:incoming>
        <bpmn:outgoing>Flow_AfterCompensation</bpmn:outgoing>
        <bpmn:compensateEventDefinition />
    </bpmn:intermediateThrowEvent>
</bpmn:process>
```

### 2. Code Example

```python
# Example of travel booking process
async def book_travel():
    # 1. Book hotel
    hotel_booking = await book_hotel()
    
    # 2. Book flights
    flight_booking = await book_flights()
    
    # 3. Process payment
    try:
        payment = await process_payment()
    except PaymentError:
        # Trigger compensation
        await trigger_compensation()
        # Result: Cancel hotel and flight bookings
        raise
```

## Testing

### 1. Running Tests

```bash
cd backend
poetry run python ../basic_compensation_test.py
```

### 2. Test Scenarios

```python
@pytest.mark.asyncio
async def test_compensation_boundary_event():
    # Create compensation scope
    process_scope = CompensationScope(scope_id="Process_1")
    
    # Create handler for Task_1
    boundary_event = CompensationBoundaryEvent(
        event_id="BoundaryEvent_1",
        attached_to_id="Task_1",
        handler_id="CompensationHandler_1",
        scope=process_scope
    )
    
    # Verify results
    assert result.state == TokenState.ACTIVE
    assert result.node_id == handler_id
```

## Results and Benefits

### 1. Process Reliability
- Automatic error recovery
- Data consistency preservation
- Ability to rollback successfully completed actions

### 2. Flexibility
- Support for various compensation event types
- Ability to compensate individual activities or entire process
- Configurable compensation scopes

### 3. Monitoring and Debugging
- Detailed logging of all compensation stages
- Ability to track compensation state
- Context preservation for debugging

## Conclusion

The compensation transactions implementation provides a robust and flexible solution for handling process rollbacks and error recovery in BPMN processes. The implementation follows BPMN 2.0 specifications and provides comprehensive support for all compensation-related features.
