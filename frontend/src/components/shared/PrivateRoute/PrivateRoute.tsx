import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { ROUTES } from '@/constants';
import { useAuthContext } from '@/context/AuthContext';

interface PrivateRouteProps {
    children: React.ReactNode;
}

export function PrivateRoute({ children }: PrivateRouteProps) {
    const { loading, isAuthenticated } = useAuthContext();
    const location = useLocation();

    if (loading) {
        return <div data-testid="loading-state">Loading...</div>;
    }

    if (!isAuthenticated) {
        return (
            <Navigate
                to={ROUTES.LOGIN}
                state={{ from: location }}
                replace
            />
        );
    }

    return <>{children}</>;
}

export default PrivateRoute;
