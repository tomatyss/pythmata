/**
 * Utility functions for validating process variables
 */
import { ProcessVariableValue } from '@/types/process';

/**
 * Error thrown when a variable validation fails
 */
export class VariableValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'VariableValidationError';
  }
}

/**
 * Validates a single ProcessVariableValue to ensure it matches the expected schema
 *
 * @param name - The name of the variable (for error messages)
 * @param variable - The variable to validate
 * @throws VariableValidationError if validation fails
 */
export const validateVariable = (
  name: string,
  variable: ProcessVariableValue
): void => {
  // Check if variable has the required properties
  if (!variable || typeof variable !== 'object') {
    throw new VariableValidationError(
      `Variable "${name}" must be an object with type and value properties`
    );
  }

  if (!('type' in variable) || !('value' in variable)) {
    throw new VariableValidationError(
      `Variable "${name}" must have both type and value properties`
    );
  }

  // Validate type
  const validTypes = ['string', 'number', 'boolean', 'date'];
  if (!validTypes.includes(variable.type)) {
    throw new VariableValidationError(
      `Variable "${name}" has invalid type "${variable.type}". Valid types are: ${validTypes.join(
        ', '
      )}`
    );
  }

  // Validate value matches the declared type
  if (variable.value !== null) {
    switch (variable.type) {
      case 'string':
        if (typeof variable.value !== 'string') {
          throw new VariableValidationError(
            `Variable "${name}" has type "string" but value is not a string`
          );
        }
        break;
      case 'number':
        if (typeof variable.value !== 'number') {
          throw new VariableValidationError(
            `Variable "${name}" has type "number" but value is not a number`
          );
        }
        break;
      case 'boolean':
        if (typeof variable.value !== 'boolean') {
          throw new VariableValidationError(
            `Variable "${name}" has type "boolean" but value is not a boolean`
          );
        }
        break;
      case 'date':
        if (
          !(variable.value instanceof Date) &&
          typeof variable.value !== 'string'
        ) {
          throw new VariableValidationError(
            `Variable "${name}" has type "date" but value is not a Date object or ISO string`
          );
        }
        break;
    }
  }
};

/**
 * Validates a record of variables to ensure they match the expected schema
 *
 * @param variables - Record of variable name to ProcessVariableValue
 * @returns The validated variables (unchanged if valid)
 * @throws VariableValidationError if any variable fails validation
 */
export const validateVariables = (
  variables?: Record<string, ProcessVariableValue>
): Record<string, ProcessVariableValue> => {
  if (!variables) {
    return {};
  }

  // Validate each variable
  Object.entries(variables).forEach(([name, variable]) => {
    validateVariable(name, variable);
  });

  return variables;
};

/**
 * Converts frontend variable types to backend variable types
 * Frontend: 'string' | 'number' | 'boolean' | 'date'
 * Backend: 'string' | 'integer' | 'float' | 'boolean' | 'date' | 'json'
 *
 * @param type - Frontend variable type
 * @param value - The variable value (used to determine if number is integer or float)
 * @returns Backend variable type
 */
export const convertTypeToBackend = (
  type: string,
  value: number | string | boolean | Date | null
): string => {
  if (type === 'number') {
    // Check if the number is an integer
    return Number.isInteger(value) ? 'integer' : 'float';
  }
  return type;
};

/**
 * Prepares variables for sending to the backend by converting types
 *
 * @param variables - Record of variable name to ProcessVariableValue
 * @returns Variables with backend-compatible types
 */
export const prepareVariablesForBackend = (
  variables?: Record<string, ProcessVariableValue>
): Record<string, ProcessVariableValue> => {
  if (!variables) {
    return {};
  }

  // First validate the variables
  validateVariables(variables);

  // Convert types for backend
  const result: Record<string, ProcessVariableValue> = {};

  Object.entries(variables).forEach(([name, variable]) => {
    result[name] = {
      ...variable,
      type: convertTypeToBackend(variable.type, variable.value) as
        | 'string'
        | 'integer'
        | 'float'
        | 'boolean'
        | 'date'
        | 'json',
    };
  });

  return result;
};
