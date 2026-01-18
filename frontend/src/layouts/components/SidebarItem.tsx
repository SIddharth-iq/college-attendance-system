import { memo } from "react";
import { Link, useLocation } from "react-router-dom";
import type { NavigationItem } from "../../types/navigation";

interface SidebarItemProps {
  item: NavigationItem;
  isCollapsed: boolean;
}

export const SidebarItem = memo(({ item, isCollapsed }: SidebarItemProps) => {
  const location = useLocation();
  const isActive = location.pathname === item.path;

  return (
    <Link
      to={item.path}
      className={`flex items-center gap-3 px-4 py-3 text-gray-700 hover:bg-gray-100 transition-colors ${
        isActive ? "bg-gray-100 border-l-4 border-blue-600" : ""
      } ${isCollapsed ? "justify-center" : ""}`}
      title={isCollapsed ? item.label : undefined}
    >
      {isCollapsed ? (
        <span className="text-lg font-semibold">{item.label[0]}</span>
      ) : (
        <span>{item.label}</span>
      )}
    </Link>
  );
});

SidebarItem.displayName = "SidebarItem";

