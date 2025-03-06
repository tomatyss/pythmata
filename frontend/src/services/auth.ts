import { AxiosError } from 'axios';
import { API_ENDPOINTS, AUTH_TOKEN_KEY, ERROR_MESSAGES } from '@/constants';
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
      // Use URLSearchParams instead of FormData for OAuth2 password flow
      const params = new URLSearchParams();
      params.append('username', credentials.username);
      params.append('password', credentials.password);

      const response = await axiosInstance.post<AuthResponse>(
        API_ENDPOINTS.AUTH.LOGIN,
        params,
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
          console.error('Validation error:', err.response.data);
          throw new Error(ERROR_MESSAGES.VALIDATION);
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
        data
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
      const response = await axiosInstance.get<User>(API_ENDPOINTS.AUTH.ME);
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
      await axiosInstance.post(API_ENDPOINTS.AUTH.LOGOUT);
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
