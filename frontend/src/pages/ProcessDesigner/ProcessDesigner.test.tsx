import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes, useNavigate } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import ProcessDesigner from './ProcessDesigner';
import apiService from '@/services/api';
import { act } from 'react-dom/test-utils';

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

// Improved mock for bpmn-js
vi.mock('bpmn-js/lib/Modeler', () => ({
  default: vi.fn().mockImplementation(() => {
    const eventCallbacks: Record<
      string,
      (payload: Record<string, unknown>) => void
    > = {};

    // Mock elements for validation
    const mockElements = [
      { id: 'StartEvent_1', type: 'bpmn:StartEvent' },
      { id: 'EndEvent_1', type: 'bpmn:EndEvent' },
      {
        id: 'ServiceTask_1',
        type: 'bpmn:ServiceTask',
        businessObject: {
          extensionElements: {
            values: [
              { $type: 'pythmata:ServiceTaskConfig', taskName: 'mockTask' },
            ],
          },
        },
      },
    ];

    return {
      importXML: vi.fn().mockResolvedValue({ warnings: [] }),
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
            // Implement filter method to support validation rules
            filter: vi.fn((filterFn) => {
              return mockElements.filter(filterFn);
            }),
            get: vi.fn().mockImplementation((id: string) => {
              return mockElements.find((el) => el.id === id) || null;
            }),
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

// Mock VariableDefinitionsPanel component
vi.mock(
  '@/components/shared/VariableDefinitionsPanel/VariableDefinitionsPanel',
  () => ({
    default: vi
      .fn()
      .mockImplementation(() => <div data-testid="mock-variable-panel" />),
  })
);

// Mock ChatPanel component
vi.mock('@/components/shared/ChatPanel', () => ({
  default: vi
    .fn()
    .mockImplementation(() => <div data-testid="mock-chat-panel" />),
}));

// Mock MonacoEditor
vi.mock('@monaco-editor/react', () => ({
  default: vi
    .fn()
    .mockImplementation(({ value, onChange }) => (
      <textarea
        data-testid="monaco-editor"
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
      />
    )),
}));

describe('ProcessDesigner', () => {
  const mockProcess = {
    id: '123',
    name: 'Test Process',
    bpmnXml: '<test-xml/>',
    version: 1,
    createdAt: '2024-02-06T00:00:00Z',
    updatedAt: '2024-02-06T00:00:00Z',
    variableDefinitions: [],
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
    await waitFor(() => {
      expect(screen.getByDisplayValue('New Process')).toBeInTheDocument();
    });

    // Should initialize modeler with empty diagram
    await waitFor(() => {
      const modelerInstance = (BpmnModeler as MockFunction).mock.results[0]
        ?.value as MockBpmnModeler;
      expect(modelerInstance?.importXML).toHaveBeenCalled();
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

    // Wait for component to load
    await waitFor(() => {
      expect(screen.getByDisplayValue('New Process')).toBeInTheDocument();
    });

    // Change process name
    const nameInput = screen.getByPlaceholderText('Process Name');
    await user.clear(nameInput);
    await user.type(nameInput, newProcess.name);

    // Click save button
    const saveButton = screen.getByRole('button', { name: /save/i });
    await user.click(saveButton);

    // Should have called create API with correct data
    await waitFor(() => {
      expect(apiService.createProcessDefinition).toHaveBeenCalledWith(
        expect.objectContaining({
          name: newProcess.name,
          bpmnXml: expect.any(String),
          version: 1,
          variableDefinitions: expect.any(Array),
        })
      );
    });
  });

  it('cleans up modeler on unmount', async () => {
    const { default: BpmnModeler } = await import('bpmn-js/lib/Modeler');
    const destroyMock = vi.fn();

    // Override modeler mock for this specific test
    (BpmnModeler as MockFunction).mockImplementationOnce(() => ({
      importXML: vi.fn().mockResolvedValue({}),
      saveXML: vi.fn().mockResolvedValue({ xml: '<mock-xml/>' }),
      destroy: destroyMock,
      get: vi.fn().mockImplementation((module: string) => {
        if (module === 'eventBus') {
          return { on: vi.fn() };
        }
        if (module === 'elementRegistry') {
          return {
            filter: vi.fn().mockReturnValue([]),
            get: vi.fn(),
          };
        }
        return null;
      }),
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
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/processes');
    });
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
    await waitFor(() => {
      expect(apiService.updateProcessDefinition).toHaveBeenCalledWith(
        mockProcess.id,
        expect.objectContaining({
          name: mockProcess.name,
          bpmnXml: expect.any(String),
          variableDefinitions: expect.any(Array),
        })
      );
    });
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
    // Create a simpler test approach with direct event simulation
    // Set up event callbacks dictionary
    const eventCallbacks: Record<
      string,
      (payload: Record<string, unknown>) => void
    > = {};

    // Create a custom eventBus for this test
    const eventBus = {
      on: vi.fn(
        (
          event: string,
          callback: (payload: Record<string, unknown>) => void
        ) => {
          eventCallbacks[event] = callback;
        }
      ),
      fire: vi.fn(),
    };

    // Override the BpmnModeler mock for this specific test
    const { default: BpmnModeler } = await import('bpmn-js/lib/Modeler');
    (BpmnModeler as MockFunction).mockImplementationOnce(() => ({
      importXML: vi.fn().mockResolvedValue({}),
      saveXML: vi.fn().mockResolvedValue({ xml: '<mock-xml/>' }),
      destroy: vi.fn(),
      get: vi.fn().mockImplementation((module: string) => {
        if (module === 'eventBus') return eventBus;
        if (module === 'elementRegistry') {
          return {
            filter: vi.fn().mockReturnValue([]),
            get: vi.fn(),
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

    // Verify that the event.dblclick handler was registered
    expect(eventBus.on).toHaveBeenCalledWith(
      'element.dblclick',
      expect.any(Function)
    );

    // Now trigger the double-click event using our captured callbacks
    act(() => {
      if (eventCallbacks['element.dblclick']) {
        eventCallbacks['element.dblclick']({
          element: { id: 'test-element', type: 'bpmn:ServiceTask' },
        });
      } else {
        throw new Error('element.dblclick callback not registered');
      }
    });

    // Check that the element panel is opened
    await waitFor(() => {
      expect(screen.getByTestId('mock-element-panel')).toBeInTheDocument();
    });
  });
});
