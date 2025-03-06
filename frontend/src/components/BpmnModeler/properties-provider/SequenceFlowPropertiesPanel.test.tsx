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

  test('handles default flow checkbox', () => {
    render(
      <SequenceFlowPropertiesPanel
        element={mockElement}
        modeler={mockModeler}
        variables={mockVariables}
      />
    );

    // Mock elementRegistry.get before rendering the component
    const elementRegistry = mockModeler.get('elementRegistry');
    if (!elementRegistry?.get) {
      throw new Error('Element registry or its get method is undefined');
    }
    elementRegistry.get.mockReturnValue({
      type: 'bpmn:ExclusiveGateway',
      id: 'Gateway_1',
      businessObject: {
        id: 'Gateway_1',
        name: 'Test Gateway',
      },
    });

    render(
      <SequenceFlowPropertiesPanel
        element={mockElement}
        modeler={mockModeler}
        variables={mockVariables}
      />
    );

    const checkbox = screen.getByLabelText(/Use as default flow/i);

    // Verify sourceElement is correctly retrieved
    const sourceElement = elementRegistry?.get?.('Gateway_1') ?? null;
    expect(sourceElement).not.toBeNull();

    // Simulate checkbox click
    fireEvent.click(checkbox);

    // Verify updateProperties is called with the correct arguments
    expect(mockModeler.get('modeling').updateProperties).toHaveBeenCalledWith(
      sourceElement,
      { default: mockElement }
    );
  });
});
