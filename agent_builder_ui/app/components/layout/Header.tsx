import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router';
import { cn } from '../../lib/utils';
import { useAuth } from '../../contexts/AuthContext';
import { Button } from '../ui/Button';

interface NavigationItem {
  name: string;
  href: string;
}

const navigation: NavigationItem[] = [
  { name: 'Dashboard', href: '/' },
  { name: 'Projects', href: '/projects' },
  { name: 'Agents', href: '/agents' },
  { name: 'Workflows', href: '/workflows' },
  { name: 'Tools', href: '/tools' },
  { name: 'Credentials', href: '/credentials' },
];

export function Header() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [showUserMenu, setShowUserMenu] = useState(false);

  const isActive = (href: string) => {
    if (href === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(href);
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
    setShowUserMenu(false);
  };

  return (
    <header className="flex items-center justify-between whitespace-nowrap border-b border-solid border-b-[#233648] px-10 py-3">
      {/* Logo and Brand */}
      <div className="flex items-center gap-4 text-white">
        <div className="size-6 text-[#1173d4]">
          <svg fill="none" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
            <path
              d="M24 45.8096C19.6865 45.8096 15.4698 44.5305 11.8832 42.134C8.29667 39.7376 5.50128 36.3314 3.85056 32.3462C2.19985 28.361 1.76794 23.9758 2.60947 19.7452C3.451 15.5145 5.52816 11.6284 8.57829 8.5783C11.6284 5.52817 15.5145 3.45101 19.7452 2.60948C23.9758 1.76795 28.361 2.19986 32.3462 3.85057C36.3314 5.50129 39.7376 8.29668 42.134 11.8833C44.5305 15.4698 45.8096 19.6865 45.8096 24L24 24L24 45.8096Z"
              fill="currentColor"
            />
          </svg>
        </div>
        <h2 className="text-white text-lg font-bold leading-tight tracking-[-0.015em]">
          AgentSmith
        </h2>
      </div>

      {/* Navigation */}
      <nav className="flex items-center gap-8 text-sm font-medium text-gray-300">
        {navigation.map((item) => (
          <Link
            key={item.name}
            to={item.href}
            className={cn(
              'hover:text-white transition-colors',
              isActive(item.href) && 'text-white font-semibold'
            )}
          >
            {item.name}
          </Link>
        ))}
      </nav>

      {/* User Actions */}
      <div className="flex items-center gap-4">
        <button className="flex h-10 w-10 items-center justify-center rounded-full text-gray-400 hover:bg-[#233648] hover:text-white transition-colors">
          <span className="material-symbols-outlined text-2xl">help</span>
        </button>
        <button className="flex h-10 w-10 items-center justify-center rounded-full text-gray-400 hover:bg-[#233648] hover:text-white transition-colors">
          <span className="material-symbols-outlined text-2xl">notifications</span>
        </button>

        {user ? (
          <div className="relative">
            <button
              onClick={() => setShowUserMenu(!showUserMenu)}
              className="flex items-center gap-2 px-3 py-2 rounded-lg text-gray-300 hover:bg-[#233648] hover:text-white transition-colors"
            >
              <div className="w-8 h-8 bg-[#1173d4] rounded-full flex items-center justify-center text-white font-semibold text-sm">
                {user.username.charAt(0).toUpperCase()}
              </div>
              <span className="text-sm">{user.username}</span>
              <span className="material-symbols-outlined text-sm">expand_more</span>
            </button>

            {showUserMenu && (
              <div className="absolute right-0 mt-2 w-48 bg-[#233648] border border-[#2d3748] rounded-lg shadow-lg z-50">
                <div className="p-3 border-b border-[#2d3748]">
                  <p className="text-sm text-white font-medium">{user.username}</p>
                  <p className="text-xs text-gray-400">{user.email}</p>
                </div>
                <div className="p-2">
                  <button
                    onClick={handleLogout}
                    className="w-full text-left px-3 py-2 text-sm text-gray-300 hover:bg-[#2d3748] hover:text-white rounded-md transition-colors flex items-center gap-2"
                  >
                    <span className="material-symbols-outlined text-sm">logout</span>
                    Sign Out
                  </button>
                </div>
              </div>
            )}
          </div>
        ) : (
          <Link to="/login">
            <Button size="sm">
              Sign In
            </Button>
          </Link>
        )}
      </div>
    </header>
  );
}