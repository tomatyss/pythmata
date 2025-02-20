import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { ROUTES } from '@/constants';
import { useAuthContext } from '@/context/AuthContext';

interface PrivateRouteProps {
  children: React.ReactNode;
}

// Main component implementation
function PrivateRouteComponent({ children }: PrivateRouteProps) {
  const { loading, isAuthenticated } = useAuthContext();
  const location = useLocation();

  if (loading) {
    return <div>Loading...</div>; // You might want to use a proper loading component
  }

  if (!isAuthenticated) {
    // Redirect to login page with return url
    return <Navigate to={ROUTES.LOGIN} state={{ from: location }} replace />;
  }

  return <>{children}</>;
}

// Export as a named constant to comply with React Refresh
export const PrivateRoute = PrivateRouteComponent;

// Export as default
export default PrivateRoute;
