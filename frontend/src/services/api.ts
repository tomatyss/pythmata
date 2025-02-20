import axios, { AxiosInstance, AxiosResponse } from 'axios';
import { ApiError } from '@/lib/errors';
import { convertKeysToCamel, convertKeysToSnake } from '@/utils/case';
import {
  ActivityLog,
  ApiResponse,
  PaginatedResponse,
  ProcessDefinition,
  ProcessInstance,
  ProcessStats,
  Script,
  CreateProcessDefinitionRequest,
  UpdateProcessDefinitionRequest,
  StartProcessInstanceRequest,
  UpdateScriptRequest,
} from '@/types/process';

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: '/api',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add request interceptor to convert camelCase to snake_case
    this.client.interceptors.request.use(
      (config) => {
        if (config.data) {
          config.data = convertKeysToSnake(config.data);
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Add response interceptors for error handling and case conversion
    this.client.interceptors.response.use(
      (response: AxiosResponse) => {
        // Convert snake_case to camelCase in response data
        if (response.data) {
          response.data = convertKeysToCamel(response.data);
        }
        return response;
      },
      (error) => {
        if (error.response) {
          const message =
            error.response.data.detail || error.message || 'An error occurred';
          throw new ApiError(
            message,
            error.response.status,
            error.response.data
          );
        }
        throw new ApiError('Network error', 500);
      }
    );
  }

  // Process Definitions
  async getProcessDefinitions(): Promise<
    ApiResponse<PaginatedResponse<ProcessDefinition>>
  > {
    const response = await this.client.get('/processes');
    return response.data;
  }

  async getProcessDefinition(
    id: string
  ): Promise<ApiResponse<ProcessDefinition>> {
    const response = await this.client.get(`/processes/${id}`);
    return response.data;
  }

  async createProcessDefinition(
    data: CreateProcessDefinitionRequest
  ): Promise<ApiResponse<ProcessDefinition>> {
    const response = await this.client.post('/processes', data);
    return response.data;
  }

  async updateProcessDefinition(
    id: string,
    data: UpdateProcessDefinitionRequest
  ): Promise<ApiResponse<ProcessDefinition>> {
    const response = await this.client.put(`/processes/${id}`, data);
    return response.data;
  }

  async deleteProcessDefinition(id: string): Promise<ApiResponse<void>> {
    const response = await this.client.delete(`/processes/${id}`);
    return response.data;
  }

  // Process Instances
  private readonly statusMap: Record<string, string> = {
    running: 'RUNNING',
    completed: 'COMPLETED',
    suspended: 'SUSPENDED',
    error: 'ERROR',
  };

  async getProcessInstances(options?: {
    definitionId?: string;
    page?: number;
    pageSize?: number;
    status?: string;
  }): Promise<ApiResponse<PaginatedResponse<ProcessInstance>>> {
    const params = {
      ...(options?.definitionId ? { definition_id: options.definitionId } : {}),
      ...(options?.page ? { page: options.page } : {}),
      ...(options?.pageSize ? { page_size: options.pageSize } : {}),
      ...(options?.status ? { status: this.statusMap[options.status] } : {}),
    };
    const response = await this.client.get('/instances', { params });
    return response.data;
  }

  async getProcessInstance(id: string): Promise<ApiResponse<ProcessInstance>> {
    const response = await this.client.get(`/instances/${id}`);
    return response.data;
  }

  async startProcessInstance(
    data: StartProcessInstanceRequest
  ): Promise<ApiResponse<ProcessInstance>> {
    const response = await this.client.post('/instances', data);
    return response.data;
  }

  async suspendProcessInstance(
    id: string
  ): Promise<ApiResponse<ProcessInstance>> {
    const response = await this.client.post(`/instances/${id}/suspend`);
    return response.data;
  }

  async resumeProcessInstance(
    id: string
  ): Promise<ApiResponse<ProcessInstance>> {
    const response = await this.client.post(`/instances/${id}/resume`);
    return response.data;
  }

  async getInstanceActivities(id: string): Promise<ApiResponse<ActivityLog[]>> {
    const response = await this.client.get(`/instances/${id}/activities`);
    return response.data;
  }

  async getInstanceTokens(id: string): Promise<
    ApiResponse<
      {
        nodeId: string;
        state: string;
        scopeId?: string;
        data?: Record<string, unknown>;
      }[]
    >
  > {
    const response = await this.client.get(`/instances/${id}/tokens`);
    return response.data;
  }

  // Scripts
  async getScripts(processDefId: string): Promise<ApiResponse<Script[]>> {
    const response = await this.client.get(
      `/processes/${processDefId}/scripts`
    );
    return response.data;
  }

  async getScript(
    processDefId: string,
    nodeId: string
  ): Promise<ApiResponse<Script>> {
    const response = await this.client.get(
      `/processes/${processDefId}/scripts/${nodeId}`
    );
    return response.data;
  }

  async updateScript(
    processDefId: string,
    nodeId: string,
    data: UpdateScriptRequest
  ): Promise<ApiResponse<Script>> {
    const response = await this.client.put(
      `/processes/${processDefId}/scripts/${nodeId}`,
      data
    );
    return response.data;
  }

  // Statistics
  async getProcessStats(): Promise<ApiResponse<ProcessStats>> {
    const response = await this.client.get('/stats');
    return response.data;
  }
}

// Create a singleton instance
const apiService = new ApiService();

export default apiService;
