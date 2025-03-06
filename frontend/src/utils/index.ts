import { ProcessStatus } from '@/types/process';

// Get color based on process status
export const getStatusColor = (status: ProcessStatus): string => {
  switch (status) {
    case ProcessStatus.RUNNING:
      return '#2196f3'; // blue
    case ProcessStatus.COMPLETED:
      return '#4caf50'; // green
    case ProcessStatus.SUSPENDED:
      return '#ff9800'; // orange
    case ProcessStatus.ERROR:
      return '#f44336'; // red
    default:
      return '#9e9e9e'; // grey
  }
};

// Get human readable status text
export const getStatusText = (status: ProcessStatus): string => {
  return status.charAt(0).toUpperCase() + status.slice(1).toLowerCase();
};

// Format error message
export const formatError = (error: unknown): string => {
  if (error instanceof Error) {
    return error.message;
  }
  if (typeof error === 'string') {
    return error;
  }
  return 'An unknown error occurred';
};

// Debounce function
export const debounce = <T extends (...args: unknown[]) => void>(
  func: T,
  wait: number
): ((...args: Parameters<T>) => void) => {
  let timeout: NodeJS.Timeout;

  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
};

// Constants
export const POLLING_INTERVAL = 5000; // 5 seconds
export const MAX_RETRIES = 3;
export const DEFAULT_PAGE_SIZE = 10;

// Local storage keys
export const STORAGE_KEYS = {
  AUTH_TOKEN: 'pythmata_auth_token',
  USER_PREFERENCES: 'pythmata_user_prefs',
} as const;

// API endpoints
export const API_ENDPOINTS = {
  PROCESSES: '/processes',
  INSTANCES: '/instances',
  SCRIPTS: '/scripts',
  STATS: '/stats',
} as const;

// Validation
export const VALIDATION = {
  NAME_MIN_LENGTH: 3,
  NAME_MAX_LENGTH: 50,
  SCRIPT_MAX_LENGTH: 10000,
} as const;

// Error messages
export const ERROR_MESSAGES = {
  REQUIRED_FIELD: 'This field is required',
  INVALID_NAME: `Name must be between ${VALIDATION.NAME_MIN_LENGTH} and ${VALIDATION.NAME_MAX_LENGTH} characters`,
  INVALID_BPMN: 'Invalid BPMN XML format',
  SCRIPT_TOO_LONG: `Script cannot exceed ${VALIDATION.SCRIPT_MAX_LENGTH} characters`,
  NETWORK_ERROR: 'Network error. Please check your connection and try again.',
  SERVER_ERROR: 'Server error. Please try again later.',
} as const;

// Success messages
export const SUCCESS_MESSAGES = {
  PROCESS_CREATED: 'Process created successfully',
  PROCESS_UPDATED: 'Process updated successfully',
  PROCESS_DELETED: 'Process deleted successfully',
  INSTANCE_STARTED: 'Process instance started successfully',
  INSTANCE_SUSPENDED: 'Process instance suspended successfully',
  INSTANCE_RESUMED: 'Process instance resumed successfully',
  SCRIPT_UPDATED: 'Script updated successfully',
} as const;
