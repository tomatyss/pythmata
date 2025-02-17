import { snakeToCamel, convertKeysToCamel } from '../case';

describe('snakeToCamel', () => {
  it('converts snake_case to camelCase', () => {
    expect(snakeToCamel('hello_world')).toBe('helloWorld');
    expect(snakeToCamel('first_name')).toBe('firstName');
    expect(snakeToCamel('user_id_number')).toBe('userIdNumber');
  });

  it('handles single word correctly', () => {
    expect(snakeToCamel('hello')).toBe('hello');
    expect(snakeToCamel('test')).toBe('test');
  });

  it('preserves existing camelCase', () => {
    expect(snakeToCamel('helloWorld')).toBe('helloWorld');
    expect(snakeToCamel('firstName')).toBe('firstName');
  });
});

describe('convertKeysToCamel', () => {
  it('converts object keys from snake_case to camelCase', () => {
    const input = {
      first_name: 'John',
      last_name: 'Doe',
      user_details: {
        email_address: 'john@example.com',
        phone_number: '123-456-7890',
      },
    };

    const expected = {
      firstName: 'John',
      lastName: 'Doe',
      userDetails: {
        emailAddress: 'john@example.com',
        phoneNumber: '123-456-7890',
      },
    };

    expect(convertKeysToCamel(input)).toEqual(expected);
  });

  it('handles arrays of objects', () => {
    const input = [
      { user_id: 1, first_name: 'John' },
      { user_id: 2, first_name: 'Jane' },
    ];

    const expected = [
      { userId: 1, firstName: 'John' },
      { userId: 2, firstName: 'Jane' },
    ];

    expect(convertKeysToCamel(input)).toEqual(expected);
  });

  it('handles nested arrays', () => {
    const input = {
      user_list: [{ user_id: 1, address_list: [{ street_name: 'Main St' }] }],
    };

    const expected = {
      userList: [{ userId: 1, addressList: [{ streetName: 'Main St' }] }],
    };

    expect(convertKeysToCamel(input)).toEqual(expected);
  });

  it('preserves non-object values', () => {
    const input = {
      string_value: 'test',
      number_value: 123,
      boolean_value: true,
      null_value: null,
      undefined_value: undefined,
    };

    const expected = {
      stringValue: 'test',
      numberValue: 123,
      booleanValue: true,
      nullValue: null,
      undefinedValue: undefined,
    };

    expect(convertKeysToCamel(input)).toEqual(expected);
  });

  it('handles empty objects and arrays', () => {
    const input = {
      empty_object: {},
      empty_array: [],
    };

    const expected = {
      emptyObject: {},
      emptyArray: [],
    };

    expect(convertKeysToCamel(input)).toEqual(expected);
  });

  it('preserves Date objects', () => {
    const date = new Date();
    const input = {
      created_at: date,
    };

    const expected = {
      createdAt: date,
    };

    expect(convertKeysToCamel(input)).toEqual(expected);
  });

  it('handles real API response example', () => {
    const input = {
      definition_id: '123',
      definition_name: 'Process 1',
      status: 'RUNNING',
      start_time: '2024-02-15T12:00:00Z',
      end_time: null,
      bpmn_xml: '<xml>...</xml>',
      active_instances: 5,
      total_instances: 10,
      variable_definitions: [
        {
          name: 'var1',
          type: 'string',
          required: true,
          default_value: 'test',
        },
      ],
    };

    const expected = {
      definitionId: '123',
      definitionName: 'Process 1',
      status: 'RUNNING',
      startTime: '2024-02-15T12:00:00Z',
      endTime: null,
      bpmnXml: '<xml>...</xml>',
      activeInstances: 5,
      totalInstances: 10,
      variableDefinitions: [
        {
          name: 'var1',
          type: 'string',
          required: true,
          defaultValue: 'test',
        },
      ],
    };

    expect(convertKeysToCamel(input)).toEqual(expected);
  });
});
