import React from 'react';
import { useAuthContext } from './AuthContext';

export function withAuth<P extends object>(WrappedComponent: React.ComponentType<P>) {
    function WithAuthComponent(props: P) {
        const { loading, isAuthenticated } = useAuthContext();

        if (loading) {
            return <div data-testid="loading-state">Loading...</div>;
        }

        if (!isAuthenticated) {
            return null;
        }

        return <WrappedComponent {...props} />;
    }

    // Set display name for debugging
    WithAuthComponent.displayName = `WithAuth(${
        WrappedComponent.displayName || WrappedComponent.name || 'Component'
    })`;

    return WithAuthComponent;
}

export default withAuth;
