import { useState, type ReactNode } from "react";
import { Topbar } from "./components/Topbar";
import { Sidebar } from "./components/Sidebar";

interface DashboardLayoutProps {
  children: ReactNode;
}

export const DashboardLayout = ({ children }: DashboardLayoutProps) => {
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  const handleMobileToggle = () => {
    setIsMobileOpen(!isMobileOpen);
  };

  const handleMobileClose = () => {
    setIsMobileOpen(false);
  };

  const handleCollapseChange = (isCollapsed: boolean) => {
    setIsSidebarCollapsed(isCollapsed);
  };

  return (
    <div className="flex flex-col h-screen">
      <Topbar onMobileMenuToggle={handleMobileToggle} />
      
      <div className="flex flex-1 pt-16">
      <Sidebar
  isMobileOpen={isMobileOpen}
  isCollapsed={isSidebarCollapsed}
  onMobileClose={handleMobileClose}
  onCollapseChange={handleCollapseChange}
/>

        
        <main className="flex-1 overflow-y-auto pt-16">
  <div className="p-6">{children}</div>
</main>

      </div>
    </div>
  );
};

