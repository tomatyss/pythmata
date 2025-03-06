/**
 * Utility functions for converting between frontend and backend variable types
 */
import { ProcessVariableDefinition } from '@/types/process';

/**
 * Convert frontend variable type to backend variable type
 * Frontend: 'string' | 'number' | 'boolean' | 'date'
 * Backend: 'string' | 'integer' | 'float' | 'boolean' | 'date' | 'json'
 *
 * @param type - Frontend variable type
 * @param value - The variable value (used to determine if number is integer or float)
 * @returns Backend variable type
 */
export const convertTypeToBackend = (
  type: string,
  value?: number | string | boolean | Date | null
): 'string' | 'number' | 'boolean' | 'date' => {
  if (type === 'number') {
    // If value is provided, check if it's an integer
    if (value !== undefined && value !== null) {
      return 'number';
    }
    // Default to 'number' if no value is provided
    return 'number';
  }
  if (type === 'string' || type === 'boolean' || type === 'date') {
    return type;
  }
  return 'number'; // Default to 'number' for unsupported types
};

/**
 * Convert a ProcessVariableDefinition from frontend format to backend format
 *
 * @param definition - Frontend variable definition
 * @returns Backend-compatible variable definition
 */
export const convertDefinitionToBackend = (
  definition: ProcessVariableDefinition
): Record<string, unknown> => {
  const backendType = convertTypeToBackend(
    definition.type,
    definition.defaultValue
  );

  return {
    ...definition,
    type: backendType,
    // Convert camelCase to snake_case for backend
    default_value: definition.defaultValue,
    // Remove frontend-only properties
    defaultValue: undefined,
  };
};

/**
 * Convert an array of ProcessVariableDefinitions from frontend format to backend format
 *
 * @param definitions - Array of frontend variable definitions
 * @returns Array of backend-compatible variable definitions
 */
export const convertDefinitionsToBackend = (
  definitions: ProcessVariableDefinition[]
): ProcessVariableDefinition[] => {
  return definitions.map((definition) => ({
    ...definition,
    type: convertTypeToBackend(definition.type, definition.defaultValue),
    defaultValue: definition.defaultValue,
  }));
};
