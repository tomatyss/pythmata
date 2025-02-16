import axios, { AxiosInstance } from 'axios';
import { ApiError } from '@/lib/errors';
import {
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

    // Add response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
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
    definition_id?: string;
    page?: number;
    page_size?: number;
    status?: string;
  }): Promise<ApiResponse<PaginatedResponse<ProcessInstance>>> {
    const params = {
      ...(options?.definition_id
        ? { definition_id: options.definition_id }
        : {}),
      ...(options?.page ? { page: options.page } : {}),
      ...(options?.page_size ? { page_size: options.page_size } : {}),
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

  // Snake case response type for tokens
  async getInstanceTokens(
    id: string
  ): Promise<
    ApiResponse<
      {
        node_id: string;
        state: string;
        scope_id?: string;
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
