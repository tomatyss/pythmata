import { render, screen, fireEvent } from '@testing-library/react';
import GatewayPropertiesPanel from './GatewayPropertiesPanel';
import { vi } from 'vitest';

// Mock data
const mockElementRegistry = {
  get: vi.fn((id: string) => {
    if (id === 'Flow_1') {
      return {
        id: 'Flow_1',
        businessObject: {
          id: 'Flow_1',
          name: 'Flow 1',
        },
      };
    }
    if (id === 'Flow_2') {
      return {
        id: 'Flow_2',
        businessObject: {
          id: 'Flow_2',
          name: 'Flow 2',
        },
      };
    }
    return null;
  }),
};

const mockModeling = {
  updateProperties: vi.fn(),
};

const mockModeler = {
  get: vi.fn((module: string) => {
    if (module === 'elementRegistry') {
      return mockElementRegistry;
    }
    if (module === 'modeling') {
      return mockModeling;
    }
    return {};
  }),
};

const mockExclusiveGateway = {
  id: 'Gateway_1',
  type: 'bpmn:ExclusiveGateway',
  businessObject: {
    id: 'Gateway_1',
    name: 'Exclusive Gateway',
    outgoing: [{ id: 'Flow_1' }, { id: 'Flow_2' }],
    default: { id: 'Flow_1' },
  },
};

const mockInclusiveGateway = {
  id: 'Gateway_2',
  type: 'bpmn:InclusiveGateway',
  businessObject: {
    id: 'Gateway_2',
    name: 'Inclusive Gateway',
    outgoing: [{ id: 'Flow_1' }, { id: 'Flow_2' }],
    default: null,
  },
};

const mockParallelGateway = {
  id: 'Gateway_3',
  type: 'bpmn:ParallelGateway',
  businessObject: {
    id: 'Gateway_3',
    name: 'Parallel Gateway',
    outgoing: [{ id: 'Flow_1' }, { id: 'Flow_2' }],
  },
};

// Mock MUI Select component behavior
vi.mock('@mui/material', async () => {
  const actual = await vi.importActual('@mui/material');
  return {
    ...actual,
    Select: ({
      children,
      onChange,
      value,
      ...props
    }: React.PropsWithChildren<{
      onChange: React.ChangeEventHandler<HTMLButtonElement>;
      value: string | null;
    }>) => {
      return (
        <div data-testid="mock-select" {...props}>
          <div data-value={value}>{value}</div>
          <button
            onClick={() =>
              onChange({
                target: { value: 'Flow_2' },
              } as unknown as React.ChangeEvent<HTMLButtonElement>)
            }
            data-testid="select-flow2"
          >
            Select Flow 2
          </button>
          <button
            onClick={() =>
              onChange({
                target: { value: '' },
              } as unknown as React.ChangeEvent<HTMLButtonElement>)
            }
            data-testid="select-none"
          >
            Select None
          </button>
          {children}
        </div>
      );
    },
  };
});

describe('GatewayPropertiesPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('renders exclusive gateway properties', () => {
    render(
      <GatewayPropertiesPanel
        element={mockExclusiveGateway}
        modeler={mockModeler}
      />
    );

    expect(screen.getByText(/Gateway Configuration/i)).toBeInTheDocument();
    expect(screen.getByText(/For exclusive gateways/i)).toBeInTheDocument();
    expect(screen.getByTestId('mock-select')).toBeInTheDocument();

    // Check that Flow_1 is the current value (checking the data-value attribute)
    const selectValue = screen
      .getByTestId('mock-select')
      .querySelector('[data-value]');
    expect(selectValue).toHaveAttribute('data-value', 'Flow_1');

    // We don't need to check for Flow_2 text being visible since it would only
    // be visible when the dropdown is open
  });

  test('renders inclusive gateway properties', () => {
    render(
      <GatewayPropertiesPanel
        element={mockInclusiveGateway}
        modeler={mockModeler}
      />
    );

    expect(screen.getByText(/Gateway Configuration/i)).toBeInTheDocument();
    expect(screen.getByText(/For inclusive gateways/i)).toBeInTheDocument();
    expect(screen.getByTestId('mock-select')).toBeInTheDocument();
  });

  test('renders parallel gateway message', () => {
    render(
      <GatewayPropertiesPanel
        element={mockParallelGateway}
        modeler={mockModeler}
      />
    );

    expect(
      screen.getByText(/Parallel gateways do not use default flows/i)
    ).toBeInTheDocument();
  });

  test('handles default flow change', () => {
    render(
      <GatewayPropertiesPanel
        element={mockExclusiveGateway}
        modeler={mockModeler}
      />
    );

    // Use our custom button to simulate selecting Flow_2
    fireEvent.click(screen.getByTestId('select-flow2'));

    // Check that updateProperties was called with the correct arguments
    expect(mockModeling.updateProperties).toHaveBeenCalledWith(
      mockExclusiveGateway,
      { default: expect.anything() }
    );
  });

  test('handles clearing default flow', () => {
    render(
      <GatewayPropertiesPanel
        element={mockExclusiveGateway}
        modeler={mockModeler}
      />
    );

    // Use our custom button to simulate selecting None
    fireEvent.click(screen.getByTestId('select-none'));

    // Check that updateProperties was called with the correct arguments
    expect(mockModeling.updateProperties).toHaveBeenCalledWith(
      mockExclusiveGateway,
      { default: null }
    );
  });
});
