import { vi, describe, it, expect, beforeEach } from 'vitest';
import axios from 'axios';
import apiService from '../api';
import { ProcessStatus } from '@/types/process';

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
    transformRequest: null as any,
    transformResponse: null as any,
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
const mockedAxios = axios.create();

describe('ApiService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // Helper function to apply response transformation
  const mockResponseWithTransform = (mockData: any) => {
    const response = { data: mockData };
    return (mockedAxios as any).transformResponse?.(response) || response;
  };

  describe('Case conversion', () => {
    it('converts snake_case to camelCase in process definition response', async () => {
      const mockResponse = {
        data: {
          id: '123',
          name: 'Test Process',
          bpmn_xml: '<xml>...</xml>',
          variable_definitions: [
            {
              name: 'var1',
              default_value: 'test',
            },
          ],
          active_instances: 5,
          total_instances: 10,
          created_at: '2024-02-15T12:00:00Z',
          updated_at: '2024-02-15T12:00:00Z',
        },
      };

      // Mock the axios get method to return our transformed response
      (mockedAxios.get as any).mockResolvedValueOnce(
        mockResponseWithTransform(mockResponse)
      );

      const response = await apiService.getProcessDefinition('123');

      expect(response.data).toEqual({
        id: '123',
        name: 'Test Process',
        bpmnXml: '<xml>...</xml>',
        variableDefinitions: [
          {
            name: 'var1',
            defaultValue: 'test',
          },
        ],
        activeInstances: 5,
        totalInstances: 10,
        createdAt: '2024-02-15T12:00:00Z',
        updatedAt: '2024-02-15T12:00:00Z',
      });
    });

    it('converts snake_case to camelCase in process instance response', async () => {
      const mockResponse = {
        data: {
          id: '123',
          definition_id: 'def123',
          definition_name: 'Test Process',
          status: ProcessStatus.RUNNING,
          start_time: '2024-02-15T12:00:00Z',
          end_time: null,
          created_at: '2024-02-15T12:00:00Z',
          updated_at: '2024-02-15T12:00:00Z',
        },
      };

      (mockedAxios.get as any).mockResolvedValueOnce(
        mockResponseWithTransform(mockResponse)
      );

      const response = await apiService.getProcessInstance('123');

      expect(response.data).toEqual({
        id: '123',
        definitionId: 'def123',
        definitionName: 'Test Process',
        status: ProcessStatus.RUNNING,
        startTime: '2024-02-15T12:00:00Z',
        endTime: null,
        createdAt: '2024-02-15T12:00:00Z',
        updatedAt: '2024-02-15T12:00:00Z',
      });
    });

    it('converts snake_case to camelCase in process instances list response', async () => {
      const mockResponse = {
        data: {
          items: [
            {
              id: '123',
              definition_id: 'def123',
              definition_name: 'Test Process',
              status: ProcessStatus.RUNNING,
              start_time: '2024-02-15T12:00:00Z',
            },
          ],
          total: 1,
          page: 1,
          page_size: 10,
          total_pages: 1,
        },
      };

      (mockedAxios.get as any).mockResolvedValueOnce(
        mockResponseWithTransform(mockResponse)
      );

      const response = await apiService.getProcessInstances();

      expect(response.data).toEqual({
        items: [
          {
            id: '123',
            definitionId: 'def123',
            definitionName: 'Test Process',
            status: ProcessStatus.RUNNING,
            startTime: '2024-02-15T12:00:00Z',
          },
        ],
        total: 1,
        page: 1,
        pageSize: 10,
        totalPages: 1,
      });
    });

    it('converts snake_case to camelCase in process stats response', async () => {
      const mockResponse = {
        data: {
          total_instances: 100,
          status_counts: {
            [ProcessStatus.RUNNING]: 5,
            [ProcessStatus.COMPLETED]: 90,
            [ProcessStatus.ERROR]: 5,
          },
          average_completion_time: 120,
          error_rate: 5,
          active_instances: 5,
        },
      };

      (mockedAxios.get as any).mockResolvedValueOnce(
        mockResponseWithTransform(mockResponse)
      );

      const response = await apiService.getProcessStats();

      expect(response.data).toEqual({
        totalInstances: 100,
        statusCounts: {
          [ProcessStatus.RUNNING]: 5,
          [ProcessStatus.COMPLETED]: 90,
          [ProcessStatus.ERROR]: 5,
        },
        averageCompletionTime: 120,
        errorRate: 5,
        activeInstances: 5,
      });
    });

    it('converts snake_case to camelCase in tokens response', async () => {
      const mockResponse = {
        data: [
          {
            node_id: 'node1',
            state: 'active',
            scope_id: 'scope1',
            data: {
              some_value: 123,
              nested_data: {
                inner_value: 'test',
              },
            },
          },
        ],
      };

      (mockedAxios.get as any).mockResolvedValueOnce(
        mockResponseWithTransform(mockResponse)
      );

      const response = await apiService.getInstanceTokens('123');

      expect(response.data).toEqual([
        {
          nodeId: 'node1',
          state: 'active',
          scopeId: 'scope1',
          data: {
            someValue: 123,
            nestedData: {
              innerValue: 'test',
            },
          },
        },
      ]);
    });
  });
});
