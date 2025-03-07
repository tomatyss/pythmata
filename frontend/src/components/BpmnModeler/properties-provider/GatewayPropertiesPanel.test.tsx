import { render, screen, fireEvent } from '@testing-library/react';
import GatewayPropertiesPanel from './GatewayPropertiesPanel';
import { vi } from 'vitest';

// Mock data
const mockModeler = {
  get: vi.fn((module: string) => {
    if (module === 'elementRegistry') {
      return {
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
        updateProperties: vi.fn(),
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
    expect(screen.getByLabelText(/Default Flow/i)).toBeInTheDocument();
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
    expect(screen.getByLabelText(/Default Flow/i)).toBeInTheDocument();
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
    fireEvent.mouseDown(select, { container: document.body }); // Open the dropdown
    const option = screen.getByText((content, _element) =>
      content.includes('Flow 2')
    );
    fireEvent.click(option, { container: document.body }); // Select an option
    const elementRegistry = mockModeler.get('elementRegistry');
    const modeling = mockModeler.get('modeling');
    if (!elementRegistry?.get) {
      throw new Error(
        'MockModeler.get("elementRegistry") returned undefined or invalid'
      );
    }
    if (!modeling?.updateProperties) {
      throw new Error(
        'MockModeler.get("modeling") returned undefined or invalid'
      );
    }
    const updatePropertiesSpy = modeling.updateProperties;
    console.warn('Spy calls:', updatePropertiesSpy.mock.calls);
    expect(updatePropertiesSpy).toHaveBeenCalledWith(mockExclusiveGateway, {
      default: expect.anything(),
    });
  });

  test('handles clearing default flow', () => {
    render(
      <GatewayPropertiesPanel
        element={mockExclusiveGateway}
        modeler={mockModeler}
      />
    );

    const select = screen.getByLabelText(/Default Flow/i);
    fireEvent.mouseDown(select); // Open the dropdown
    const noneOption = screen.getByText((content, _element) =>
      content.includes('None')
    );
    fireEvent.click(noneOption, { container: document.body }); // Select "None"
    const modeling = mockModeler.get('modeling');
    if (!modeling?.updateProperties) {
      throw new Error(
        'MockModeler.get("modeling") returned undefined or invalid'
      );
    }
    const updatePropertiesSpy = modeling.updateProperties;
    console.warn('Spy calls:', updatePropertiesSpy.mock.calls);
    expect(updatePropertiesSpy).toHaveBeenCalledWith(mockExclusiveGateway, {
      default: null,
    });
  });
});
