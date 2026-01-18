import type { Role } from "./auth";

export interface NavigationItem {
  label: string;
  path: string;
  roles: Role[];
}

