import { useState, useRef, useEffect } from "react";
import { useAuth } from "../../contexts/useAuth";
import api from "../../api/axios";

export const UserMenu = () => {
  const { user } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  const handleLogout = async () => {
    setIsOpen(false);
    try {
      await api.post("/auth/logout");
    } catch {
      // even if it fails, continue
    }
    window.location.href = "/login";
  };

  if (!user) {
    return null;
  }

  const displayName = user.name || user.username;
  

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-4 py-2 hover:bg-gray-100 rounded"
      >
        <span className="text-sm font-medium">{displayName}</span>
        <span className="text-gray-500">▼</span>
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-48 bg-white border rounded shadow-lg z-50">
          <div className="p-2 border-b">
            <p className="text-sm font-medium">{displayName}</p>
            <p className="text-xs text-gray-500">{user.username}</p>
          </div>
          <button
            onClick={handleLogout}
            className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-gray-100"
          >
            Logout
          </button>
        </div>
      )}
    </div>
  );
};

