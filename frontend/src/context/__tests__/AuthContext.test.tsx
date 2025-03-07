import { vi, describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { useNavigate } from 'react-router-dom';
import { AuthProvider, useAuthContext } from '../AuthContext';
import type { User } from '@/types/auth';
import type { AuthContextType } from '../auth-utils';

// Mock react-router-dom
vi.mock('react-router-dom', () => ({
  useNavigate: vi.fn(),
}));

// Mock useAuth hook with proper typing
const defaultMockAuth: AuthContextType = {
  user: null,
  loading: false,
  error: null,
  isAuthenticated: false,
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
};

const mockUseAuth = vi.fn(() => defaultMockAuth);

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => mockUseAuth(),
}));

describe('AuthContext', () => {
  const mockNavigate = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (useNavigate as jest.Mock).mockReturnValue(mockNavigate);
    mockUseAuth.mockReturnValue(defaultMockAuth);
  });

  const TestComponent = () => {
    const auth = useAuthContext();
    return (
      <div>
        <div data-testid="loading">{auth.loading.toString()}</div>
        <div data-testid="authenticated">{auth.isAuthenticated.toString()}</div>
        <div data-testid="user">{auth.user?.email || 'no user'}</div>
        <div data-testid="error">{auth.error || 'no error'}</div>
      </div>
    );
  };

  it('should provide auth context to children', () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    expect(screen.getByTestId('loading')).toHaveTextContent('false');
    expect(screen.getByTestId('authenticated')).toHaveTextContent('false');
    expect(screen.getByTestId('user')).toHaveTextContent('no user');
    expect(screen.getByTestId('error')).toHaveTextContent('no error');
  });

  it('should throw error when used outside provider', () => {
    // Suppress console.error for this test
    const consoleSpy = vi.spyOn(console, 'error');
    consoleSpy.mockImplementation(() => {});

    expect(() => render(<TestComponent />)).toThrow(
      'useAuthContext must be used within an AuthProvider'
    );

    consoleSpy.mockRestore();
  });

  it('should update context when user logs in', async () => {
    const mockUser: User = {
      id: '1',
      email: 'test@example.com',
      full_name: 'Test User',
      is_active: true,
      roles: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    const mockAuthWithUser: AuthContextType = {
      ...defaultMockAuth,
      user: mockUser,
      isAuthenticated: true,
    };

    mockUseAuth.mockReturnValue(mockAuthWithUser);

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toHaveTextContent('true');
      expect(screen.getByTestId('user')).toHaveTextContent(mockUser.email);
    });
  });

  it('should show loading state', () => {
    mockUseAuth.mockReturnValue({
      ...defaultMockAuth,
      loading: true,
    });

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    expect(screen.getByTestId('loading')).toHaveTextContent('true');
  });

  it('should show error state', () => {
    mockUseAuth.mockReturnValue({
      ...defaultMockAuth,
      error: 'Authentication failed',
    });

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    expect(screen.getByTestId('error')).toHaveTextContent(
      'Authentication failed'
    );
  });
});
