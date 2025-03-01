import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import '@testing-library/jest-dom';
import ElementPanel, { ExtendedBpmnModeler } from './ElementPanel';

// Mock the ElementPropertiesPanel component
vi.mock(
  '@/components/BpmnModeler/properties-provider/ElementPropertiesPanel',
  () => ({
    default: vi
      .fn()
      .mockImplementation(({ element }: { element: { type: string } }) => (
        <div data-testid="mock-element-properties-panel">
          Element Properties for {element.type}
        </div>
      )),
  })
);

// Mock modeler
const mockModeler = {
  get: vi.fn().mockImplementation((module: string) => {
    if (module === 'elementRegistry') {
      return {
        get: vi.fn().mockImplementation((id: string) => ({
          id,
          type: 'bpmn:ServiceTask',
          businessObject: {
            extensionElements: {
              values: [],
            },
          },
        })),
      };
    }
    return null;
  }),
  // Add required BpmnModeler properties to satisfy TypeScript
  importXML: vi.fn(),
  saveXML: vi.fn(),
  destroy: vi.fn(),
} as unknown as ExtendedBpmnModeler;

describe('ElementPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders element properties panel', async () => {
    render(
      <ElementPanel
        elementId="test-element"
        modeler={mockModeler}
        onClose={() => {}}
      />
    );

    // Check that the element properties panel is rendered
    expect(
      screen.getByTestId('mock-element-properties-panel')
    ).toBeInTheDocument();
    expect(
      screen.getByText('Element Properties for bpmn:ServiceTask')
    ).toBeInTheDocument();
  });

  it('displays element type in the header', () => {
    render(
      <ElementPanel
        elementId="test-element"
        modeler={mockModeler}
        onClose={() => {}}
      />
    );

    // Check that the element type is displayed in the header
    expect(screen.getByText('Service Task Properties')).toBeInTheDocument();
  });

  it('calls onClose when close button is clicked', () => {
    const onCloseMock = vi.fn();
    render(
      <ElementPanel
        elementId="test-element"
        modeler={mockModeler}
        onClose={onCloseMock}
      />
    );

    // Click the close button
    fireEvent.click(screen.getByRole('button', { name: /close/i }));

    // Check that onClose was called
    expect(onCloseMock).toHaveBeenCalled();
  });

  it('calls onClose when save button is clicked', () => {
    const onCloseMock = vi.fn();
    render(
      <ElementPanel
        elementId="test-element"
        modeler={mockModeler}
        onClose={onCloseMock}
      />
    );

    // Click the save button
    fireEvent.click(screen.getByRole('button', { name: /save/i }));

    // Check that onClose was called
    expect(onCloseMock).toHaveBeenCalled();
  });

  it('handles error when element is not found', () => {
    // Mock error case
    const errorModeler = {
      ...mockModeler,
      get: vi.fn().mockImplementation((module: string) => {
        if (module === 'elementRegistry') {
          return {
            get: vi.fn().mockReturnValue(null),
          };
        }
        return null;
      }),
    } as unknown as ExtendedBpmnModeler;

    render(
      <ElementPanel
        elementId="non-existent-element"
        modeler={errorModeler}
        onClose={() => {}}
      />
    );

    // Check that the error message is displayed
    expect(
      screen.getByText(/Element with ID non-existent-element not found/i)
    ).toBeInTheDocument();
  });

  it('formats element type name correctly', () => {
    // Mock a different element type
    const customModeler = {
      ...mockModeler,
      get: vi.fn().mockImplementation((module: string) => {
        if (module === 'elementRegistry') {
          return {
            get: vi.fn().mockReturnValue({
              id: 'test-element',
              type: 'bpmn:ExclusiveGateway',
              businessObject: {
                extensionElements: {
                  values: [],
                },
              },
            }),
          };
        }
        return null;
      }),
    } as unknown as ExtendedBpmnModeler;

    render(
      <ElementPanel
        elementId="test-element"
        modeler={customModeler}
        onClose={() => {}}
      />
    );

    // Check that the element type is formatted correctly
    expect(
      screen.getByText('Exclusive Gateway Properties')
    ).toBeInTheDocument();
  });
});
