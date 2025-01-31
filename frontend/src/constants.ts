// API Configuration
export const API_BASE_URL = '/api';
export const API_TIMEOUT = 30000; // 30 seconds

// Authentication
export const AUTH_TOKEN_KEY = 'pythmata_auth_token';
export const AUTH_REFRESH_TOKEN_KEY = 'pythmata_refresh_token';
export const TOKEN_EXPIRY_BUFFER = 300; // 5 minutes in seconds

// Pagination
export const DEFAULT_PAGE_SIZE = 10;
export const PAGE_SIZE_OPTIONS = [5, 10, 25, 50];

// WebSocket
export const WS_RECONNECT_INTERVAL = 5000; // 5 seconds
export const WS_MAX_RECONNECT_ATTEMPTS = 5;

// Process Status
export const PROCESS_STATUS = {
  RUNNING: 'RUNNING',
  COMPLETED: 'COMPLETED',
  SUSPENDED: 'SUSPENDED',
  ERROR: 'ERROR',
} as const;

// Process Status Colors
export const STATUS_COLORS = {
  [PROCESS_STATUS.RUNNING]: 'primary',
  [PROCESS_STATUS.COMPLETED]: 'success',
  [PROCESS_STATUS.SUSPENDED]: 'warning',
  [PROCESS_STATUS.ERROR]: 'error',
} as const;

// Process Variable Types
export const VARIABLE_TYPES = {
  STRING: 'string',
  NUMBER: 'number',
  BOOLEAN: 'boolean',
  OBJECT: 'object',
} as const;

// Script Execution
export const SCRIPT_TIMEOUT = 30000; // 30 seconds
export const MAX_SCRIPT_LENGTH = 10000; // characters

// Form Validation
export const VALIDATION = {
  NAME_MIN_LENGTH: 3,
  NAME_MAX_LENGTH: 50,
  DESCRIPTION_MAX_LENGTH: 500,
} as const;

// Date Formats
export const DATE_FORMAT = 'yyyy-MM-dd HH:mm:ss';
export const DATE_FORMAT_SHORT = 'yyyy-MM-dd';
export const TIME_FORMAT = 'HH:mm:ss';

// File Types
export const ALLOWED_BPMN_TYPES = [
  'application/xml',
  'text/xml',
  '.bpmn',
  '.xml',
];

// Error Messages
export const ERROR_MESSAGES = {
  GENERIC: 'An error occurred. Please try again.',
  NETWORK: 'Network error. Please check your connection.',
  UNAUTHORIZED: 'You are not authorized to perform this action.',
  SESSION_EXPIRED: 'Your session has expired. Please log in again.',
  VALIDATION: 'Please check your input and try again.',
  NOT_FOUND: 'The requested resource was not found.',
  SERVER_ERROR: 'Server error. Please try again later.',
} as const;

// Success Messages
export const SUCCESS_MESSAGES = {
  PROCESS_CREATED: 'Process created successfully',
  PROCESS_UPDATED: 'Process updated successfully',
  PROCESS_DELETED: 'Process deleted successfully',
  INSTANCE_STARTED: 'Process instance started successfully',
  INSTANCE_SUSPENDED: 'Process instance suspended successfully',
  INSTANCE_RESUMED: 'Process instance resumed successfully',
  SCRIPT_UPDATED: 'Script updated successfully',
} as const;

// Routes
export const ROUTES = {
  HOME: '/',
  DASHBOARD: '/dashboard',
  PROCESSES: '/processes',
  NEW_PROCESS: '/processes/new',
  PROCESS_DETAILS: (id: string) => `/processes/${id}`,
  PROCESS_INSTANCE: (id: string, instanceId: string) =>
    `/processes/${id}/instances/${instanceId}`,
} as const;

// Local Storage Keys
export const STORAGE_KEYS = {
  THEME: 'pythmata_theme',
  LANGUAGE: 'pythmata_language',
  USER_PREFERENCES: 'pythmata_preferences',
} as const;

// Theme
export const DRAWER_WIDTH = 240;
export const HEADER_HEIGHT = 64;
export const FOOTER_HEIGHT = 48;
