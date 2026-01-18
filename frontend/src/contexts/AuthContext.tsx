/* eslint-disable react-refresh/only-export-components */

import {
  createContext,
  useEffect,
  useState,
  useCallback,
  useContext,
  type ReactNode,
} from "react";
import api from "../api/axios";
import type { User, Role, AuthContextType } from "../types/auth";

// --------------------
// Context
// --------------------
export const AuthContext = createContext<AuthContextType | undefined>(undefined);

// --------------------
// Provider Props
// --------------------
interface AuthProviderProps {
  children: ReactNode;
}

// --------------------
// Provider
// --------------------
export const AuthProvider = ({ children }: AuthProviderProps) => {
  const [user, setUser] = useState<User | null>(null);
  const [role, setRole] = useState<Role | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const isAuthenticated = user !== null;

  // --------------------
  // Fetch Auth (single source of truth)
  // --------------------
  const fetchAuth = useCallback(async () => {
    setIsLoading(true);

    try {
      const response = await api.get("/auth/me");

      if (response.status === 200 && response.data) {
        setUser(response.data);

        // Normalize role to uppercase for frontend consistency
        setRole(response.data.role?.toUpperCase() as Role);
        return;
      }

      // Fallback safety
      setUser(null);
      setRole(null);
    } catch {
      // Any failure = unauthenticated
      setUser(null);
      setRole(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // --------------------
  // Initial Auth Check
  // --------------------
  useEffect(() => {
    fetchAuth();
  }, [fetchAuth]);

  // --------------------
  // Public Refetch Method
  // --------------------
  const refetchAuth = useCallback(async () => {
    await fetchAuth();
  }, [fetchAuth]);

  return (
    <AuthContext.Provider
      value={{
        user,
        role,
        isAuthenticated,
        isLoading,
        refetchAuth,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

// --------------------
// Custom Hook
// --------------------
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }

  return context;
};
