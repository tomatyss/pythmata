import { vi, describe, it, expect, beforeEach } from 'vitest';
import { AUTH_TOKEN_KEY, ERROR_MESSAGES } from '@/constants';
import type { User } from '@/types/auth';

// Use vi.hoisted() to ensure the mock functions are hoisted to the top
const mockPost = vi.hoisted(() => vi.fn());
const mockGet = vi.hoisted(() => vi.fn());

// This mock will be hoisted to the top of the file by Vitest
vi.mock('@/lib/axios', () => {
  return {
    default: {
      get: mockGet,
      post: mockPost,
      interceptors: {
        request: { use: vi.fn(), eject: vi.fn() },
        response: { use: vi.fn(), eject: vi.fn() },
      },
    },
  };
});

import { AxiosResponse } from 'axios';
vi.mock('axios', async () => {
  const { AxiosError } = await import('axios');
  return {
    default: {
      post: mockPost,
    },
    AxiosError, // Include the AxiosError export dynamically
  };
});

// Now import the service
import authService from '../auth';

describe('AuthService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  describe('login', () => {
    const credentials = {
      username: 'test@example.com',
      password: 'password123',
    };

    it('should store token on successful login', async () => {
      const mockResponse = {
        data: { access_token: 'test-token', token_type: 'bearer' },
      };
      mockPost.mockResolvedValueOnce(mockResponse);

      await authService.login(credentials);

      // Verify that localStorage has stored the token
      expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBe('test-token');
    });

    it('should throw error on invalid credentials', async () => {
      const { AxiosError } = await import('axios');
      const error = new AxiosError();
      error.response = {
        data: null,
        status: 401,
        statusText: 'Unauthorized',
        headers: {},
        config: {},
      } as AxiosResponse;
      mockPost.mockRejectedValueOnce(error);

      await expect(authService.login(credentials)).rejects.toThrow(
        ERROR_MESSAGES.INVALID_CREDENTIALS
      );
    });
  });

  describe('register', () => {
    const registerData = {
      email: 'test@example.com',
      password: 'password123',
      full_name: 'Test User',
    };

    it('should return user data on successful registration', async () => {
      const mockUser: User = {
        id: '1',
        email: registerData.email,
        full_name: registerData.full_name,
        is_active: true,
        roles: [],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      mockPost.mockResolvedValueOnce({
        data: mockUser,
      });

      const result = await authService.register(registerData);

      // Update expectation to include all arguments
      expect(mockPost).toHaveBeenCalledWith('/auth/register', registerData, {
        headers: {
          'Content-Type': 'application/json',
        },
      });
      expect(result).toEqual(mockUser);
    });

    it('should throw error on duplicate email', async () => {
      const { AxiosError } = await import('axios');
      const error = new AxiosError();
      error.response = {
        data: null,
        status: 400,
        statusText: 'Bad Request',
        headers: {},
        config: {},
      } as AxiosResponse;
      mockPost.mockRejectedValueOnce(error);

      await expect(authService.register(registerData)).rejects.toThrow(
        ERROR_MESSAGES.EMAIL_EXISTS
      );
    });
  });

  describe('getCurrentUser', () => {
    it('should return current user data', async () => {
      const mockUser: User = {
        id: '1',
        email: 'test@example.com',
        full_name: 'Test User',
        is_active: true,
        roles: [],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      mockGet.mockResolvedValueOnce({
        data: mockUser,
      });

      const result = await authService.getCurrentUser();

      // Update expectation to include all arguments
      expect(mockGet).toHaveBeenCalledWith('/auth/me', {
        headers: {
          'Content-Type': 'application/json',
        },
      });
      expect(result).toEqual(mockUser);
    });

    it('should throw error on unauthorized access', async () => {
      const { AxiosError } = await import('axios');
      const error = new AxiosError();
      error.response = {
        data: null,
        status: 401,
        statusText: 'Unauthorized',
        headers: {},
        config: {},
      } as AxiosResponse;
      mockGet.mockRejectedValueOnce(error);

      await expect(authService.getCurrentUser()).rejects.toThrow(
        ERROR_MESSAGES.UNAUTHORIZED
      );
    });
  });

  describe('logout', () => {
    it('should clear token on logout', async () => {
      localStorage.setItem(AUTH_TOKEN_KEY, 'test-token');
      mockPost.mockResolvedValueOnce({
        data: {},
      });

      await authService.logout();

      // Update expectation to include all arguments
      expect(mockPost).toHaveBeenCalledWith('/auth/logout', null, {
        headers: {
          'Content-Type': 'application/json',
        },
      });
      expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBeNull();
    });

    it('should clear token even if request fails', async () => {
      localStorage.setItem(AUTH_TOKEN_KEY, 'test-token');
      mockPost.mockRejectedValueOnce(new Error('Request failed'));

      try {
        await authService.logout();
      } catch (error) {
        // We expect an error to be thrown
        expect((error as Error).message).toBe('Request failed');
      }

      expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBeNull();
    });
  });
});
