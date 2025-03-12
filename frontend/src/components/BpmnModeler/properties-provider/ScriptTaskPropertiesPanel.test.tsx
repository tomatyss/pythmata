import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ScriptTaskPropertiesPanel from './ScriptTaskPropertiesPanel';
import apiService from '@/services/api';
import {
  ExtendedBpmnModeler,
  BpmnElement,
} from '@/pages/ProcessDesigner/types';

// Mock the API service
vi.mock('@/services/api', () => ({
  default: {
    getScript: vi.fn(),
    updateScript: vi.fn(),
  },
}));

// Mock the Monaco editor
vi.mock('@monaco-editor/react', () => ({
  Editor: ({
    value,
    onChange,
  }: {
    value: string;
    onChange: (value: string) => void;
  }) => (
    <textarea
      data-testid="monaco-editor"
      value={value}
      onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
        onChange(e.target.value)
      }
    />
  ),
}));

describe('ScriptTaskPropertiesPanel', () => {
  // Basic element with script task properties
  const mockElement: BpmnElement = {
    id: 'script-task-1',
    type: 'bpmn:ScriptTask',
    businessObject: {
      id: 'script-task-1',
      scriptFormat: 'javascript',
      resultVariable: 'result',
      extensionElements: {
        values: [
          {
            $type: 'pythmata:ScriptConfig',
            timeout: '30',
          },
        ],
      },
    },
  };

  // Create a single updateProperties spy that will be used throughout the test
  const updatePropertiesSpy = vi.fn();

  // Mock modeler with necessary methods
  const mockModeler: ExtendedBpmnModeler = {
    get: vi.fn((service: string) => {
      if (service === 'canvas') {
        return {
          getRootElement: () => ({ id: 'Process_1' }),
        };
      }
      if (service === 'elementRegistry') {
        return {
          get: () => ({
            id: 'Process_1',
            businessObject: {
              id: 'process-def-1',
            },
          }),
        };
      }
      if (service === 'modeling') {
        return {
          // Use the same spy instance for all calls
          updateProperties: updatePropertiesSpy,
        };
      }
      if (service === 'moddle') {
        return {
          create: vi.fn((type: string) => {
            if (type === 'bpmn:ExtensionElements') {
              return { values: [] };
            }
            if (type === 'pythmata:ScriptConfig') {
              return { timeout: '30' };
            }
            return {};
          }),
        };
      }
      return {};
    }),
  } as unknown as ExtendedBpmnModeler;

  beforeEach(() => {
    vi.clearAllMocks();

    // Mock successful API responses
    (apiService.getScript as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: {
        id: 'script-1',
        processDefId: 'process-def-1',
        nodeId: 'script-task-1',
        content: 'console.log("Hello World");\nresult = "success";',
        version: 1,
        createdAt: '2025-03-11T12:00:00Z',
        updatedAt: '2025-03-11T12:00:00Z',
      },
    });

    (apiService.updateScript as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: {
        id: 'script-1',
        processDefId: 'process-def-1',
        nodeId: 'script-task-1',
        content: 'console.log("Updated");\nresult = "updated";',
        version: 2,
        createdAt: '2025-03-11T12:00:00Z',
        updatedAt: '2025-03-11T12:30:00Z',
      },
    });
  });

  // Helper function to render the component with router context
  const renderWithRouter = (processId?: string) => {
    return render(
      <MemoryRouter initialEntries={[`/processes/${processId || ''}`]}>
        <Routes>
          <Route
            path="/processes/:id"
            element={
              <ScriptTaskPropertiesPanel
                element={mockElement}
                modeler={mockModeler}
              />
            }
          />
          <Route
            path="/processes"
            element={
              <ScriptTaskPropertiesPanel
                element={mockElement}
                modeler={mockModeler}
              />
            }
          />
        </Routes>
      </MemoryRouter>
    );
  };

  // Test Case 1: Basic rendering with valid process ID
  it('renders loading state initially', async () => {
    renderWithRouter('process-def-1');
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  // Test Case 2: Loads script content from API
  it('loads script content from API when process ID is valid', async () => {
    renderWithRouter('process-def-1');

    await waitFor(() => {
      expect(apiService.getScript).toHaveBeenCalledWith(
        'process-def-1',
        'script-task-1'
      );
      expect(screen.getByTestId('monaco-editor')).toHaveValue(
        'console.log("Hello World");\nresult = "success";'
      );
    });
  });

  // Test Case 3: Shows warning when process ID is missing
  it('shows warning when process ID is missing', async () => {
    renderWithRouter(); // No process ID

    await waitFor(() => {
      expect(
        screen.getByText(
          'Process must be saved before scripts can be edited. Please save the process first.'
        )
      ).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: 'Save Script' })
      ).toBeDisabled();
    });
  });

  // Test Case 4: Updates script language when changed
  it('updates script language when changed', async () => {
    renderWithRouter('process-def-1');

    await waitFor(() => {
      expect(screen.getByTestId('monaco-editor')).toBeInTheDocument();
    });

    // Find the language select by its ID and trigger a change
    const languageSelect = screen.getByLabelText('Script Language');

    // For Material-UI Select, we need to:
    // 1. First click on the select to open the dropdown
    fireEvent.mouseDown(languageSelect);

    // 2. Then find and click on the option we want
    const pythonOption = screen.getByText('Python');
    fireEvent.click(pythonOption);

    // Check that the modeling.updateProperties was called with the right values
    await waitFor(() => {
      const modeling = mockModeler.get('modeling');
      expect(modeling.updateProperties).toHaveBeenCalledWith(
        mockElement,
        expect.objectContaining({
          scriptFormat: 'python',
        })
      );
    });
  });

  // Test Case 5: Updates result variable when changed
  it('updates result variable when changed', async () => {
    renderWithRouter('process-def-1');

    await waitFor(() => {
      expect(screen.getByTestId('monaco-editor')).toBeInTheDocument();
    });

    // Find the result variable input and change it
    const resultVarInput = screen.getByLabelText('Result Variable');
    fireEvent.change(resultVarInput, { target: { value: 'newResult' } });

    // Check that the modeling.updateProperties was called with the right values
    await waitFor(() => {
      const modeling = mockModeler.get('modeling');
      expect(modeling.updateProperties).toHaveBeenCalledWith(
        mockElement,
        expect.objectContaining({
          resultVariable: 'newResult',
        })
      );
    });
  });

  // Test Case 6: Saves script content when save button is clicked
  it('saves script content when save button is clicked', async () => {
    renderWithRouter('process-def-1');

    await waitFor(() => {
      expect(screen.getByTestId('monaco-editor')).toBeInTheDocument();
    });

    // Change the script content
    const editor = screen.getByTestId('monaco-editor');
    fireEvent.change(editor, {
      target: { value: 'console.log("Updated");\nresult = "updated";' },
    });

    // Click the save button
    const saveButton = screen.getByRole('button', { name: 'Save Script' });
    fireEvent.click(saveButton);

    // Check that the API was called with the right values
    await waitFor(() => {
      expect(apiService.updateScript).toHaveBeenCalledWith(
        'process-def-1',
        'script-task-1',
        {
          content: 'console.log("Updated");\nresult = "updated";',
          version: 1,
        }
      );
    });
  });

  // Test Case 7: Validates JavaScript syntax
  it('validates JavaScript syntax and shows error for invalid code', async () => {
    renderWithRouter('process-def-1');

    await waitFor(() => {
      expect(screen.getByTestId('monaco-editor')).toBeInTheDocument();
    });

    // Enter invalid JavaScript
    const editor = screen.getByTestId('monaco-editor');
    fireEvent.change(editor, {
      target: { value: 'console.log("Missing semicolon"' },
    });

    // Check that validation error is shown
    await waitFor(() => {
      expect(screen.getByText(/Syntax error:/)).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: 'Save Script' })
      ).toBeDisabled();
    });
  });

  // Test Case 8: Handles API errors gracefully
  it('handles API errors gracefully when fetching script', async () => {
    // Mock API error
    (apiService.getScript as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error('API Error')
    );

    renderWithRouter('process-def-1');

    await waitFor(() => {
      expect(
        screen.getByText(/Failed to load script content/)
      ).toBeInTheDocument();
    });
  });

  // Test Case 9: Handles API errors gracefully when saving script
  it('handles API errors gracefully when saving script', async () => {
    // Mock successful get but failed update
    (apiService.getScript as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: {
        content: 'console.log("Hello");',
        version: 1,
      },
    });
    (apiService.updateScript as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error('Save Error')
    );

    renderWithRouter('process-def-1');

    await waitFor(() => {
      expect(screen.getByTestId('monaco-editor')).toBeInTheDocument();
    });

    // Click the save button
    const saveButton = screen.getByRole('button', { name: 'Save Script' });
    fireEvent.click(saveButton);

    // Check that error is shown
    await waitFor(() => {
      expect(
        screen.getByText(/Failed to save script content/)
      ).toBeInTheDocument();
    });
  });

  // Test Case 10: Handles 422 validation errors from backend
  it('handles 422 validation errors from backend', async () => {
    // Mock 422 error
    const validationError = new Error('Validation Error');
    (validationError as unknown as { response: { status: number } }).response =
      { status: 422 };
    (apiService.updateScript as ReturnType<typeof vi.fn>).mockRejectedValue(
      validationError
    );

    renderWithRouter('process-def-1');

    await waitFor(() => {
      expect(screen.getByTestId('monaco-editor')).toBeInTheDocument();
    });

    // Click the save button
    const saveButton = screen.getByRole('button', { name: 'Save Script' });
    fireEvent.click(saveButton);

    // Check that specific validation error is shown
    await waitFor(() => {
      expect(
        screen.getByText(
          'Invalid process or node ID. Please save the process first.'
        )
      ).toBeInTheDocument();
    });
  });

  // Test Case 11: Handles 404 not found errors gracefully
  it('handles 404 not found errors gracefully', async () => {
    // Mock 404 error
    const notFoundError = new Error('Not Found');
    (notFoundError as unknown as { response: { status: number } }).response = {
      status: 404,
    };
    (apiService.getScript as ReturnType<typeof vi.fn>).mockRejectedValue(
      notFoundError
    );

    renderWithRouter('process-def-1');

    // Should set default content
    await waitFor(() => {
      expect(screen.getByTestId('monaco-editor')).toHaveValue(
        '// Write your script here\n\n// Set result variable\nresult = null;'
      );
    });
  });

  // Test Case 12: Updates timeout when changed
  it('updates timeout when changed', async () => {
    // Create a fresh spy for updateProperties
    const updatePropertiesSpy = vi.fn();

    // Create a new mock modeler for this test to avoid TypeScript errors
    const testModeler = {
      ...mockModeler,
      get: vi.fn((service: string) => {
        if (service === 'canvas') {
          return {
            getRootElement: () => ({ id: 'Process_1' }),
          };
        }
        if (service === 'elementRegistry') {
          return {
            get: () => ({
              id: 'Process_1',
              businessObject: {
                id: 'process-def-1',
              },
            }),
          };
        }
        if (service === 'modeling') {
          return {
            updateProperties: updatePropertiesSpy,
          };
        }
        if (service === 'moddle') {
          return {
            create: vi.fn(
              (
                type: string,
                props: { timeout?: string; language?: string }
              ) => {
                if (type === 'bpmn:ExtensionElements') {
                  return { values: [] };
                }
                if (type === 'pythmata:ScriptConfig') {
                  return {
                    $type: 'pythmata:ScriptConfig',
                    timeout: props?.timeout || '30',
                    language: props?.language || 'javascript',
                  };
                }
                return {};
              }
            ),
          };
        }
        return {};
      }),
    } as unknown as ExtendedBpmnModeler;

    // Render with our test-specific modeler
    render(
      <MemoryRouter initialEntries={['/processes/process-def-1']}>
        <Routes>
          <Route
            path="/processes/:id"
            element={
              <ScriptTaskPropertiesPanel
                element={mockElement}
                modeler={testModeler}
              />
            }
          />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('monaco-editor')).toBeInTheDocument();
    });

    // Find the timeout input and change it
    const timeoutInput = screen.getByLabelText('Execution Timeout (seconds)');
    fireEvent.change(timeoutInput, { target: { value: '60' } });

    // Check that the updateProperties spy was called
    await waitFor(() => {
      expect(updatePropertiesSpy).toHaveBeenCalled();
    });
  });

  // Test Case 13: Handles missing element or businessObject gracefully
  it('handles missing element or businessObject gracefully', async () => {
    // Render with null element
    render(
      <MemoryRouter initialEntries={['/processes/process-def-1']}>
        <Routes>
          <Route
            path="/processes/:id"
            element={
              <ScriptTaskPropertiesPanel element={null} modeler={mockModeler} />
            }
          />
        </Routes>
      </MemoryRouter>
    );

    // Should not crash
    await waitFor(() => {
      expect(screen.queryByTestId('monaco-editor')).not.toBeInTheDocument();
    });
  });

  // Test Case 14: Handles missing modeler gracefully
  it('handles missing modeler gracefully', async () => {
    // Render with null modeler
    render(
      <MemoryRouter initialEntries={['/processes/process-def-1']}>
        <Routes>
          <Route
            path="/processes/:id"
            element={
              <ScriptTaskPropertiesPanel element={mockElement} modeler={null} />
            }
          />
        </Routes>
      </MemoryRouter>
    );

    // Should not crash
    await waitFor(() => {
      expect(screen.queryByTestId('monaco-editor')).not.toBeInTheDocument();
    });
  });
});
