import { render, screen, fireEvent } from '@testing-library/react';
import GatewayPropertiesPanel from './GatewayPropertiesPanel';

// Mock data
const mockModeler = {
  get: jest.fn((module) => {
    if (module === 'elementRegistry') {
      return {
        get: jest.fn((id) => {
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
    }
    if (module === 'modeling') {
      return {
        updateProperties: jest.fn(),
      };
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

describe('GatewayPropertiesPanel', () => {
  test('renders exclusive gateway properties', () => {
    render(
      <GatewayPropertiesPanel
        element={mockExclusiveGateway}
        modeler={mockModeler}
      />
    );

    expect(screen.getByText(/Gateway Configuration/i)).toBeInTheDocument();
    expect(screen.getByText(/For exclusive gateways/i)).toBeInTheDocument();
    expect(screen.getByText(/Default Flow/i)).toBeInTheDocument();
    expect(screen.getByText(/Flow 1/i)).toBeInTheDocument();
    expect(screen.getByText(/Flow 2/i)).toBeInTheDocument();
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
    expect(screen.getByText(/Default Flow/i)).toBeInTheDocument();
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

    const select = screen.getByLabelText(/Default Flow/i);
    fireEvent.change(select, { target: { value: 'Flow_2' } });

    expect(mockModeler.get('modeling').updateProperties).toHaveBeenCalledWith(
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

    const select = screen.getByLabelText(/Default Flow/i);
    fireEvent.change(select, { target: { value: '' } });

    expect(mockModeler.get('modeling').updateProperties).toHaveBeenCalledWith(
      mockExclusiveGateway,
      { default: null }
    );
  });
});
