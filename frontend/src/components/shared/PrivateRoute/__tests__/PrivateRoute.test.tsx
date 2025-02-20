import { vi, describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { useLocation, Navigate } from 'react-router-dom';
import { PrivateRoute } from '../PrivateRoute';
import { useAuthContext } from '@/context/AuthContext';
import { ROUTES } from '@/constants';

// Mock react-router-dom
const mockNavigate = vi.fn();
vi.mock('react-router-dom', () => ({
    useLocation: vi.fn(),
    Navigate: vi.fn((props) => {
        mockNavigate(props);
        return null;
    }),
}));

// Mock AuthContext
vi.mock('@/context/AuthContext', () => ({
    useAuthContext: vi.fn(),
}));

describe('PrivateRoute', () => {
    const mockLocation = { pathname: '/protected' };
    const TestComponent = () => <div data-testid="protected-content">Protected Content</div>;

    beforeEach(() => {
        vi.clearAllMocks();
        (useLocation as jest.Mock).mockReturnValue(mockLocation);
        (useAuthContext as jest.Mock).mockReturnValue({
            loading: false,
            isAuthenticated: false,
        });
    });

    it('should render loading state', () => {
        (useAuthContext as jest.Mock).mockReturnValue({
            loading: true,
            isAuthenticated: false,
        });

        render(
            <PrivateRoute>
                <TestComponent />
            </PrivateRoute>
        );

        expect(screen.getByTestId('loading-state')).toBeInTheDocument();
        expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
    });

    it('should redirect to login when not authenticated', () => {
        render(
            <PrivateRoute>
                <TestComponent />
            </PrivateRoute>
        );

        expect(mockNavigate).toHaveBeenCalledWith({
            to: ROUTES.LOGIN,
            state: { from: mockLocation },
            replace: true,
        });
        expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
    });

    it('should render children when authenticated', () => {
        (useAuthContext as jest.Mock).mockReturnValue({
            loading: false,
            isAuthenticated: true,
        });

        render(
            <PrivateRoute>
                <TestComponent />
            </PrivateRoute>
        );

        expect(screen.getByTestId('protected-content')).toBeInTheDocument();
        expect(mockNavigate).not.toHaveBeenCalled();
    });

    it('should handle state transition from loading to authenticated', () => {
        // Initial loading state
        (useAuthContext as jest.Mock).mockReturnValue({
            loading: true,
            isAuthenticated: false,
        });

        const { rerender } = render(
            <PrivateRoute>
                <TestComponent />
            </PrivateRoute>
        );

        // Verify loading state
        expect(screen.getByTestId('loading-state')).toBeInTheDocument();
        expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();

        // Update to authenticated state
        (useAuthContext as jest.Mock).mockReturnValue({
            loading: false,
            isAuthenticated: true,
        });

        rerender(
            <PrivateRoute>
                <TestComponent />
            </PrivateRoute>
        );

        expect(screen.queryByTestId('loading-state')).not.toBeInTheDocument();
        expect(screen.getByTestId('protected-content')).toBeInTheDocument();
    });

    it('should handle state transition from loading to unauthenticated', () => {
        // Initial loading state
        (useAuthContext as jest.Mock).mockReturnValue({
            loading: true,
            isAuthenticated: false,
        });

        const { rerender } = render(
            <PrivateRoute>
                <TestComponent />
            </PrivateRoute>
        );

        // Verify loading state
        expect(screen.getByTestId('loading-state')).toBeInTheDocument();

        // Update to unauthenticated state
        (useAuthContext as jest.Mock).mockReturnValue({
            loading: false,
            isAuthenticated: false,
        });

        rerender(
            <PrivateRoute>
                <TestComponent />
            </PrivateRoute>
        );

        expect(screen.queryByTestId('loading-state')).not.toBeInTheDocument();
        expect(mockNavigate).toHaveBeenCalledWith({
            to: ROUTES.LOGIN,
            state: { from: mockLocation },
            replace: true,
        });
    });
});
