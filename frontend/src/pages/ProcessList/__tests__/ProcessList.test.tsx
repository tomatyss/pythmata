import { vi, describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import {
  ApiResponse,
  PaginatedResponse,
  ProcessDefinition,
} from '@/types/process';

// Mock dependencies
vi.mock('react-router-dom', () => ({
  useNavigate: vi.fn(),
}));

// Mock API service
vi.mock('@/services/api', () => ({
  default: {
    getProcessDefinitions: vi.fn(),
    deleteProcessDefinition: vi.fn(),
    startProcessInstance: vi.fn(),
    createProcessDefinition: vi.fn(),
  },
}));

// Mock hook with confirmation dialog
vi.mock('@/hooks/useConfirmDialog', () => ({
  default: () => ({
    confirmDelete: vi.fn((_itemName: string) => Promise.resolve(true)),
    ConfirmDialog: () => <div data-testid="confirm-dialog" />,
  }),
}));

// Import after mocks are defined
import ProcessList from '../ProcessList';
import apiService from '@/services/api';
import { useNavigate } from 'react-router-dom';

describe('ProcessList', () => {
  const mockNavigate = vi.fn();

  // Mock processes with proper typing and all required fields
  const mockProcesses: ApiResponse<PaginatedResponse<ProcessDefinition>> = {
    data: {
      items: [
        {
          id: 'process-1',
          name: 'Test Process 1',
          version: 1,
          bpmnXml: '<xml>...</xml>',
          activeInstances: 2,
          totalInstances: 5,
          createdAt: '2024-02-15T12:00:00Z',
          updatedAt: '2024-02-15T12:00:00Z',
          variableDefinitions: [],
        },
        {
          id: 'process-2',
          name: 'Test Process 2',
          version: 2,
          bpmnXml: '<xml>...</xml>',
          activeInstances: 0,
          totalInstances: 10,
          createdAt: '2024-02-15T12:00:00Z',
          updatedAt: '2024-02-15T12:00:00Z',
          variableDefinitions: [],
        },
      ],
      total: 2,
      page: 1,
      pageSize: 10,
      totalPages: 1,
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (useNavigate as jest.MockedFunction<typeof useNavigate>).mockReturnValue(
      mockNavigate
    );
    (
      apiService.getProcessDefinitions as jest.MockedFunction<
        typeof apiService.getProcessDefinitions
      >
    ).mockResolvedValue(mockProcesses);
  });

  it('renders process list correctly', async () => {
    render(<ProcessList />);

    // Should show loading initially
    expect(screen.getByRole('progressbar')).toBeInTheDocument();

    // Wait for processes to load
    await waitFor(() => {
      expect(screen.getByText('Test Process 1')).toBeInTheDocument();
      expect(screen.getByText('Test Process 2')).toBeInTheDocument();
    });

    // Should display process information
    expect(screen.getByText('v1')).toBeInTheDocument();
    expect(screen.getByText('v2')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument(); // active instances
    expect(screen.getByText('5')).toBeInTheDocument(); // total instances
    expect(screen.getByText('10')).toBeInTheDocument(); // total instances
  });

  it('deletes a process successfully', async () => {
    (
      apiService.deleteProcessDefinition as jest.MockedFunction<
        typeof apiService.deleteProcessDefinition
      >
    ).mockResolvedValue({
      data: undefined,
    });

    render(<ProcessList />);

    // Wait for processes to load
    await waitFor(() => {
      expect(screen.getByText('Test Process 1')).toBeInTheDocument();
    });

    // Find and click delete button for the first process
    const deleteButtons = screen.getAllByTitle('Delete Process');
    expect(deleteButtons.length).toBeGreaterThan(0);
    if (deleteButtons[0]) {
      fireEvent.click(deleteButtons[0]);
    }

    // Should call delete API with correct process ID
    await waitFor(() => {
      expect(apiService.deleteProcessDefinition).toHaveBeenCalledWith(
        'process-1'
      );
    });

    // Process should be removed from the list
    await waitFor(() => {
      expect(screen.queryByText('Test Process 1')).not.toBeInTheDocument();
      expect(screen.getByText('Test Process 2')).toBeInTheDocument();
    });
  });

  it('handles deletion error', async () => {
    // Mock console.error to prevent test output pollution
    const originalConsoleError = console.error;
    console.error = vi.fn();

    // Mock window.alert
    const alertMock = vi.fn();
    window.alert = alertMock;

    // Mock API to throw an error
    const errorMessage = 'Failed to delete process';
    (
      apiService.deleteProcessDefinition as jest.MockedFunction<
        typeof apiService.deleteProcessDefinition
      >
    ).mockRejectedValue(new Error(errorMessage));

    render(<ProcessList />);

    // Wait for processes to load
    await waitFor(() => {
      expect(screen.getByText('Test Process 1')).toBeInTheDocument();
    });

    // Find and click delete button for the first process
    const deleteButtons = screen.getAllByTitle('Delete Process');
    expect(deleteButtons.length).toBeGreaterThan(0);
    if (deleteButtons[0]) {
      fireEvent.click(deleteButtons[0]);
    }

    // Should show error alert
    await waitFor(() => {
      expect(alertMock).toHaveBeenCalledWith(errorMessage);
    });

    // Should still display all processes
    expect(screen.getByText('Test Process 1')).toBeInTheDocument();
    expect(screen.getByText('Test Process 2')).toBeInTheDocument();

    // Restore console.error
    console.error = originalConsoleError;
  });

  it('navigates to correct routes when action buttons are clicked', async () => {
    render(<ProcessList />);

    // Wait for processes to load
    await waitFor(() => {
      expect(screen.getByText('Test Process 1')).toBeInTheDocument();
    });

    // Test each button navigation
    const viewDiagramButtons = screen.getAllByTitle('View Diagram');
    expect(viewDiagramButtons.length).toBeGreaterThan(0);
    if (viewDiagramButtons[0]) {
      fireEvent.click(viewDiagramButtons[0]);
    }
    expect(mockNavigate).toHaveBeenCalledWith('/processes/process-1/diagram');

    const viewInstancesButtons = screen.getAllByTitle('View Instances');
    expect(viewInstancesButtons.length).toBeGreaterThan(0);
    if (viewInstancesButtons[0]) {
      fireEvent.click(viewInstancesButtons[0]);
    }
    expect(mockNavigate).toHaveBeenCalledWith('/processes/process-1/instances');

    const editProcessButtons = screen.getAllByTitle('Edit Process');
    expect(editProcessButtons.length).toBeGreaterThan(0);
    if (editProcessButtons[0]) {
      fireEvent.click(editProcessButtons[0]);
    }
    expect(mockNavigate).toHaveBeenCalledWith('/processes/process-1');
  });

  it('copies a process successfully', async () => {
    // Mock the createProcessDefinition API call
    const mockCopiedProcess = {
      data: {
        id: 'process-3',
        name: 'Copy of Test Process 1',
        version: 1,
        bpmnXml: '<xml>...</xml>',
        activeInstances: 0,
        totalInstances: 0,
        createdAt: '2024-02-15T12:00:00Z',
        updatedAt: '2024-02-15T12:00:00Z',
        variableDefinitions: [],
      },
    };

    (
      apiService.createProcessDefinition as jest.MockedFunction<
        typeof apiService.createProcessDefinition
      >
    ).mockResolvedValue(mockCopiedProcess);

    // Mock window.alert
    const alertMock = vi.fn();
    window.alert = alertMock;

    render(<ProcessList />);

    // Wait for processes to load
    await waitFor(() => {
      expect(screen.getByText('Test Process 1')).toBeInTheDocument();
    });

    // Find and click copy button for the first process
    const copyButtons = screen.getAllByTitle('Copy Process');
    expect(copyButtons.length).toBeGreaterThan(0);
    if (copyButtons[0]) {
      fireEvent.click(copyButtons[0]);
    }

    // Should call createProcessDefinition API with correct data
    await waitFor(() => {
      expect(apiService.createProcessDefinition).toHaveBeenCalledWith({
        name: 'Copy of Test Process 1',
        bpmnXml: '<xml>...</xml>',
        variableDefinitions: [],
      });
    });

    // Should show success message
    expect(alertMock).toHaveBeenCalledWith('Process copied successfully');

    // New process should be added to the list
    await waitFor(() => {
      expect(screen.getByText('Copy of Test Process 1')).toBeInTheDocument();
    });
  });

  it('handles copy process error', async () => {
    // Mock console.error to prevent test output pollution
    const originalConsoleError = console.error;
    console.error = vi.fn();

    // Mock window.alert
    const alertMock = vi.fn();
    window.alert = alertMock;

    // Mock API to throw an error
    const errorMessage = 'Failed to copy process';
    (
      apiService.createProcessDefinition as jest.MockedFunction<
        typeof apiService.createProcessDefinition
      >
    ).mockRejectedValue(new Error(errorMessage));

    render(<ProcessList />);

    // Wait for processes to load
    await waitFor(() => {
      expect(screen.getByText('Test Process 1')).toBeInTheDocument();
    });

    // Find and click copy button for the first process
    const copyButtons = screen.getAllByTitle('Copy Process');
    expect(copyButtons.length).toBeGreaterThan(0);
    if (copyButtons[0]) {
      fireEvent.click(copyButtons[0]);
    }

    // Should show error alert
    await waitFor(() => {
      expect(alertMock).toHaveBeenCalledWith(errorMessage);
    });

    // Should not add any new process to the list
    expect(
      screen.queryByText('Copy of Test Process 1')
    ).not.toBeInTheDocument();

    // Restore console.error
    console.error = originalConsoleError;
  });
});
