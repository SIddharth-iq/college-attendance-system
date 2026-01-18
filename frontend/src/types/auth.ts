export type Role = "STUDENT" | "FACULTY" | "ADMIN";

export interface User {
  id: number;
  username: string;
  name?: string;
  role: Role;
}

export interface AuthContextType {
  user: User | null;
  role: Role | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  refetchAuth: () => Promise<void>;
}

