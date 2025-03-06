import { vi, describe, it, expect, beforeEach } from 'vitest';
import axios from 'axios';
import apiService from '../api';

// Mock axios
vi.mock('axios', () => {
  const mockAxiosInstance = {
    interceptors: {
      request: {
        use: vi.fn((successFn) => {
          mockAxiosInstance.transformRequest = successFn;
        }),
      },
      response: {
        use: vi.fn((successFn) => {
          mockAxiosInstance.transformResponse = successFn;
        }),
      },
    },
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    transformRequest: null as unknown,
    transformResponse: null as unknown,
  };

  return {
    default: {
      create: vi.fn(() => {
        return mockAxiosInstance;
      }),
    },
  };
});

// Create the mocked axios instance
const mockedAxios = axios.create() as unknown as ReturnType<
  typeof axios.create
> & {
  transformRequest: (config: unknown) => unknown;
  transformResponse: (response: unknown) => unknown;
};

describe('ApiService - Process Definition Deletion', () => {
  const processId = 'test-process-123';

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should call delete endpoint with correct process ID', async () => {
    // Mock successful response
    (
      mockedAxios.delete as jest.MockedFunction<typeof mockedAxios.delete>
    ).mockResolvedValueOnce({
      data: { message: 'Process deleted successfully' },
    });

    // Call the deleteProcessDefinition method
    await apiService.deleteProcessDefinition(processId);

    // Check that the delete method was called with the right URL
    expect(mockedAxios.delete).toHaveBeenCalledWith(`/processes/${processId}`);
    expect(mockedAxios.delete).toHaveBeenCalledTimes(1);
  });

  it('should handle API errors when deleting a process', async () => {
    // Create a mock API error
    const errorResponse = {
      response: {
        status: 404,
        data: {
          detail: 'Process not found',
        },
      },
    };

    // Mock a failed response
    (
      mockedAxios.delete as jest.MockedFunction<typeof mockedAxios.delete>
    ).mockRejectedValueOnce(errorResponse);

    // Call the method and expect it to throw
    await expect(
      apiService.deleteProcessDefinition(processId)
    ).rejects.toThrow();
  });
});
