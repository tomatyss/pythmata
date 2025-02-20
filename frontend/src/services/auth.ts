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
      const formData = new FormData();
      formData.append('username', credentials.username);
      formData.append('password', credentials.password);

      const response = await axiosInstance.post<AuthResponse>(
        API_ENDPOINTS.AUTH.LOGIN,
        formData
      );

      localStorage.setItem(AUTH_TOKEN_KEY, response.data.access_token);
    } catch (err: unknown) {
      if (err instanceof AxiosError) {
        if (err.response?.status === 401) {
          throw new Error(ERROR_MESSAGES.INVALID_CREDENTIALS);
        }
      }
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
        }
      }
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
        }
      }
      throw new Error(ERROR_MESSAGES.GENERIC);
    }
  }

  /**
   * Logout user
   */
  async logout(): Promise<void> {
    try {
      await axiosInstance.post(API_ENDPOINTS.AUTH.LOGOUT);
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
