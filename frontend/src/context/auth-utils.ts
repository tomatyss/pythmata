import type { LoginCredentials, RegisterData, User } from '@/types/auth';

export interface AuthContextType {
  user: User | null;
  loading: boolean;
  error: string | null;
  isAuthenticated: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => Promise<void>;
}

// Move JSX-related code to a separate .tsx file
export type WithAuthProps = {
  loading: boolean;
  isAuthenticated: boolean;
};
