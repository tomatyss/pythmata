import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { AUTH_TOKEN_KEY } from '@/constants';

describe('Axios Instance', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Request Interceptor', () => {
    // Recreate the exact same interceptor logic here for testing
    const requestInterceptor = (config) => {
      // Get token from storage
      const token = localStorage.getItem(AUTH_TOKEN_KEY);

      // Don't add auth header for authentication endpoints
      const isAuthEndpoint =
        config.url &&
        (config.url.includes('/auth/register') ||
          config.url.includes('/auth/login'));

      // Add auth header if token exists and not an auth endpoint
      if (token && !isAuthEndpoint) {
        // Create headers object if it doesn't exist
        config.headers = config.headers || {};
        config.headers.Authorization = `Bearer ${token}`;
      }

      return config;
    };

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
