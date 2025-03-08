import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import ProcessList from './ProcessList';
import apiService from '@/services/api';
import { ProcessStatus } from '@/types/process';

// Mock API service
vi.mock('@/services/api', () => ({
  default: {
    getProcessDefinitions: vi.fn(),
    startProcessInstance: vi.fn(),
  },
}));

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock window.alert
const mockAlert = vi.fn();
window.alert = mockAlert;

describe('ProcessList', () => {
  const mockProcesses = {
    data: {
      items: [
        {
          id: '1',
          name: 'Order Process',
          version: 1,
          bpmnXml: '<xml></xml>',
          createdAt: '2025-02-06T12:00:00Z',
          updatedAt: '2025-02-06T12:00:00Z',
          variableDefinitions: [
            {
              name: 'amount',
              type: 'number' as const,
              required: true,
              label: 'Amount',
              validation: {
                min: 0,
              },
            },
          ],
        },
      ],
      total: 1,
      page: 1,
      pageSize: 10,
      totalPages: 1,
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (apiService.getProcessDefinitions as jest.Mock).mockResolvedValue(
      mockProcesses
    );
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  it('renders process list', async () => {
    render(
      <MemoryRouter>
        <ProcessList />
      </MemoryRouter>
    );

    // Wait for loading spinner to appear
    expect(screen.getByRole('progressbar')).toBeInTheDocument();

    // Wait for loading to finish and processes to be rendered
    await waitFor(() => {
      expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
    });

    // Check if process is rendered in the table
    expect(screen.getByText('Order Process')).toBeInTheDocument();
    expect(screen.getByTitle('Start Process')).toBeInTheDocument();
  });

  it('starts process instance successfully', async () => {
    const mockInstance = {
      data: {
        id: 'instance-1',
        definitionId: '1',
        definitionName: 'Order Process',
        status: ProcessStatus.RUNNING,
        startTime: '2025-02-06T12:00:00Z',
        createdAt: '2025-02-06T12:00:00Z',
        updatedAt: '2025-02-06T12:00:00Z',
      },
    };
    (apiService.startProcessInstance as jest.Mock).mockResolvedValue(
      mockInstance
    );

    render(
      <MemoryRouter>
        <ProcessList />
      </MemoryRouter>
    );

    // Wait for loading to finish and processes to be rendered
    await waitFor(() => {
      expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
    });

    // Click start button
    const startButton = screen.getByTitle('Start Process');
    fireEvent.click(startButton);

    // Enter amount in dialog
    await waitFor(() => {
      expect(screen.getByLabelText('Amount')).toBeInTheDocument();
    });
    fireEvent.change(screen.getByLabelText('Amount'), {
      target: { value: '99.99' },
    });
    fireEvent.click(screen.getByText('Start'));

    // Verify API call
    await waitFor(() => {
      expect(apiService.startProcessInstance).toHaveBeenCalledWith({
        definitionId: '1',
        variables: {
          amount: {
            type: 'float',
            value: 99.99,
          },
        },
      });
    });

    // Verify navigation
    expect(mockNavigate).toHaveBeenCalledWith(
      '/processes/1/instances/instance-1'
    );
  });

  it('handles process start error', async () => {
    const error = new Error('Failed to start process');
    (apiService.startProcessInstance as jest.Mock).mockRejectedValue(error);

    render(
      <MemoryRouter>
        <ProcessList />
      </MemoryRouter>
    );

    // Wait for loading to finish and processes to be rendered
    await waitFor(() => {
      expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
    });

    // Click start button
    const startButton = screen.getByTitle('Start Process');
    fireEvent.click(startButton);

    // Enter amount in dialog
    await waitFor(() => {
      expect(screen.getByLabelText('Amount')).toBeInTheDocument();
    });
    fireEvent.change(screen.getByLabelText('Amount'), {
      target: { value: '99.99' },
    });
    fireEvent.click(screen.getByText('Start'));

    // Verify error handling
    await waitFor(() => {
      expect(mockAlert).toHaveBeenCalledWith('Failed to start process');
    });
  });
});
