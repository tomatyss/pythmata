# Process Variables

Process variables are key-value pairs that can be used to store and manipulate data within a process instance. This document explains how variables are defined, validated, and used in the system.

## Variable Types

The system supports the following variable types:

| Frontend Type | Backend Type | Description |
|---------------|--------------|-------------|
| `string`      | `string`     | Text values |
| `number`      | `integer` or `float` | Numeric values (automatically converted to the appropriate backend type) |
| `boolean`     | `boolean`    | Boolean values (true/false) |
| `date`        | `date`       | Date and time values |
| -             | `json`       | JSON objects or arrays (backend only) |

## Variable Definitions

Variable definitions are used to define the structure and validation rules for process variables. They are defined in the process definition and are used to validate variables when starting a process instance.

```typescript
interface ProcessVariableDefinition {
  name: string;                 // Variable name
  type: 'string' | 'number' | 'boolean' | 'date';  // Variable type
  required: boolean;            // Whether the variable is required
  defaultValue?: any;           // Default value if not provided
  validation?: {                // Validation rules
    min?: number;               // Minimum value (for numbers)
    max?: number;               // Maximum value (for numbers)
    pattern?: string;           // Regex pattern (for strings)
    options?: any[];            // Allowed values
  };
  label: string;                // Display label
  description?: string;         // Description
}
```

## Variable Values

Variable values are used to store the actual data for a variable. They consist of a type and a value.

```typescript
interface ProcessVariableValue {
  type: 'string' | 'number' | 'boolean' | 'date';  // Variable type
  value: string | number | boolean | Date | null;  // Variable value
}
```

## Validation

Variables are validated before being sent to the backend to ensure they match the expected format and type. The validation process checks:

1. **Type Validation**: Ensures the variable's value matches its declared type.
2. **Required Fields**: Ensures all required variables are provided.
3. **Validation Rules**: Applies any validation rules defined in the variable definition.

### Using the Validation Utility

The `validateVariables` utility can be used to validate variables before sending them to the backend:

```typescript
import { validateVariables, VariableValidationError } from '@/utils/validateVariables';

try {
  // Validate variables
  const validatedVariables = validateVariables(variables);
  
  // Use validated variables
  // ...
} catch (error) {
  if (error instanceof VariableValidationError) {
    // Handle validation error
    console.error(`Validation error: ${error.message}`);
  }
}
```

### Preparing Variables for Backend

The `prepareVariablesForBackend` utility can be used to convert frontend variable types to backend types:

```typescript
import { prepareVariablesForBackend } from '@/utils/validateVariables';

// Convert frontend types to backend types
const backendVariables = prepareVariablesForBackend(variables);

// Send to backend
await apiService.startProcessInstance({
  definitionId,
  variables: backendVariables,
});
```

## Best Practices

1. **Always Validate Variables**: Always validate variables before sending them to the backend to ensure they match the expected format and type.
2. **Use Type Conversion**: Use the `prepareVariablesForBackend` utility to convert frontend types to backend types.
3. **Handle Validation Errors**: Catch and handle validation errors to provide meaningful feedback to the user.
4. **Use Default Values**: Provide default values for variables when appropriate to simplify the user experience.
5. **Document Variable Definitions**: Document the purpose and expected format of each variable to help users understand how to use them.
