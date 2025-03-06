import { vi } from 'vitest';

const mockPost = vi.hoisted(() => vi.fn());
const mockGet = vi.hoisted(() => vi.fn());

vi.mock('axios', async () => {
  const actual = await vi.importActual('axios');
  return {
    ...actual,
    default: {
      create: vi.fn().mockReturnValue({
        defaults: {},
        interceptors: {
          request: { use: vi.fn(), eject: vi.fn() },
          response: { use: vi.fn(), eject: vi.fn() },
        },
        get: mockGet,
        post: mockPost,
      }),
    },
  };
});

import { describe, it, expect, beforeEach } from 'vitest';
import { AxiosError } from 'axios';
import authService from '../auth';
import { AUTH_TOKEN_KEY, ERROR_MESSAGES } from '@/constants';
import type { User } from '@/types/auth';

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

      expect(mockPost).toHaveBeenCalledWith(
        '/auth/login',
        expect.any(FormData)
      );
      expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBe('test-token');
    });

    it('should throw error on invalid credentials', async () => {
      const error = new AxiosError();
      error.response = { status: 401 } as import('axios').AxiosResponse;
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
      mockPost.mockResolvedValueOnce({ data: mockUser });

      const result = await authService.register(registerData);

      expect(mockPost).toHaveBeenCalledWith('/auth/register', registerData);
      // Authorization header should not be included for registration
      expect(result).toEqual(mockUser);
    });

    it('should throw error on duplicate email', async () => {
      const error = new AxiosError();
      error.response = { status: 400 } as import('axios').AxiosResponse;
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
      mockGet.mockResolvedValueOnce({ data: mockUser });

      const result = await authService.getCurrentUser();

      expect(mockGet).toHaveBeenCalledWith('/auth/me');
      expect(result).toEqual(mockUser);
    });

    it('should throw error on unauthorized access', async () => {
      const error = new AxiosError();
      error.response = { status: 401 } as import('axios').AxiosResponse;
      mockGet.mockRejectedValueOnce(error);

      await expect(authService.getCurrentUser()).rejects.toThrow(
        ERROR_MESSAGES.UNAUTHORIZED
      );
    });
  });

  describe('logout', () => {
    it('should clear token on logout', async () => {
      localStorage.setItem(AUTH_TOKEN_KEY, 'test-token');
      mockPost.mockResolvedValueOnce({});

      await authService.logout();

      expect(mockPost).toHaveBeenCalledWith('/auth/logout');
      expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBeNull();
    });

    it('should clear token even if request fails', async () => {
      localStorage.setItem(AUTH_TOKEN_KEY, 'test-token');
      mockPost.mockRejectedValueOnce(new Error('Request failed'));

      await expect(authService.logout()).rejects.toThrow('Request failed');

      expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBeNull();
    });
  });
});
