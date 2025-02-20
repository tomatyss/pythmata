import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes, useNavigate } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import ProcessDesigner from './ProcessDesigner';
import apiService from '@/services/api';

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
  default: vi.fn().mockImplementation(() => ({
    importXML: vi.fn().mockResolvedValue({}),
    saveXML: vi.fn().mockResolvedValue({ xml: '<mock-xml/>' }),
    destroy: vi.fn(),
  })),
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
    (useNavigate as any).mockReturnValue(mockNavigate);
    // Set up window.alert mock
    window.alert = mockAlert;
  });

  afterEach(() => {
    // Restore window.alert after each test
    window.alert = originalAlert;
  });

  it('loads existing process when editing', async () => {
    // Mock the API call
    (apiService.getProcessDefinition as any).mockResolvedValueOnce({
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
    (apiService.getProcessDefinition as any).mockRejectedValueOnce(
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
      const modelerInstance = (BpmnModeler as any).mock.results[0]?.value;
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
    (apiService.createProcessDefinition as any).mockResolvedValueOnce({
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
    (BpmnModeler as any).mockImplementation(() => ({
      importXML: vi.fn().mockResolvedValue({}),
      saveXML: vi.fn().mockResolvedValue({ xml: '<mock-xml/>' }),
      destroy: destroyMock,
    }));

    // Mock the API call
    (apiService.getProcessDefinition as any).mockResolvedValueOnce({
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
    (useNavigate as any).mockReturnValue(mockNavigate);

    // Mock the API calls
    (apiService.getProcessDefinition as any).mockResolvedValueOnce({
      data: mockProcess,
    });
    (apiService.updateProcessDefinition as any).mockResolvedValueOnce({
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
    (apiService.getProcessDefinition as any).mockResolvedValueOnce({
      data: mockProcess,
    });
    (apiService.updateProcessDefinition as any).mockResolvedValueOnce({
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
    (apiService.getProcessDefinition as any).mockResolvedValueOnce({
      data: mockProcess,
    });
    (apiService.updateProcessDefinition as any).mockRejectedValueOnce(
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
});
