import React, { createContext, useContext } from 'react';
import { useAuth } from '@/hooks/useAuth';
import type { AuthContextType } from './auth-utils';

const AuthContext = createContext<AuthContextType | null>(null);

// Main Provider component
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const auth = useAuth();

  return <AuthContext.Provider value={auth}>{children}</AuthContext.Provider>;
}

// Separate hook component to comply with React Refresh
function UseAuthContext() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuthContext must be used within an AuthProvider');
  }
  return context;
}

// Export hook as a named constant
export const useAuthContext = () => UseAuthContext();
