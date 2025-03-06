import {
  validateVariable,
  validateVariables,
  prepareVariablesForBackend,
  VariableValidationError,
  convertTypeToBackend,
} from '../validateVariables';
import { ProcessVariableValue } from '@/types/process';

describe('validateVariable', () => {
  it('should validate a string variable', () => {
    const variable: ProcessVariableValue = {
      type: 'string',
      value: 'test',
    };
    expect(() => validateVariable('test', variable)).not.toThrow();
  });

  it('should validate a number variable', () => {
    const variable: ProcessVariableValue = {
      type: 'number',
      value: 42,
    };
    expect(() => validateVariable('test', variable)).not.toThrow();
  });

  it('should validate a boolean variable', () => {
    const variable: ProcessVariableValue = {
      type: 'boolean',
      value: true,
    };
    expect(() => validateVariable('test', variable)).not.toThrow();
  });

  it('should validate a date variable', () => {
    const variable: ProcessVariableValue = {
      type: 'date',
      value: new Date(),
    };
    expect(() => validateVariable('test', variable)).not.toThrow();
  });

  it('should throw for missing type', () => {
    const variable = {
      value: 'test',
    } as { value: string; type: 'string' };
    expect(() => validateVariable('test', variable)).toThrow(
      VariableValidationError
    );
  });

  it('should throw for missing value', () => {
    const variable = {
      type: 'string',
    } as { type: 'string'; value: null };
    expect(() => validateVariable('test', variable)).toThrow(
      VariableValidationError
    );
  });

  it('should throw for invalid type', () => {
    const variable = {
      type: 'invalid',
      value: 'test',
    } as { type: 'invalid'; value: string } as unknown as ProcessVariableValue;
    expect(() => validateVariable('test', variable)).toThrow(
      VariableValidationError
    );
  });

  it('should throw for mismatched type and value (string)', () => {
    const variable: ProcessVariableValue = {
      type: 'string',
      value: 42 as number,
    };
    expect(() => validateVariable('test', variable)).toThrow(
      VariableValidationError
    );
  });

  it('should throw for mismatched type and value (number)', () => {
    const variable: ProcessVariableValue = {
      type: 'number',
      value: 'test' as string,
    };
    expect(() => validateVariable('test', variable)).toThrow(
      VariableValidationError
    );
  });

  it('should throw for mismatched type and value (boolean)', () => {
    const variable: ProcessVariableValue = {
      type: 'boolean',
      value: 'test' as string,
    };
    expect(() => validateVariable('test', variable)).toThrow(
      VariableValidationError
    );
  });

  it('should throw for mismatched type and value (date)', () => {
    const variable: ProcessVariableValue = {
      type: 'date',
      value: 42 as number,
    };
    expect(() => validateVariable('test', variable)).toThrow(
      VariableValidationError
    );
  });
});

describe('validateVariables', () => {
  it('should return empty object for undefined variables', () => {
    expect(validateVariables()).toEqual({});
  });

  it('should validate multiple variables', () => {
    const variables: Record<string, ProcessVariableValue> = {
      string: {
        type: 'string',
        value: 'test',
      },
      number: {
        type: 'number',
        value: 42,
      },
      boolean: {
        type: 'boolean',
        value: true,
      },
      date: {
        type: 'date',
        value: new Date(),
      },
    };
    expect(() => validateVariables(variables)).not.toThrow();
  });

  it('should throw for invalid variables', () => {
    const variables: Record<string, ProcessVariableValue> = {
      string: {
        type: 'string',
        value: 'test',
      },
      invalid: {
        type: 'number',
        value: 'test' as string,
      },
    };
    expect(() => validateVariables(variables)).toThrow(VariableValidationError);
  });
});

describe('convertTypeToBackend', () => {
  it('should convert number to integer for integer values', () => {
    expect(convertTypeToBackend('number', 42)).toBe('integer');
  });

  it('should convert number to float for float values', () => {
    expect(convertTypeToBackend('number', 42.5)).toBe('float');
  });

  it('should pass through other types', () => {
    expect(convertTypeToBackend('string', 'test')).toBe('string');
    expect(convertTypeToBackend('boolean', true)).toBe('boolean');
    expect(convertTypeToBackend('date', new Date())).toBe('date');
  });
});

describe('prepareVariablesForBackend', () => {
  it('should return empty object for undefined variables', () => {
    expect(prepareVariablesForBackend()).toEqual({});
  });

  it('should convert types for backend', () => {
    const variables: Record<string, ProcessVariableValue> = {
      string: {
        type: 'string',
        value: 'test',
      },
      integer: {
        type: 'number',
        value: 42,
      },
      float: {
        type: 'number',
        value: 42.5,
      },
      boolean: {
        type: 'boolean',
        value: true,
      },
      date: {
        type: 'date',
        value: new Date(),
      },
    };

    const result = prepareVariablesForBackend(variables);

    // Use type assertion to avoid TypeScript errors
    expect(result['string']?.type).toBe('string');
    expect(result['integer']?.type).toBe('integer');
    expect(result['float']?.type).toBe('float');
    expect(result['boolean']?.type).toBe('boolean');
    expect(result['date']?.type).toBe('date');
  });

  it('should throw for invalid variables', () => {
    const variables: Record<string, ProcessVariableValue> = {
      string: {
        type: 'string',
        value: 42 as number,
      },
    };
    expect(() => prepareVariablesForBackend(variables)).toThrow(
      VariableValidationError
    );
  });
});
