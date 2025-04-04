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
// Mock Material-UI components
vi.mock('@mui/material', () => {
  return {
    Box: ({
      children,
      sx: _sx,
    }: {
      children: React.ReactNode;
      sx?: Record<string, unknown>;
    }) => <div>{children}</div>,
    Typography: ({
      children,
      color: _color,
      sx: _sx,
      variant: _variant,
    }: {
      children: React.ReactNode;
      color?: string;
      sx?: Record<string, unknown>;
      variant?: string;
    }) => <div>{children}</div>,
    FormControl: ({
      children,
      fullWidth: _fullWidth,
      sx: _sx,
    }: {
      children: React.ReactNode;
      fullWidth?: boolean;
      sx?: Record<string, unknown>;
    }) => <div>{children}</div>,
    InputLabel: ({
      children,
      id,
    }: {
      children: React.ReactNode;
      id?: string;
    }) => <label htmlFor={id}>{children}</label>,
    Select: ({
      children,
      labelId,
      id,
      value,
      onChange,
      label: _label,
    }: {
      children: React.ReactNode;
      labelId?: string;
      id?: string;
      value: string;
      onChange: (e: React.ChangeEvent<HTMLSelectElement>) => void;
      label?: string;
    }) => (
      <select
        aria-labelledby={labelId}
        id={id}
        value={value}
        onChange={onChange}
      >
        {children}
      </select>
    ),
    MenuItem: ({
      children,
      value,
    }: {
      children: React.ReactNode;
      value: string | number | readonly string[] | undefined;
    }) => <option value={value}>{children}</option>,
    TextField: ({
      label,
      fullWidth: _fullWidth,
      value,
      onChange,
      helperText,
      sx: _sx,
      type,
    }: {
      label: string;
      fullWidth?: boolean;
      value: string;
      onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
      helperText?: string;
      sx?: Record<string, unknown>;
      type?: string;
    }) => (
      <div>
        <label>{label}</label>
        <input
          type={type || 'text'}
          value={value}
          onChange={onChange}
          aria-label={label}
        />
        {helperText && <div>{helperText}</div>}
      </div>
    ),
    CircularProgress: ({
      size: _size,
      sx: _sx,
    }: {
      size?: number;
      sx?: Record<string, unknown>;
    }) => <div role="progressbar">Loading...</div>,
    FormHelperText: ({ children }: { children: React.ReactNode }) => (
      <div>{children}</div>
    ),
    Button: ({
      children,
      variant: _variant,
      color: _color,
      onClick,
      disabled,
    }: {
      children: React.ReactNode;
      variant?: string;
      color?: string;
      onClick?: () => void;
      disabled?: boolean;
    }) => (
      <button onClick={onClick} disabled={disabled}>
        {children}
      </button>
    ),
    Alert: ({
      children,
      severity: _severity,
      sx: _sx,
      onClose: _onClose,
    }: {
      children: React.ReactNode;
      severity?: string;
      sx?: Record<string, unknown>;
      onClose?: () => void;
    }) => <div role="alert">{children}</div>,
    Snackbar: ({
      children,
      open,
      autoHideDuration: _autoHideDuration,
      onClose: _onClose,
      anchorOrigin: _anchorOrigin,
    }: {
      children: React.ReactNode;
      open?: boolean;
      autoHideDuration?: number;
      onClose?: () => void;
      anchorOrigin?: unknown;
    }) => (open ? <div>{children}</div> : null),
  };
});

// Mock the API service
vi.mock('@/services/api', () => ({
  default: {
    getScript: vi.fn(),
    updateScript: vi.fn(),
  },
}));

// Mock the Monaco editor
vi.mock('@monaco-editor/react', () => ({
  default: vi.fn(),
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

  // Test Case 3: Shows info message when process ID is missing
  it('shows info message when process ID is missing', async () => {
    renderWithRouter(); // No process ID

    await waitFor(() => {
      expect(
        screen.getByText(
          'Script properties will be stored in the process model. Save the process to persist scripts to the server.'
        )
      ).toBeInTheDocument();
      // Save button should be enabled now
      expect(screen.getByRole('button', { name: 'Save Script' })).toBeEnabled();
    });
  });

  // Test Case 4: Updates script language when changed
  it('updates script language when changed', async () => {
    // Mock the updateProperties function to ensure it's called
    const updatePropertiesMock = vi.fn();
    const mockingModeler = {
      ...mockModeler,
      get: vi.fn((service) => {
        if (service === 'modeling') {
          return {
            updateProperties: updatePropertiesMock,
          };
        }
        return mockModeler.get(service);
      }),
    };

    render(
      <MemoryRouter initialEntries={['/processes/process-def-1']}>
        <Routes>
          <Route
            path="/processes/:id"
            element={
              <ScriptTaskPropertiesPanel
                element={mockElement}
                modeler={mockingModeler}
              />
            }
          />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('monaco-editor')).toBeInTheDocument();
    });

    // Find the language select by its role
    const languageSelect = screen.getByRole('combobox');

    // Directly simulate a change event on the select
    fireEvent.change(languageSelect, { target: { value: 'python' } });

    // Check that the updateProperties mock was called
    expect(updatePropertiesMock).toHaveBeenCalled();
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

  // Test Case 6: Auto-saves script content when content changes with process ID
  it('auto-saves script content when content changes with process ID', async () => {
    // Mock the timer
    vi.useFakeTimers();

    renderWithRouter('process-def-1');

    await waitFor(() => {
      expect(screen.getByTestId('monaco-editor')).toBeInTheDocument();
    });

    // Change the script content
    const editor = screen.getByTestId('monaco-editor');
    fireEvent.change(editor, {
      target: { value: 'console.log("Updated");\nresult = "updated";' },
    });

    // Fast-forward timer to trigger auto-save
    vi.runAllTimers();

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

    // Restore real timers
    vi.useRealTimers();
  });

  // Test Case 6b: Updates BPMN model when content changes without process ID
  it('updates BPMN model when content changes without process ID', async () => {
    renderWithRouter(); // No process ID

    await waitFor(() => {
      expect(screen.getByTestId('monaco-editor')).toBeInTheDocument();
    });

    // Change the script content
    const editor = screen.getByTestId('monaco-editor');
    fireEvent.change(editor, {
      target: { value: 'console.log("Updated");\nresult = "updated";' },
    });

    // Check that the API was NOT called
    expect(apiService.updateScript).not.toHaveBeenCalled();

    // Check that the BPMN model was updated
    expect(updatePropertiesSpy).toHaveBeenCalled();
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

  // Test Case 9: Handles API errors gracefully when auto-saving script
  it('handles API errors gracefully when auto-saving script', async () => {
    // Mock the timer
    vi.useFakeTimers();

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

    // Change the script content
    const editor = screen.getByTestId('monaco-editor');
    fireEvent.change(editor, {
      target: { value: 'console.log("Updated");\nresult = "updated";' },
    });

    // Fast-forward timer to trigger auto-save
    vi.runAllTimers();

    // Verify the API was called but failed
    await waitFor(() => {
      expect(apiService.updateScript).toHaveBeenCalled();
    });

    // Error should not be shown for auto-save failures
    expect(
      screen.queryByText(/Failed to save script content/)
    ).not.toBeInTheDocument();

    // Restore real timers
    vi.useRealTimers();
  });

  // Test Case 9b: Updates BPMN model even when API fails
  it('updates BPMN model even when API fails', async () => {
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

    // Change the script content
    const editor = screen.getByTestId('monaco-editor');
    fireEvent.change(editor, {
      target: { value: 'console.log("Updated");\nresult = "updated";' },
    });

    // Check that the BPMN model was updated even without clicking save
    await waitFor(() => {
      expect(updatePropertiesSpy).toHaveBeenCalled();
    });
  });

  // Test Case 10: Handles 422 validation errors from backend during auto-save
  it('handles 422 validation errors from backend during auto-save', async () => {
    // Mock the timer
    vi.useFakeTimers();

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

    // Change the script content
    const editor = screen.getByTestId('monaco-editor');
    fireEvent.change(editor, {
      target: { value: 'console.log("Updated");\nresult = "updated";' },
    });

    // Fast-forward timer to trigger auto-save
    vi.runAllTimers();

    // Verify the API was called but failed
    await waitFor(() => {
      expect(apiService.updateScript).toHaveBeenCalled();
    });

    // Error should not be shown for auto-save validation errors
    expect(
      screen.queryByText(/Invalid process or node ID/)
    ).not.toBeInTheDocument();

    // Restore real timers
    vi.useRealTimers();
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

  // Test Case 15: Loads script content from BPMN model if available
  it('loads script content from BPMN model if available', async () => {
    // Create a mock element with script content in extension elements
    const elementWithScriptContent = {
      ...mockElement,
      businessObject: {
        ...mockElement.businessObject,
        extensionElements: {
          values: [
            {
              $type: 'pythmata:ScriptConfig',
              timeout: '30',
              scriptContent: 'console.log("From BPMN model");',
            },
          ],
        },
      },
    };

    // Render with the modified element
    render(
      <MemoryRouter initialEntries={['/processes/process-def-1']}>
        <Routes>
          <Route
            path="/processes/:id"
            element={
              <ScriptTaskPropertiesPanel
                element={elementWithScriptContent}
                modeler={mockModeler}
              />
            }
          />
        </Routes>
      </MemoryRouter>
    );

    // Should load content from BPMN model
    await waitFor(() => {
      expect(screen.getByTestId('monaco-editor')).toHaveValue(
        'console.log("From BPMN model");'
      );
    });

    // API should not be called since content was found in BPMN model
    expect(apiService.getScript).not.toHaveBeenCalled();
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
