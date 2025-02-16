import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ProcessInstanceList from './ProcessInstanceList';
import {
  ApiResponse,
  PaginatedResponse,
  ProcessDefinition,
  ProcessInstance,
  ProcessStatus,
} from '@/types/process';

// Mock the API service
const mockGetProcessInstances = vi.fn();
const mockGetProcessDefinition = vi.fn();

vi.mock('@/services/api', () => ({
  default: {
    getProcessInstances: (options?: {
      definitionId?: string;
      page?: number;
      pageSize?: number;
      status?: string;
    }) => mockGetProcessInstances(options),
    getProcessDefinition: (id: string) => mockGetProcessDefinition(id),
  },
}));

describe('ProcessInstanceList', () => {
  const mockProcessId = '03fffc6c-b6da-43eb-aed5-a582ac8dde72';
  const mockInstances: ApiResponse<PaginatedResponse<ProcessInstance>> = {
    data: {
      items: [
        {
          id: '1',
          definitionId: mockProcessId,
          definitionName: 'Test Process',
          status: ProcessStatus.RUNNING,
          startTime: '2024-02-15T12:00:00Z',
          createdAt: '2024-02-15T12:00:00Z',
          updatedAt: '2024-02-15T12:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      pageSize: 10,
      totalPages: 1,
    },
  };

  const mockProcessDefinition: ApiResponse<ProcessDefinition> = {
    data: {
      id: mockProcessId,
      name: 'Test Process',
      version: 1,
      bpmnXml: '<xml></xml>',
      variableDefinitions: [],
      activeInstances: 1,
      totalInstances: 1,
      createdAt: '2024-02-15T12:00:00Z',
      updatedAt: '2024-02-15T12:00:00Z',
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockGetProcessInstances.mockResolvedValue(mockInstances);
    mockGetProcessDefinition.mockResolvedValue(mockProcessDefinition);
  });

  it('fetches and displays instances for the correct process', async () => {
    render(
      <MemoryRouter initialEntries={[`/processes/${mockProcessId}/instances`]}>
        <Routes>
          <Route
            path="/processes/:id/instances"
            element={<ProcessInstanceList />}
          />
        </Routes>
      </MemoryRouter>
    );

    // Verify API calls
    await waitFor(() => {
      expect(mockGetProcessInstances).toHaveBeenCalledWith({
        definitionId: mockProcessId,
        page: 1,
        pageSize: 10,
        status: undefined,
      });
    });

    expect(mockGetProcessDefinition).toHaveBeenCalledWith(mockProcessId);

    // Verify rendered content
    await waitFor(() => {
      // Find the process name in the header
      expect(
        screen.getByRole('heading', {
          name: /Process Instances - Test Process/i,
        })
      ).toBeInTheDocument();
      // Find the status chip
      expect(screen.getByText('RUNNING')).toBeInTheDocument();
    });
  });

  it('handles different process IDs correctly', async () => {
    const anotherProcessId = '41deafdb-189d-4359-9dc7-4c64cd9aa6e3';
    const anotherProcessInstances: ApiResponse<
      PaginatedResponse<ProcessInstance>
    > = {
      data: {
        items: [
          {
            id: '2',
            definitionId: anotherProcessId,
            definitionName: 'Another Process',
            status: ProcessStatus.RUNNING,
            startTime: '2024-02-15T12:00:00Z',
            createdAt: '2024-02-15T12:00:00Z',
            updatedAt: '2024-02-15T12:00:00Z',
          },
        ],
        total: 1,
        page: 1,
        pageSize: 10,
        totalPages: 1,
      },
    };

    const anotherProcessDefinition: ApiResponse<ProcessDefinition> = {
      data: {
        id: anotherProcessId,
        name: 'Another Process',
        version: 1,
        bpmnXml: '<xml></xml>',
        variableDefinitions: [],
        activeInstances: 1,
        totalInstances: 1,
        createdAt: '2024-02-15T12:00:00Z',
        updatedAt: '2024-02-15T12:00:00Z',
      },
    };

    mockGetProcessInstances.mockResolvedValueOnce(anotherProcessInstances);
    mockGetProcessDefinition.mockResolvedValueOnce(anotherProcessDefinition);

    render(
      <MemoryRouter
        initialEntries={[`/processes/${anotherProcessId}/instances`]}
      >
        <Routes>
          <Route
            path="/processes/:id/instances"
            element={<ProcessInstanceList />}
          />
        </Routes>
      </MemoryRouter>
    );

    // Verify API calls with different process ID
    await waitFor(() => {
      expect(mockGetProcessInstances).toHaveBeenCalledWith({
        definitionId: anotherProcessId,
        page: 1,
        pageSize: 10,
        status: undefined,
      });
    });

    expect(mockGetProcessDefinition).toHaveBeenCalledWith(anotherProcessId);

    // Verify rendered content shows different process
    await waitFor(() => {
      // Find the process name in the header
      expect(
        screen.getByRole('heading', {
          name: /Process Instances - Another Process/i,
        })
      ).toBeInTheDocument();
    });
  });

  it('handles status filtering correctly', async () => {
    mockGetProcessInstances.mockImplementation(
      (options?: {
        definitionId?: string;
        page?: number;
        pageSize?: number;
        status?: string;
      }) =>
        Promise.resolve({
          data: {
            items: [
              {
                id: '1',
                definitionId: mockProcessId,
                definitionName: 'Test Process',
                status: options?.status
                  ? (options.status.toUpperCase() as ProcessStatus)
                  : ProcessStatus.RUNNING,
                startTime: '2024-02-15T12:00:00Z',
                createdAt: '2024-02-15T12:00:00Z',
                updatedAt: '2024-02-15T12:00:00Z',
              },
            ],
            total: 1,
            page: 1,
            pageSize: 10,
            totalPages: 1,
          },
        })
    );

    render(
      <MemoryRouter initialEntries={[`/processes/${mockProcessId}/instances`]}>
        <Routes>
          <Route
            path="/processes/:id/instances"
            element={<ProcessInstanceList />}
          />
        </Routes>
      </MemoryRouter>
    );

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getAllByText('Test Process')[0]).toBeInTheDocument();
    });

    // Change status filter
    const statusSelect = screen.getByRole('combobox');
    fireEvent.mouseDown(statusSelect);

    // Wait for the dropdown to open and select Running
    const runningOption = await screen.findByText('Running');
    fireEvent.click(runningOption);

    // Verify API call with status filter
    await waitFor(() => {
      expect(mockGetProcessInstances).toHaveBeenCalledWith({
        definitionId: mockProcessId,
        page: 1,
        pageSize: 10,
        status: 'running',
      });
    });

    // Verify the filtered results are displayed
    await waitFor(() => {
      expect(screen.getByText('RUNNING')).toBeInTheDocument();
    });
  });
});
