# API Reference

## REST API

### Process Definitions

#### List Process Definitions
```http
GET /processes
```

Response:
```json
{
  "data": {
    "items": [
      {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "name": "Order Processing",
        "version": 1,
        "bpmn_xml": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>...",
        "created_at": "2025-02-03T12:00:00Z",
        "updated_at": "2025-02-03T12:00:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "pageSize": 1,
    "totalPages": 1
  }
}
```

#### Get Process Definition
```http
GET /processes/{process_id}
```

Response:
```json
{
  "data": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "Order Processing",
    "version": 1,
    "bpmn_xml": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>...",
    "created_at": "2025-02-03T12:00:00Z",
    "updated_at": "2025-02-03T12:00:00Z"
  }
}
```

#### Create Process Definition
```http
POST /processes
Content-Type: application/json

{
  "name": "Order Processing",
  "bpmn_xml": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>...",
  "version": 1  // Optional, defaults to 1
}
```

Response:
```json
{
  "data": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "Order Processing",
    "version": 1,
    "bpmn_xml": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>...",
    "created_at": "2025-02-03T12:00:00Z",
    "updated_at": "2025-02-03T12:00:00Z"
  }
}
```

#### Update Process Definition
```http
PUT /processes/{process_id}
Content-Type: application/json

{
  "name": "Updated Order Process",  // Optional
  "bpmn_xml": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>...",  // Optional
  "version": 2  // Optional, auto-increments if not specified
}
```

Response:
```json
{
  "data": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "Updated Order Process",
    "version": 2,
    "bpmn_xml": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>...",
    "created_at": "2025-02-03T12:00:00Z",
    "updated_at": "2025-02-03T12:01:00Z"
  }
}
```

#### Delete Process Definition
```http
DELETE /processes/{process_id}
```

Response:
```json
{
  "message": "Process deleted successfully"
}
```

### Error Handling

All error responses follow this format:
```json
{
  "detail": "Error message describing what went wrong"
}
```

Common error scenarios:
- 404: Process not found
- 500: Internal server error (with error details)

### Data Models

#### ProcessDefinitionCreate
```typescript
{
  name: string;          // Process definition name
  bpmn_xml: string;      // BPMN 2.0 XML content
  version?: number;      // Optional version number (defaults to 1)
}
```

#### ProcessDefinitionUpdate
```typescript
{
  name?: string;         // Optional new name
  bpmn_xml?: string;    // Optional new BPMN XML
  version?: number;     // Optional new version
}
```

#### ProcessDefinitionResponse
```typescript
{
  id: UUID;             // Unique identifier
  name: string;         // Process name
  version: number;      // Version number
  bpmn_xml: string;     // BPMN XML content
  created_at: string;   // Creation timestamp
  updated_at: string;   // Last update timestamp
}
```

#### PaginatedResponse
```typescript
{
  items: T[];           // Array of items
  total: number;        // Total number of items
  page: number;         // Current page number
  pageSize: number;     // Items per page
  totalPages: number;   // Total number of pages
}
```

### API Response Wrapper

All successful responses are wrapped in a data object:
```typescript
{
  data: T;  // Response data of type T
}
```

### Best Practices

1. Version Management
   - Process definitions are versioned automatically
   - Version increments on updates unless specified
   - Keep track of version history

2. Error Handling
   - Check for 404 when accessing specific processes
   - Handle 500 errors with proper error messages
   - Use try-catch blocks for error handling

3. BPMN XML
   - Validate BPMN XML before sending
   - Use proper XML escaping
   - Include all required BPMN elements

4. Pagination
   - Current implementation returns all items
   - Future enhancement: add page and pageSize query parameters
   - Handle empty result sets appropriately

### Example Usage

Using fetch:
```javascript
// List processes
const response = await fetch('/processes');
const { data } = await response.json();
const processes = data.items;

// Create process
const newProcess = await fetch('/processes', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    name: 'New Process',
    bpmn_xml: '<?xml version="1.0" encoding="UTF-8"?>...',
  }),
});

// Update process
const updatedProcess = await fetch(`/processes/${processId}`, {
  method: 'PUT',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    name: 'Updated Process',
  }),
});

// Delete process
await fetch(`/processes/${processId}`, {
  method: 'DELETE',
});
```

Using Python requests:
```python
import requests

# List processes
response = requests.get('/processes')
processes = response.json()['data']['items']

# Create process
response = requests.post('/processes', json={
    'name': 'New Process',
    'bpmn_xml': '<?xml version="1.0" encoding="UTF-8"?>...',
})
new_process = response.json()['data']

# Update process
response = requests.put(f'/processes/{process_id}', json={
    'name': 'Updated Process',
})
updated_process = response.json()['data']

# Delete process
response = requests.delete(f'/processes/{process_id}')
