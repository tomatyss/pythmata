import { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthContext } from '@/context/AuthContext';
import { ROUTES } from '@/constants';
import LoadingSpinner from './LoadingSpinner';

/**
 * ProtectedRoute component to guard routes that require authentication
 * Redirects to login page if user is not authenticated
 *
 * @param children - The route component to render if authenticated
 * @returns The protected component or redirect to login
 */
const ProtectedRoute = ({ children }: { children: ReactNode }) => {
  const { isAuthenticated, loading } = useAuthContext();
  const location = useLocation();

  // If still loading auth state, show loading spinner
  if (loading) {
    return <LoadingSpinner fullHeight />;
  }

  // If not authenticated, redirect to login page
  if (!isAuthenticated) {
    // Save the attempted location so we can redirect after login
    return (
      <Navigate to={ROUTES.LOGIN} state={{ from: location.pathname }} replace />
    );
  }

  // If authenticated, render the protected route
  return <>{children}</>;
};

export default ProtectedRoute;
