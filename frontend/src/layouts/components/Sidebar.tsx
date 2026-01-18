import { useMemo, useState, useEffect } from "react";
import { useAuth } from "../../contexts/useAuth";
import { getNavigationForRole } from "../../config/navigation";
import { SidebarItem } from "./SidebarItem";

interface SidebarProps {
  isMobileOpen: boolean;
  onMobileClose: () => void;
  onCollapseChange?: (isCollapsed: boolean) => void;
}

export const Sidebar = ({ isMobileOpen, onMobileClose, onCollapseChange }: SidebarProps) => {
  const { role } = useAuth();
  const [isCollapsed, setIsCollapsed] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem("dashboard-sidebar-collapsed");
    if (saved !== null) {
      try {
        const savedValue = JSON.parse(saved);
        setIsCollapsed(savedValue);
        onCollapseChange?.(savedValue);
      } catch {
        // Invalid JSON, use default
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const toggleCollapse = () => {
    const newValue = !isCollapsed;
    setIsCollapsed(newValue);
    localStorage.setItem("dashboard-sidebar-collapsed", JSON.stringify(newValue));
    onCollapseChange?.(newValue);
  };

  const navigationItems = useMemo(() => {
    if (!role) return [];
    return getNavigationForRole(role);
  }, [role]);

  return (
    <>
      {/* Mobile backdrop */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 md:hidden"
          onClick={onMobileClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed left-0 top-16 bottom-0 bg-white border-r z-40 transition-all duration-300 ${
          isMobileOpen ? "translate-x-0" : "-translate-x-full"
        } md:translate-x-0 md:block hidden ${
          isCollapsed ? "md:w-16" : "md:w-64"
        } w-64`}
      >
        <div className="h-full flex flex-col">
          {/* Collapse button (desktop only) */}
          <div className="hidden md:flex justify-end p-2 border-b">
            <button
              onClick={toggleCollapse}
              className="p-2 hover:bg-gray-100 rounded"
              aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            >
              {isCollapsed ? "→" : "←"}
            </button>
          </div>

          {/* Navigation items */}
          <nav className="flex-1 overflow-y-auto py-2">
            {navigationItems.map((item) => (
              <SidebarItem key={item.path} item={item} isCollapsed={isCollapsed} />
            ))}
          </nav>
        </div>
      </aside>
    </>
  );
};

