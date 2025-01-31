import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { API_BASE_URL, API_TIMEOUT, AUTH_TOKEN_KEY, ERROR_MESSAGES } from '@/constants';

// Create axios instance with default config
const axiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
axiosInstance.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Get token from storage
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    
    // Add auth header if token exists
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

// Response interceptor
axiosInstance.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    // Handle specific error cases
    if (error.response) {
      switch (error.response.status) {
        case 401:
          // Handle unauthorized (could add token refresh logic here)
          localStorage.removeItem(AUTH_TOKEN_KEY);
          window.location.href = '/login';
          return Promise.reject(new Error(ERROR_MESSAGES.UNAUTHORIZED));

        case 403:
          return Promise.reject(new Error(ERROR_MESSAGES.UNAUTHORIZED));

        case 404:
          return Promise.reject(new Error(ERROR_MESSAGES.NOT_FOUND));

        case 500:
          return Promise.reject(new Error(ERROR_MESSAGES.SERVER_ERROR));

        default:
          return Promise.reject(
            new Error(
              (error.response.data && typeof error.response.data === 'object' && 'message' in error.response.data)
                ? String(error.response.data.message)
                : ERROR_MESSAGES.GENERIC
            )
          );
      }
    }

    // Handle network errors
    if (error.message === 'Network Error') {
      return Promise.reject(new Error(ERROR_MESSAGES.NETWORK));
    }

    // Handle timeout
    if (error.code === 'ECONNABORTED') {
      return Promise.reject(new Error('Request timed out. Please try again.'));
    }

    return Promise.reject(error);
  }
);

export default axiosInstance;

// API response types
export interface ApiResponse<T = any> {
  data: T;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

// Error handling helper
export const handleApiError = (error: unknown): string => {
  if (error instanceof Error) {
    return error.message;
  }
  return ERROR_MESSAGES.GENERIC;
};
