import { useContext } from 'react';
import { AuthContext } from './AuthContext';

/**
 * Custom hook to access the AuthContext
 *
 * Ensures that the context is used within an AuthProvider.
 *
 * @returns The AuthContext value
 * @throws Error if used outside of an AuthProvider
 */
export const useAuthContext = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuthContext must be used within an AuthProvider');
  }
  return context;
};
