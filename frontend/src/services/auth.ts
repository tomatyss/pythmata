import axios, { AxiosError } from 'axios';
import {
  API_BASE_URL,
  API_ENDPOINTS,
  AUTH_TOKEN_KEY,
  ERROR_MESSAGES,
} from '@/constants';
import axiosInstance from '@/lib/axios';
import type {
  AuthResponse,
  LoginCredentials,
  RegisterData,
  User,
} from '@/types/auth';

class AuthService {
  /**
   * Login user and store token
   */
  async login(credentials: LoginCredentials): Promise<void> {
    try {
      // Create a function to serialize the data in the format FastAPI expects
      const serialize = (obj: Record<string, unknown>) => {
        const str = [];
        for (const p in obj) {
          if (Object.prototype.hasOwnProperty.call(obj, p)) {
            const value = obj[p];
            if (
              typeof value === 'string' ||
              typeof value === 'number' ||
              typeof value === 'boolean'
            ) {
              str.push(encodeURIComponent(p) + '=' + encodeURIComponent(value));
            }
          }
        }
        return str.join('&');
      };

      const data = {
        username: credentials.username,
        password: credentials.password,
      };

      const response = await axios.post<AuthResponse>(
        `${API_BASE_URL}${API_ENDPOINTS.AUTH.LOGIN}`,
        serialize(data),
        {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
        }
      );

      localStorage.setItem(AUTH_TOKEN_KEY, response.data.access_token);
    } catch (err: unknown) {
      if (err instanceof AxiosError) {
        if (err.response?.status === 401) {
          throw new Error(ERROR_MESSAGES.INVALID_CREDENTIALS);
        } else if (err.response?.status === 422) {
          console.error(
            'Validation error details:',
            JSON.stringify(err.response.data, null, 2)
          );

          // Extract specific validation errors if available
          if (
            err.response.data?.detail &&
            Array.isArray(err.response.data.detail)
          ) {
            const errorDetails = err.response.data.detail
              .map(
                (detail: { loc: string[]; msg: string }) =>
                  `${detail.loc.join('.')}: ${detail.msg}`
              )
              .join(', ');
            throw new Error(`Validation error: ${errorDetails}`);
          } else {
            throw new Error(ERROR_MESSAGES.VALIDATION);
          }
        }
      }
      console.error('Login error:', err);
      throw new Error(ERROR_MESSAGES.GENERIC);
    }
  }

  /**
   * Register a new user
   */
  async register(data: RegisterData): Promise<User> {
    try {
      const response = await axiosInstance.post<User>(
        API_ENDPOINTS.AUTH.REGISTER,
        data,
        {
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );
      return response.data;
    } catch (err: unknown) {
      if (err instanceof AxiosError) {
        if (err.response?.status === 400) {
          throw new Error(ERROR_MESSAGES.EMAIL_EXISTS);
        } else if (err.response?.status === 422) {
          console.error('Validation error:', err.response.data);
          throw new Error(ERROR_MESSAGES.VALIDATION);
        }
      }
      console.error('Registration error:', err);
      throw new Error(ERROR_MESSAGES.GENERIC);
    }
  }

  /**
   * Get current user profile
   */
  async getCurrentUser(): Promise<User> {
    try {
      const response = await axiosInstance.get<User>(API_ENDPOINTS.AUTH.ME, {
        headers: {
          'Content-Type': 'application/json',
        },
      });
      return response.data;
    } catch (err: unknown) {
      if (err instanceof AxiosError) {
        if (err.response?.status === 401) {
          throw new Error(ERROR_MESSAGES.UNAUTHORIZED);
        } else if (err.response?.status === 422) {
          console.error('Validation error:', err.response.data);
          throw new Error(ERROR_MESSAGES.VALIDATION);
        }
      }
      console.error('Get user error:', err);
      throw new Error(ERROR_MESSAGES.GENERIC);
    }
  }

  /**
   * Logout user - removes token from storage
   * Uses try-finally to ensure token is removed even if server request fails
   */
  async logout(): Promise<void> {
    try {
      await axiosInstance.post(API_ENDPOINTS.AUTH.LOGOUT, null, {
        headers: {
          'Content-Type': 'application/json',
        },
      });
    } catch (err) {
      console.error('Logout server request failed:', err);
      // We continue to remove the token even if the server request fails
    } finally {
      localStorage.removeItem(AUTH_TOKEN_KEY);
    }
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    return !!localStorage.getItem(AUTH_TOKEN_KEY);
  }

  /**
   * Get authentication token
   */
  getToken(): string | null {
    return localStorage.getItem(AUTH_TOKEN_KEY);
  }
}

// Create singleton instance
const authService = new AuthService();
export default authService;
