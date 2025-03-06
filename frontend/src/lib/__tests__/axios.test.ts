import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { AUTH_TOKEN_KEY } from '@/constants';

// Setup mock interceptors for testing
const mockRequestUse = vi.fn();
const mockResponseUse = vi.fn();

// Mock axios
vi.mock('axios', () => {
  return {
    default: {
      create: vi.fn(() => ({
        interceptors: {
          request: { use: mockRequestUse, eject: vi.fn() },
          response: { use: mockResponseUse, eject: vi.fn() },
        },
        defaults: {},
      })),
    },
  };
});

describe('Axios Instance', () => {
  // Initialize with dummy functions to satisfy TypeScript
  let requestInterceptor: (
    config: import('axios').AxiosRequestConfig
  ) => import('axios').AxiosRequestConfig = (config) => config;

  beforeEach(() => {
    // Clear mocks and localStorage
    vi.clearAllMocks();
    localStorage.clear();

    // Setup mock call expectations
    mockRequestUse.mockImplementation((fn) => {
      requestInterceptor = fn;
      return { use: mockRequestUse };
    });

    // We need to import the module again to trigger the interceptor setup
    vi.resetModules();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Request Interceptor', () => {
    it('should not add auth header for registration endpoint', () => {
      // Set token in localStorage
      localStorage.setItem(AUTH_TOKEN_KEY, 'test-token');

      // Create a mock config for registration endpoint
      const mockConfig = {
        url: '/auth/register',
        headers: {},
      };

      // Call the interceptor directly with our mock config
      const result = requestInterceptor(mockConfig);

      // Assert no Authorization header was added
      expect(result.headers?.Authorization).toBeUndefined();
    });

    it('should not add auth header for login endpoint', () => {
      // Set token in localStorage
      localStorage.setItem(AUTH_TOKEN_KEY, 'test-token');

      // Create a mock config for login endpoint
      const mockConfig = {
        url: '/auth/login',
        headers: {},
      };

      // Call the interceptor directly with our mock config
      const result = requestInterceptor(mockConfig);

      // Assert no Authorization header was added
      expect(result.headers?.Authorization).toBeUndefined();
    });

    it('should add auth header for other endpoints when token exists', () => {
      // Set token in localStorage
      localStorage.setItem(AUTH_TOKEN_KEY, 'test-token');

      // Create a mock config for a non-auth endpoint
      const mockConfig = {
        url: '/api/some-endpoint',
        headers: {},
      };

      // Call the interceptor directly with our mock config
      const result = requestInterceptor(mockConfig);

      // Assert Authorization header was added
      expect(result.headers?.Authorization).toBe('Bearer test-token');
    });

    it('should not add auth header when token does not exist', () => {
      // Create a mock config
      const mockConfig = {
        url: '/api/some-endpoint',
        headers: {},
      };

      // Call the interceptor directly with our mock config
      const result = requestInterceptor(mockConfig);

      // Assert no Authorization header was added
      expect(result.headers?.Authorization).toBeUndefined();
    });
  });
});
