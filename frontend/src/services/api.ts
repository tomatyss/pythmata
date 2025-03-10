import { AxiosInstance, AxiosResponse } from 'axios';
import axiosInstance from '@/lib/axios';
import { ApiError } from '@/lib/errors';
import { convertKeysToCamel, convertKeysToSnake } from '@/utils/case';
import { API_ENDPOINTS } from '@/constants';
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

// Chat and LLM types
interface ChatSession {
  id: string;
  processDefinitionId: string;
  title: string;
  createdAt: string;
  updatedAt: string;
}

interface ChatMessage {
  id: string;
  role: string;
  content: string;
  xmlContent?: string;
  model?: string;
  createdAt: string;
}

interface ChatRequest {
  messages: Array<{ role: string; content: string }>;
  processId?: string;
  currentXml?: string;
  model?: string;
  sessionId?: string;
}

interface ChatResponse {
  message: string;
  xml?: string;
  model: string;
  sessionId?: string;
}

interface XmlGenerationRequest {
  description: string;
  model?: string;
}

interface XmlModificationRequest {
  request: string;
  currentXml: string;
  model?: string;
}

interface XmlResponse {
  xml: string;
  explanation: string;
}

// Define a type for service tasks
interface ServiceTask {
  name: string;
  description: string;
  properties: Array<{
    name: string;
    label: string;
    type: string;
    required: boolean;
    default?: unknown;
    options?: string[];
    description?: string;
  }>;
}

class ApiService {
  private client: AxiosInstance;

  constructor() {
    // Use the existing axios instance that's already configured with auth token
    this.client = axiosInstance;

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
    // Create common params object without definitionId
    const params = {
      ...(options?.page ? { page: options.page } : {}),
      ...(options?.pageSize ? { page_size: options.pageSize } : {}),
      ...(options?.status ? { status: this.statusMap[options.status] } : {}),
    };

    // If definitionId is provided, use the process-specific endpoint
    if (options?.definitionId) {
      try {
        // Use the endpoint from constants that matches the frontend route
        const response = await this.client.get(
          API_ENDPOINTS.PROCESS.INSTANCES(options.definitionId),
          { params }
        );
        return response.data;
      } catch (error) {
        // If the new endpoint fails, fall back to the original endpoint
        console.error(
          'Failed to fetch instances from process-specific endpoint, falling back to generic endpoint',
          error
        );
        return this.client
          .get('/instances', {
            params: {
              ...params,
              definition_id: options.definitionId,
            },
          })
          .then((response) => response.data);
      }
    }

    // If no definitionId, use the original endpoint
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

  // Service Tasks
  async getServiceTasks(): Promise<ApiResponse<ServiceTask[]>> {
    try {
      const response = await this.client.get('/services/tasks');

      // Ensure the response is properly formatted
      if (Array.isArray(response.data)) {
        return { data: response.data };
      } else if (response.data && Array.isArray(response.data.data)) {
        return response.data;
      } else {
        console.error('Invalid service tasks response format:', response.data);
        return { data: [] };
      }
    } catch (error) {
      console.error('Error fetching service tasks:', error);
      throw error;
    }
  }

  // Chat and LLM methods
  async sendChatMessage(data: ChatRequest): Promise<ChatResponse> {
    const response = await this.client.post('/llm/chat', data);
    return response.data;
  }

  async generateXml(
    data: XmlGenerationRequest
  ): Promise<ApiResponse<XmlResponse>> {
    const response = await this.client.post('/llm/generate-xml', data);
    return response.data;
  }

  async modifyXml(
    data: XmlModificationRequest
  ): Promise<ApiResponse<XmlResponse>> {
    const response = await this.client.post('/llm/modify-xml', data);
    return response.data;
  }

  async createChatSession(data: {
    process_definition_id: string;
    title?: string;
  }): Promise<ChatSession> {
    const response = await this.client.post('/llm/sessions', data);
    return response.data;
  }

  async listChatSessions(processId: string): Promise<ChatSession[]> {
    const response = await this.client.get(`/llm/sessions/${processId}`);
    return response.data;
  }

  async getChatMessages(sessionId: string): Promise<ChatMessage[]> {
    try {
      console.warn(`Fetching chat messages for session: ${sessionId}`);

      // Use a query parameter approach to avoid path conflicts
      const url = `/llm/messages?session_id=${sessionId}`;
      console.warn(`API URL: ${url}`);

      const response = await this.client.get(url);
      console.warn(`API response:`, response.data);
      return response.data;
    } catch (error) {
      console.error(
        `Error fetching chat messages for session ${sessionId}:`,
        error
      );
      throw error;
    }
  }
}

// Create a singleton instance
const apiService = new ApiService();

export default apiService;
