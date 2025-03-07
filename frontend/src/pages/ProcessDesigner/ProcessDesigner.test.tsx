import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes, useNavigate } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import ProcessDesigner from './ProcessDesigner';
import apiService from '@/services/api';

// Define types for mocks
type MockFunction = ReturnType<typeof vi.fn>;
type MockBpmnModeler = {
  importXML: MockFunction;
  saveXML: MockFunction;
  destroy: MockFunction;
  get: MockFunction;
};

// Mock the API service
vi.mock('@/services/api', () => ({
  default: {
    getProcessDefinition: vi.fn(),
    createProcessDefinition: vi.fn(),
    updateProcessDefinition: vi.fn(),
  },
}));

// Mock react-router-dom
vi.mock('react-router-dom', async () => {
  const actual =
    await vi.importActual<typeof import('react-router-dom')>(
      'react-router-dom'
    );
  return {
    ...actual,
    useNavigate: vi.fn(),
  };
});

// Mock bpmn-js
vi.mock('bpmn-js/lib/Modeler', () => ({
  default: vi.fn().mockImplementation(() => {
    const eventCallbacks: Record<
      string,
      (payload: Record<string, unknown>) => void
    > = {};
    return {
      importXML: vi.fn().mockResolvedValue({}),
      saveXML: vi.fn().mockResolvedValue({ xml: '<mock-xml/>' }),
      destroy: vi.fn(),
      get: vi.fn().mockImplementation((module: string) => {
        if (module === 'eventBus') {
          return {
            on: vi.fn(
              (
                event: string,
                callback: (payload: Record<string, unknown>) => void
              ) => {
                eventCallbacks[event] = callback;
              }
            ),
            fire: vi.fn((event: string, payload: Record<string, unknown>) => {
              if (eventCallbacks[event]) {
                eventCallbacks[event](payload);
              }
            }),
          };
        }
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
    };
  }),
}));

// Mock ElementPanel component
vi.mock('@/components/shared/ElementPanel', () => ({
  default: vi
    .fn()
    .mockImplementation(() => <div data-testid="mock-element-panel" />),
}));

describe('ProcessDesigner', () => {
  const mockProcess = {
    id: '123',
    name: 'Test Process',
    bpmnXml: '<test-xml/>',
    version: 1,
    createdAt: '2024-02-06T00:00:00Z',
    updatedAt: '2024-02-06T00:00:00Z',
  };

  // Mock window.alert before all tests
  const mockAlert = vi.fn();
  const originalAlert = window.alert;

  beforeEach(() => {
    // Clear all mocks before each test
    vi.clearAllMocks();
    // Reset useNavigate mock and provide default implementation
    const mockNavigate = vi.fn();
    (useNavigate as MockFunction).mockReturnValue(mockNavigate);
    // Set up window.alert mock
    window.alert = mockAlert;
  });

  afterEach(() => {
    // Restore window.alert after each test
    window.alert = originalAlert;
  });

  it('loads existing process when editing', async () => {
    // Mock the API call
    (apiService.getProcessDefinition as MockFunction).mockResolvedValueOnce({
      data: mockProcess,
    });

    render(
      <MemoryRouter initialEntries={[`/processes/${mockProcess.id}`]}>
        <Routes>
          <Route path="/processes/:id" element={<ProcessDesigner />} />
          <Route path="*" element={<div>Not Found</div>} />
        </Routes>
      </MemoryRouter>
    );

    // Should show loading state initially
    expect(screen.getByRole('progressbar')).toBeInTheDocument();

    // Should load process data
    await waitFor(() => {
      expect(screen.getByDisplayValue(mockProcess.name)).toBeInTheDocument();
    });

    // Should have called the API
    expect(apiService.getProcessDefinition).toHaveBeenCalledWith(
      mockProcess.id
    );
  });

  it('shows error message when loading fails', async () => {
    // Mock API error
    (apiService.getProcessDefinition as MockFunction).mockRejectedValueOnce(
      new Error('Failed to load')
    );

    render(
      <MemoryRouter initialEntries={['/processes/123']}>
        <Routes>
          <Route path="/processes/:id" element={<ProcessDesigner />} />
          <Route path="*" element={<div>Not Found</div>} />
        </Routes>
      </MemoryRouter>
    );

    // Should show error message
    await waitFor(() => {
      expect(screen.getByText(/Failed to load process/i)).toBeInTheDocument();
    });
  });

  it('initializes with empty diagram for new process', async () => {
    const { default: BpmnModeler } = await import('bpmn-js/lib/Modeler');

    render(
      <MemoryRouter initialEntries={['/processes/new']}>
        <Routes>
          <Route path="/processes/new" element={<ProcessDesigner />} />
          <Route path="*" element={<div>Not Found</div>} />
        </Routes>
      </MemoryRouter>
    );

    // Should show "New Process" in the name field
    expect(screen.getByDisplayValue('New Process')).toBeInTheDocument();

    // Should initialize modeler with empty diagram
    await waitFor(() => {
      const modelerInstance = (BpmnModeler as MockFunction).mock.results[0]
        ?.value as MockBpmnModeler;
      expect(modelerInstance?.importXML).toHaveBeenCalledWith(
        expect.stringContaining('<bpmn:startEvent')
      );
    });
  });

  it('creates a new process successfully', async () => {
    const user = userEvent.setup();
    const newProcess = {
      ...mockProcess,
      name: 'New Test Process',
    };

    // Mock the API call
    (apiService.createProcessDefinition as MockFunction).mockResolvedValueOnce({
      data: newProcess,
    });

    render(
      <MemoryRouter initialEntries={['/processes/new']}>
        <Routes>
          <Route path="/processes/new" element={<ProcessDesigner />} />
          <Route path="*" element={<div>Not Found</div>} />
        </Routes>
      </MemoryRouter>
    );

    // Change process name
    const nameInput = screen.getByPlaceholderText('Process Name');
    await user.clear(nameInput);
    await user.type(nameInput, newProcess.name);

    // Click save button
    const saveButton = screen.getByRole('button', { name: /save/i });
    await user.click(saveButton);

    // Should have called create API with correct data
    expect(apiService.createProcessDefinition).toHaveBeenCalledWith(
      expect.objectContaining({
        name: newProcess.name,
        bpmnXml: expect.any(String),
        version: 1,
        variableDefinitions: [],
      })
    );
  });

  it('cleans up modeler on unmount', async () => {
    const { default: BpmnModeler } = await import('bpmn-js/lib/Modeler');
    const destroyMock = vi.fn();

    // Setup modeler mock with destroy function
    (BpmnModeler as MockFunction).mockImplementation(() => ({
      importXML: vi.fn().mockResolvedValue({}),
      saveXML: vi.fn().mockResolvedValue({ xml: '<mock-xml/>' }),
      destroy: destroyMock,
    }));

    // Mock the API call
    (apiService.getProcessDefinition as MockFunction).mockResolvedValueOnce({
      data: mockProcess,
    });

    const { unmount } = render(
      <MemoryRouter initialEntries={[`/processes/${mockProcess.id}`]}>
        <Routes>
          <Route path="/processes/:id" element={<ProcessDesigner />} />
          <Route path="*" element={<div>Not Found</div>} />
          <Route path="/processes" element={<div>Process List</div>} />
        </Routes>
      </MemoryRouter>
    );

    // Wait for initial load and modeler initialization
    await waitFor(() => {
      expect(BpmnModeler).toHaveBeenCalled();
    });

    // Unmount component to trigger cleanup
    unmount();

    // Verify modeler was destroyed
    expect(destroyMock).toHaveBeenCalled();
  });

  it('handles navigation after save', async () => {
    const user = userEvent.setup();
    const mockNavigate = vi.fn();
    (useNavigate as MockFunction).mockReturnValue(mockNavigate);

    // Mock the API calls
    (apiService.getProcessDefinition as MockFunction).mockResolvedValueOnce({
      data: mockProcess,
    });
    (apiService.updateProcessDefinition as MockFunction).mockResolvedValueOnce({
      data: mockProcess,
    });

    render(
      <MemoryRouter initialEntries={[`/processes/${mockProcess.id}`]}>
        <Routes>
          <Route path="/processes/:id" element={<ProcessDesigner />} />
          <Route path="/processes" element={<div>Process List</div>} />
          <Route path="*" element={<div>Not Found</div>} />
        </Routes>
      </MemoryRouter>
    );

    // Wait for process to load
    await waitFor(() => {
      expect(screen.getByDisplayValue(mockProcess.name)).toBeInTheDocument();
    });

    // Click save button
    const saveButton = screen.getByRole('button', { name: /save/i });
    await user.click(saveButton);

    // Verify navigation
    expect(mockNavigate).toHaveBeenCalledWith('/processes');
  });

  it('saves process changes', async () => {
    const user = userEvent.setup();

    // Mock the API calls
    (apiService.getProcessDefinition as MockFunction).mockResolvedValueOnce({
      data: mockProcess,
    });
    (apiService.updateProcessDefinition as MockFunction).mockResolvedValueOnce({
      data: mockProcess,
    });

    render(
      <MemoryRouter initialEntries={[`/processes/${mockProcess.id}`]}>
        <Routes>
          <Route path="/processes/:id" element={<ProcessDesigner />} />
        </Routes>
      </MemoryRouter>
    );

    // Wait for process to load
    await waitFor(() => {
      expect(screen.getByDisplayValue(mockProcess.name)).toBeInTheDocument();
    });

    // Click save button
    const saveButton = screen.getByRole('button', { name: /save/i });
    await user.click(saveButton);

    // Should have called the update API
    expect(apiService.updateProcessDefinition).toHaveBeenCalledWith(
      mockProcess.id,
      expect.objectContaining({
        name: mockProcess.name,
        bpmnXml: expect.any(String),
        variableDefinitions: [],
      })
    );
  });

  it('shows error when save fails', async () => {
    const user = userEvent.setup();
    const mockError = new Error('Save failed');

    // Mock the API calls
    (apiService.getProcessDefinition as MockFunction).mockResolvedValueOnce({
      data: mockProcess,
    });
    (apiService.updateProcessDefinition as MockFunction).mockRejectedValueOnce(
      mockError
    );

    render(
      <MemoryRouter initialEntries={[`/processes/${mockProcess.id}`]}>
        <Routes>
          <Route path="/processes/:id" element={<ProcessDesigner />} />
        </Routes>
      </MemoryRouter>
    );

    // Wait for process to load
    await waitFor(() => {
      expect(screen.getByDisplayValue(mockProcess.name)).toBeInTheDocument();
    });

    // Click save button
    const saveButton = screen.getByRole('button', { name: /save/i });
    await user.click(saveButton);

    // Wait for and verify error alert
    await waitFor(() => {
      expect(mockAlert).toHaveBeenCalledWith(
        expect.stringContaining('Failed to save process')
      );
    });
  });

  it('opens element panel on double-click', async () => {
    // Create a mock with the event bus
    const eventCallbacks: Record<
      string,
      (payload: Record<string, unknown>) => void
    > = {};
    const eventBusMock = {
      on: vi.fn(
        (
          event: string,
          callback: (payload: Record<string, unknown>) => void
        ) => {
          eventCallbacks[event] = callback;
        }
      ),
      fire: vi.fn((event: string, payload: Record<string, unknown>) => {
        if (eventCallbacks[event]) {
          eventCallbacks[event](payload);
        }
      }),
    };

    // Override the BpmnModeler mock for this test
    const { default: BpmnModeler } = await import('bpmn-js/lib/Modeler');
    (BpmnModeler as MockFunction).mockImplementation(() => ({
      importXML: vi.fn().mockResolvedValue({}),
      saveXML: vi.fn().mockResolvedValue({ xml: '<mock-xml/>' }),
      destroy: vi.fn(),
      get: vi.fn().mockImplementation((module: string) => {
        if (module === 'eventBus') return eventBusMock;
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
    }));

    // Mock the API call
    (apiService.getProcessDefinition as MockFunction).mockResolvedValueOnce({
      data: mockProcess,
    });

    render(
      <MemoryRouter initialEntries={[`/processes/${mockProcess.id}`]}>
        <Routes>
          <Route path="/processes/:id" element={<ProcessDesigner />} />
        </Routes>
      </MemoryRouter>
    );

    // Wait for process to load
    await waitFor(() => {
      expect(screen.getByDisplayValue(mockProcess.name)).toBeInTheDocument();
    });

    // Wait for the event listeners to be registered
    await waitFor(() => {
      expect(eventBusMock.on).toHaveBeenCalledWith(
        'element.dblclick',
        expect.any(Function)
      );
    });

    // Simulate double-click on an element
    const callback = eventCallbacks['element.dblclick'];
    if (callback) {
      callback({ element: { id: 'test-element', type: 'bpmn:ServiceTask' } });
    } else {
      throw new Error('element.dblclick callback not registered');
    }

    // Check that the element panel is opened
    await waitFor(() => {
      expect(screen.getByTestId('mock-element-panel')).toBeInTheDocument();
    });
  });
});
