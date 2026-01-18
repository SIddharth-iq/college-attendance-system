
import { UserMenu } from "./UserMenu";

interface TopbarProps {
  onMobileMenuToggle: () => void;
}

export const Topbar = ({ onMobileMenuToggle }: TopbarProps) => {
  return (
    <header className="fixed top-0 left-0 right-0 h-16 bg-white border-b z-50 flex items-center justify-between px-4">
      {/* Hamburger menu (mobile only) */}
      <button
        onClick={onMobileMenuToggle}
        className="md:hidden p-2 hover:bg-gray-100 rounded"
        aria-label="Toggle menu"
      >
        <span className="text-xl">☰</span>
      </button>

      {/* Logo/Brand (optional) */}
      <div className="flex-1 md:flex-none">
        <h1 className="text-xl font-bold">College Attendance</h1>
      </div>

      {/* User menu */}
      <UserMenu />
    </header>
  );
};

