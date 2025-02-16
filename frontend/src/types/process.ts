// Variable Definition Types
export interface ProcessVariableValidation {
  min?: number;
  max?: number;
  pattern?: string;
  options?: (string | number)[];
}

export interface ProcessVariableDefinition {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'date';
  required: boolean;
  defaultValue?: string | number | boolean | Date;
  validation?: ProcessVariableValidation;
  label: string;
  description?: string;
}

// Process Definition Types
export interface ProcessDefinition {
  id: string;
  name: string;
  version: number;
  bpmnXml: string;
  variableDefinitions: ProcessVariableDefinition[];
  activeInstances: number;
  totalInstances: number;
  createdAt: string;
  updatedAt: string;
}

export interface ProcessStats {
  totalInstances: number;
  statusCounts: Record<ProcessStatus, number>;
  averageCompletionTime: number | null;
  errorRate: number;
  activeInstances: number;
}

// Process Instance Types
export enum ProcessStatus {
  RUNNING = 'RUNNING',
  COMPLETED = 'COMPLETED',
  SUSPENDED = 'SUSPENDED',
  ERROR = 'ERROR',
}

export interface ProcessInstance {
  id: string;
  definitionId: string;
  definitionName: string;
  status: ProcessStatus;
  startTime: string;
  endTime?: string;
  createdAt: string;
  updatedAt: string;
}

export interface ProcessVariable {
  id: string;
  instanceId: string;
  name: string;
  valueType: string;
  valueData: string | number | boolean | null;
  scopeId?: string;
  version: number;
  createdAt: string;
}

// Activity Types
export interface ActivityLog {
  id: string;
  instanceId: string;
  nodeId: string;
  activityType: string;
  status: string;
  startTime: string;
  endTime?: string;
  result?: Record<string, unknown>;
  errorMessage?: string;
  createdAt: string;
}

// Script Types
export interface Script {
  id: string;
  processDefId: string;
  nodeId: string;
  content: string;
  version: number;
  createdAt: string;
  updatedAt: string;
}

export interface ScriptExecution {
  id: string;
  scriptId: string;
  instanceId: string;
  status: string;
  startTime: string;
  endTime?: string;
  result?: Record<string, unknown>;
  errorMessage?: string;
  createdAt: string;
}

export interface Token {
  nodeId: string;
  state: string;
  scopeId?: string;
  data?: Record<string, unknown>;
}

// API Response Types
export interface ApiResponse<T> {
  data: T;
  message?: string;
  error?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

// API Request Types
export interface CreateProcessDefinitionRequest {
  name: string;
  bpmnXml: string;
  version?: number; // Optional, defaults to 1
  variableDefinitions?: ProcessVariableDefinition[];
}

export interface UpdateProcessDefinitionRequest {
  name?: string;
  bpmnXml?: string;
  version?: number; // Optional, auto-increments if not provided
  variableDefinitions?: ProcessVariableDefinition[];
}

export interface ProcessVariableValue {
  type: 'string' | 'number' | 'boolean' | 'date';
  value: string | number | boolean | Date | null;
}

export interface StartProcessInstanceRequest {
  definitionId: string;
  variables?: Record<string, ProcessVariableValue>;
}

export interface UpdateScriptRequest {
  content: string;
}
