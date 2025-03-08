import { render, screen, fireEvent } from '@testing-library/react';
import SequenceFlowPropertiesPanel from './SequenceFlowPropertiesPanel';

// Mock data
import { vi } from 'vitest';

const mockModeler = {
  get: vi.fn((module: string) => {
    if (module === 'elementRegistry') {
      return {
        get: vi.fn((id: string) => {
          if (id === 'Gateway_1') {
            return {
              type: 'bpmn:ExclusiveGateway',
              id: 'Gateway_1',
              businessObject: {
                id: 'Gateway_1',
                name: 'Test Gateway',
              },
            };
          }
          return null;
        }),
      };
    }
    if (module === 'modeling') {
      return {
        updateProperties: vi.fn(),
      };
    }
    if (module === 'moddle') {
      return {
        create: vi.fn((type: string, props: Record<string, unknown>) => ({
          ...props,
          $type: type,
        })),
      };
    }
    return {};
  }),
};

const mockElement = {
  id: 'Flow_1',
  type: 'bpmn:SequenceFlow',
  businessObject: {
    id: 'Flow_1',
    sourceRef: {
      id: 'Gateway_1',
      default: null,
    },
    targetRef: {
      id: 'Task_1',
    },
    conditionExpression: null,
  },
};

const mockElementWithCondition = {
  id: 'Flow_1',
  type: 'bpmn:SequenceFlow',
  businessObject: {
    id: 'Flow_1',
    sourceRef: {
      id: 'Gateway_1',
      default: null,
    },
    targetRef: {
      id: 'Task_1',
    },
    conditionExpression: {
      body: '${amount > 1000}',
      language: 'javascript',
    },
  },
};

const mockVariables = [
  { name: 'amount', type: 'number' },
  { name: 'status', type: 'string' },
];

describe('SequenceFlowPropertiesPanel', () => {
  test('renders message when source is not a gateway', () => {
    const nonGatewayElement = {
      ...mockElement,
      businessObject: {
        ...mockElement.businessObject,
        sourceRef: {
          id: 'Task_1',
        },
      },
    };

    render(
      <SequenceFlowPropertiesPanel
        element={nonGatewayElement}
        modeler={mockModeler}
        variables={mockVariables}
      />
    );

    expect(
      screen.getByText(
        /Conditions can only be set on sequence flows from gateways/i
      )
    ).toBeInTheDocument();
  });

  test('renders condition editor for exclusive gateway', () => {
    render(
      <SequenceFlowPropertiesPanel
        element={mockElement}
        modeler={mockModeler}
        variables={mockVariables}
      />
    );

    expect(screen.getByText(/Flow Condition/i)).toBeInTheDocument();
    expect(screen.getByText(/For exclusive gateways/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Condition Expression/i)).toBeInTheDocument();
    expect(screen.getByText(/Use as default flow/i)).toBeInTheDocument();
  });

  test('loads existing condition expression', () => {
    render(
      <SequenceFlowPropertiesPanel
        element={mockElementWithCondition}
        modeler={mockModeler}
        variables={mockVariables}
      />
    );

    expect(screen.getByLabelText(/Condition Expression/i)).toHaveValue(
      '${amount > 1000}'
    );
  });

  test('shows available variables', () => {
    render(
      <SequenceFlowPropertiesPanel
        element={mockElement}
        modeler={mockModeler}
        variables={mockVariables}
      />
    );

    expect(screen.getByText(/Available Variables/i)).toBeInTheDocument();
    expect(screen.getByText('amount')).toBeInTheDocument();
    expect(screen.getByText('status')).toBeInTheDocument();
  });

  test('shows message when no variables are defined', () => {
    render(
      <SequenceFlowPropertiesPanel
        element={mockElement}
        modeler={mockModeler}
        variables={[]}
      />
    );

    expect(screen.getByText(/No variables defined/i)).toBeInTheDocument();
  });

  test('validates expression format', () => {
    render(
      <SequenceFlowPropertiesPanel
        element={mockElement}
        modeler={mockModeler}
        variables={mockVariables}
      />
    );

    const input = screen.getByLabelText(/Condition Expression/i);
    fireEvent.change(input, { target: { value: 'invalid expression' } });
    fireEvent.blur(input);

    const alert = screen.getByRole('alert');
    expect(alert).toHaveTextContent("Expression must be wrapped in '${...}'");
  });

  test('handles variable references in expressions without errors', () => {
    render(
      <SequenceFlowPropertiesPanel
        element={mockElement}
        modeler={mockModeler}
        variables={mockVariables}
      />
    );

    // Find the variable chip and click it
    const amountChip = screen.getByText('amount');
    fireEvent.click(amountChip);

    // The expression should be updated without errors
    const input = screen.getByLabelText(/Condition Expression/i);
    expect(input).toHaveValue('${amount}');

    // Now add an operator and another variable
    const greaterThanChip = screen.getByText('>');
    fireEvent.click(greaterThanChip);

    // Expression should be updated with the operator
    expect(input).toHaveValue('${amount >}');

    // Manually change to a complete expression
    fireEvent.change(input, { target: { value: '${amount > 1000}' } });
    fireEvent.blur(input);

    // Should not show any validation errors
    expect(screen.queryByText(/Syntax error/i)).not.toBeInTheDocument();
  });

  test('handles default flow checkbox', async () => {
    // Reset mocks before the test
    vi.clearAllMocks();

    // Mock the modeling service with a spy function
    const updatePropertiesMock = vi.fn();
    const mockModelingService = {
      updateProperties: updatePropertiesMock,
    };

    // Mock the element registry service
    const gatewayElement = {
      type: 'bpmn:ExclusiveGateway',
      id: 'Gateway_1',
      businessObject: {
        id: 'Gateway_1',
        name: 'Test Gateway',
      },
    };

    const mockElementRegistryService = {
      get: vi.fn().mockImplementation((id) => {
        if (id === 'Gateway_1') {
          return gatewayElement;
        }
        return null;
      }),
    };

    // Create a customized mock modeler for this specific test
    const testModeler = {
      get: vi.fn().mockImplementation((service) => {
        if (service === 'elementRegistry') {
          return mockElementRegistryService;
        }
        if (service === 'modeling') {
          return mockModelingService;
        }
        if (service === 'moddle') {
          return mockModeler.get('moddle');
        }
        return {};
      }),
    };

    // Render the component with our test-specific mocks
    render(
      <SequenceFlowPropertiesPanel
        element={mockElement}
        modeler={testModeler}
        variables={mockVariables}
      />
    );

    // Get the checkbox element and verify it exists
    const checkbox = screen.getByLabelText(/Use as default flow/i, {
      selector: 'input#default-flow-checkbox-Flow_1',
    });
    expect(checkbox).toBeInTheDocument();

    // Simulate checkbox click - use fireEvent.change which might be more reliable
    // for checkbox inputs in some React testing scenarios
    fireEvent.click(checkbox);

    // Wait a bit for React state updates to process
    await vi.waitFor(() => {
      // Verify updateProperties was called with correct arguments
      expect(updatePropertiesMock).toHaveBeenCalledWith(gatewayElement, {
        default: mockElement,
      });
    });
  });
});
