import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes, useNavigate } from 'react-router-dom';
import ProcessDesigner from './ProcessDesigner';
import apiService from '@/services/api';

// Mock the API service
jest.mock('@/services/api');

// Mock react-router-dom
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: jest.fn(),
}));

// Mock bpmn-js
jest.mock('bpmn-js/lib/Modeler', () => {
  return jest.fn().mockImplementation(() => ({
    importXML: jest.fn().mockResolvedValue({}),
    saveXML: jest.fn().mockResolvedValue({ xml: '<mock-xml/>' }),
    destroy: jest.fn(),
  }));
});

describe('ProcessDesigner', () => {
  const mockProcess = {
    id: '123',
    name: 'Test Process',
    bpmn_xml: '<test-xml/>',
    version: 1,
    created_at: '2024-02-06T00:00:00Z',
    updated_at: '2024-02-06T00:00:00Z',
  };

  beforeEach(() => {
    // Clear all mocks before each test
    jest.clearAllMocks();
    // Reset useNavigate mock
    (useNavigate as jest.Mock).mockReset();
  });

  afterEach(() => {
    // Restore window.alert if it was mocked
    if (global.alert !== window.alert) {
      global.alert = window.alert;
    }
  });

  it('loads existing process when editing', async () => {
    // Mock the API call
    (apiService.getProcessDefinition as jest.Mock).mockResolvedValueOnce({
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
    (apiService.getProcessDefinition as jest.Mock).mockRejectedValueOnce(
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
    const BpmnModeler = require('bpmn-js/lib/Modeler');

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
      const modelerInstance = (BpmnModeler as jest.Mock).mock.results[0]?.value;
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
    (apiService.createProcessDefinition as jest.Mock).mockResolvedValueOnce({
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
        bpmn_xml: expect.any(String),
        version: 1,
      })
    );
  });

  it('cleans up modeler on unmount', async () => {
    const BpmnModeler = require('bpmn-js/lib/Modeler');
    const destroyMock = jest.fn();

    // Setup modeler mock with destroy function
    (BpmnModeler as jest.Mock).mockImplementation(() => ({
      importXML: jest.fn().mockResolvedValue({}),
      saveXML: jest.fn().mockResolvedValue({ xml: '<mock-xml/>' }),
      destroy: destroyMock,
    }));

    // Mock the API call
    (apiService.getProcessDefinition as jest.Mock).mockResolvedValueOnce({
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
    const mockNavigate = jest.fn();
    (useNavigate as jest.Mock).mockReturnValue(mockNavigate);

    // Mock the API calls
    (apiService.getProcessDefinition as jest.Mock).mockResolvedValueOnce({
      data: mockProcess,
    });
    (apiService.updateProcessDefinition as jest.Mock).mockResolvedValueOnce({
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
    (apiService.getProcessDefinition as jest.Mock).mockResolvedValueOnce({
      data: mockProcess,
    });
    (apiService.updateProcessDefinition as jest.Mock).mockResolvedValueOnce({
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
        bpmn_xml: expect.any(String),
      })
    );
  });

  it('shows error when save fails', async () => {
    const user = userEvent.setup();
    const mockError = new Error('Save failed');
    const alertMock = jest.fn();

    // Mock window.alert before rendering
    global.alert = alertMock;

    // Mock the API calls
    (apiService.getProcessDefinition as jest.Mock).mockResolvedValueOnce({
      data: mockProcess,
    });
    (apiService.updateProcessDefinition as jest.Mock).mockRejectedValueOnce(
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
      expect(alertMock).toHaveBeenCalledWith(
        expect.stringContaining('Failed to save process')
      );
    });

    // Alert cleanup is handled in afterEach
  });
});
