import type { Role } from "../types/auth";
import type { NavigationItem } from "../types/navigation";

export const navigationItems: NavigationItem[] = [
  {
    label: "Dashboard",
    path: "/dashboard",
    roles: ["STUDENT", "FACULTY", "ADMIN"] as Role[],
  },
  {
    label: "Attendance",
    path: "/attendance",
    roles: ["STUDENT"] as Role[],
  },
  {
    label: "Classes",
    path: "/classes",
    roles: ["FACULTY"] as Role[],
  },
  {
    label: "Users",
    path: "/users",
    roles: ["ADMIN"] as Role[],
  },
];

export const getNavigationForRole = (role: Role): NavigationItem[] => {
  return navigationItems.filter((item) => item.roles.includes(role));
};

