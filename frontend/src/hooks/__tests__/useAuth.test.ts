import { vi, describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../useAuth';
import authService from '@/services/auth';
import { ROUTES } from '@/constants';
import type { User } from '@/types/auth';

// Mock dependencies
vi.mock('react-router-dom', () => ({
  useNavigate: vi.fn(),
}));

vi.mock('@/services/auth', () => ({
  default: {
    login: vi.fn(),
    register: vi.fn(),
    getCurrentUser: vi.fn(),
    logout: vi.fn(),
    isAuthenticated: vi.fn(),
  },
}));

describe('useAuth', () => {
  const mockNavigate = vi.fn();
  const mockUser: User = {
    id: '1',
    email: 'test@example.com',
    full_name: 'Test User',
    is_active: true,
    roles: [],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (useNavigate as jest.Mock).mockReturnValue(mockNavigate);
    (authService.isAuthenticated as jest.Mock).mockReturnValue(false);
  });

  it('should initialize with default values', () => {
    const { result } = renderHook(() => useAuth());

    expect(result.current.user).toBeNull();
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
  });

  it('should load user on mount when authenticated', async () => {
    (authService.isAuthenticated as jest.Mock).mockReturnValue(true);
    (authService.getCurrentUser as jest.Mock).mockResolvedValue(mockUser);

    const { result } = renderHook(() => useAuth());

    // Should start loading
    expect(result.current.loading).toBe(true);

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    expect(result.current.user).toEqual(mockUser);
    expect(result.current.loading).toBe(false);
    expect(result.current.isAuthenticated).toBe(true);
  });

  it('should handle login success', async () => {
    const credentials = { username: 'test@example.com', password: 'password' };
    (authService.login as jest.Mock).mockResolvedValue(undefined);
    (authService.getCurrentUser as jest.Mock).mockResolvedValue(mockUser);

    const { result } = renderHook(() => useAuth());

    await act(async () => {
      await result.current.login(credentials);
    });

    expect(authService.login).toHaveBeenCalledWith(credentials);
    expect(result.current.user).toEqual(mockUser);
    expect(result.current.error).toBeNull();
    expect(mockNavigate).toHaveBeenCalledWith(ROUTES.DASHBOARD);
  });

  it('should handle login failure', async () => {
    const credentials = { username: 'test@example.com', password: 'wrong' };
    const error = new Error('Invalid credentials');
    (authService.login as jest.Mock).mockRejectedValue(error);

    const { result } = renderHook(() => useAuth());

    await act(async () => {
      try {
        await result.current.login(credentials);
      } catch {
        // Expected error
      }
    });

    expect(authService.login).toHaveBeenCalledWith(credentials);
    expect(result.current.user).toBeNull();
    expect(result.current.error).toBe(error.message);
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it('should handle registration success', async () => {
    const registerData = {
      email: 'new@example.com',
      password: 'password',
      full_name: 'New User',
    };
    (authService.register as jest.Mock).mockResolvedValue(mockUser);
    (authService.login as jest.Mock).mockResolvedValue(undefined);
    (authService.getCurrentUser as jest.Mock).mockResolvedValue(mockUser);

    const { result } = renderHook(() => useAuth());

    await act(async () => {
      await result.current.register(registerData);
    });

    expect(authService.register).toHaveBeenCalledWith(registerData);
    expect(authService.login).toHaveBeenCalledWith({
      username: registerData.email,
      password: registerData.password,
    });
    expect(result.current.user).toEqual(mockUser);
    expect(result.current.error).toBeNull();
    expect(mockNavigate).toHaveBeenCalledWith(ROUTES.DASHBOARD);
  });

  it('should handle registration failure', async () => {
    const registerData = {
      email: 'existing@example.com',
      password: 'password',
      full_name: 'Existing User',
    };
    const error = new Error('Email already exists');
    (authService.register as jest.Mock).mockRejectedValue(error);

    const { result } = renderHook(() => useAuth());

    await act(async () => {
      try {
        await result.current.register(registerData);
      } catch {
        // Expected error
      }
    });

    expect(authService.register).toHaveBeenCalledWith(registerData);
    expect(result.current.user).toBeNull();
    expect(result.current.error).toBe(error.message);
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it('should handle logout', async () => {
    const { result } = renderHook(() => useAuth());

    await act(async () => {
      await result.current.logout();
    });

    expect(authService.logout).toHaveBeenCalled();
    expect(result.current.user).toBeNull();
    expect(mockNavigate).toHaveBeenCalledWith(ROUTES.LOGIN);
  });

  it('should handle logout failure gracefully', async () => {
    const error = new Error('Logout failed');
    (authService.logout as jest.Mock).mockRejectedValue(error);

    const { result } = renderHook(() => useAuth());

    await act(async () => {
      await result.current.logout();
    });

    expect(authService.logout).toHaveBeenCalled();
    expect(result.current.user).toBeNull();
    expect(mockNavigate).toHaveBeenCalledWith(ROUTES.LOGIN);
  });
});
