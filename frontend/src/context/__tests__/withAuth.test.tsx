import { vi, describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { withAuth } from '../withAuth';
import { useAuthContext } from '../AuthContext';

// Mock AuthContext
vi.mock('../AuthContext', () => ({
    useAuthContext: vi.fn(),
}));

describe('withAuth HOC', () => {
    const TestComponent = () => <div data-testid="test-component">Test Content</div>;
    const WrappedComponent = withAuth(TestComponent);

    beforeEach(() => {
        vi.clearAllMocks();
        (useAuthContext as jest.Mock).mockReturnValue({
            loading: false,
            isAuthenticated: false,
        });
    });

    it('should show loading state', () => {
        (useAuthContext as jest.Mock).mockReturnValue({
            loading: true,
            isAuthenticated: false,
        });

        render(<WrappedComponent />);

        expect(screen.getByTestId('loading-state')).toBeInTheDocument();
        expect(screen.queryByTestId('test-component')).not.toBeInTheDocument();
    });

    it('should not render component when not authenticated', () => {
        render(<WrappedComponent />);

        expect(screen.queryByTestId('test-component')).not.toBeInTheDocument();
    });

    it('should render component when authenticated', () => {
        (useAuthContext as jest.Mock).mockReturnValue({
            loading: false,
            isAuthenticated: true,
        });

        render(<WrappedComponent />);

        expect(screen.getByTestId('test-component')).toBeInTheDocument();
    });

    it('should handle props correctly', () => {
        interface TestProps {
            testId: string;
            message: string;
        }

        const PropsTestComponent = ({ testId, message }: TestProps) => (
            <div data-testid={testId}>{message}</div>
        );

        const WrappedWithProps = withAuth(PropsTestComponent);

        (useAuthContext as jest.Mock).mockReturnValue({
            loading: false,
            isAuthenticated: true,
        });

        render(
            <WrappedWithProps testId="props-test" message="Hello, World!" />
        );

        const element = screen.getByTestId('props-test');
        expect(element).toBeInTheDocument();
        expect(element).toHaveTextContent('Hello, World!');
    });

    it('should set proper display name', () => {
        const NamedComponent = () => <div>Named Component</div>;
        NamedComponent.displayName = 'NamedComponent';

        const WrappedNamed = withAuth(NamedComponent);
        expect(WrappedNamed.displayName).toBe('WithAuth(NamedComponent)');
    });

    it('should handle state transitions', () => {
        // Initial loading state
        (useAuthContext as jest.Mock).mockReturnValue({
            loading: true,
            isAuthenticated: false,
        });

        const { rerender } = render(<WrappedComponent />);

        // Verify loading state
        expect(screen.getByTestId('loading-state')).toBeInTheDocument();
        expect(screen.queryByTestId('test-component')).not.toBeInTheDocument();

        // Update to authenticated state
        (useAuthContext as jest.Mock).mockReturnValue({
            loading: false,
            isAuthenticated: true,
        });

        rerender(<WrappedComponent />);

        expect(screen.queryByTestId('loading-state')).not.toBeInTheDocument();
        expect(screen.getByTestId('test-component')).toBeInTheDocument();

        // Update to unauthenticated state
        (useAuthContext as jest.Mock).mockReturnValue({
            loading: false,
            isAuthenticated: false,
        });

        rerender(<WrappedComponent />);

        expect(screen.queryByTestId('loading-state')).not.toBeInTheDocument();
        expect(screen.queryByTestId('test-component')).not.toBeInTheDocument();
    });
});
