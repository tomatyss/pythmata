import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES, ERROR_MESSAGES } from '@/constants';
import authService from '@/services/auth';
import type { LoginCredentials, RegisterData, User } from '@/types/auth';

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  // Load user on mount
  useEffect(() => {
    const loadUser = async () => {
      try {
        if (authService.isAuthenticated()) {
          const userData = await authService.getCurrentUser();
          setUser(userData);
        }
      } catch (err) {
        console.error('Failed to load user:', err);
        // Clear token if unauthorized
        if (
          err instanceof Error &&
          err.message === ERROR_MESSAGES.UNAUTHORIZED
        ) {
          authService.logout();
        }
      } finally {
        setLoading(false);
      }
    };

    loadUser();
  }, []);

  const login = useCallback(
    async (credentials: LoginCredentials) => {
      setError(null);
      try {
        await authService.login(credentials);
        const userData = await authService.getCurrentUser();
        setUser(userData);
        navigate(ROUTES.DASHBOARD);
      } catch (err) {
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError(ERROR_MESSAGES.GENERIC);
        }
        throw err;
      }
    },
    [navigate]
  );

  const register = useCallback(
    async (data: RegisterData) => {
      setError(null);
      try {
        await authService.register(data);
        // After registration, log the user in
        await login({ username: data.email, password: data.password });
      } catch (err) {
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError(ERROR_MESSAGES.GENERIC);
        }
        throw err;
      }
    },
    [login]
  );

  const logout = useCallback(async () => {
    try {
      await authService.logout();
      setUser(null);
      navigate(ROUTES.LOGIN);
    } catch (err) {
      console.error('Logout error:', err);
      // Still clear user data even if logout request fails
      setUser(null);
      navigate(ROUTES.LOGIN);
    }
  }, [navigate]);

  return {
    user,
    loading,
    error,
    isAuthenticated: authService.isAuthenticated(),
    login,
    register,
    logout,
  };
}
