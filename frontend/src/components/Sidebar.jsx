import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, FileSearch, BarChart3, Settings, ShieldAlert, Video, ShieldCheck, FileBadge } from 'lucide-react';

export default function Sidebar() {
  const navItems = [
    { name: 'Overview', path: '/', icon: LayoutDashboard },
    { name: 'Image Upload', path: '/image', icon: FileSearch },
    { name: 'Video Upload', path: '/video', icon: Video },
    { name: 'Evidence', path: '/evidence', icon: FileSearch },
    { name: 'Analytics', path: '/analytics', icon: BarChart3 },
    { name: 'Enforcement Center', path: '/enforcement', icon: ShieldCheck },
    { name: 'Challan Database', path: '/challans', icon: FileBadge },
  ];

  return (
    <div className="w-64 bg-dark-800 border-r border-dark-700 h-screen flex flex-col">
      {/* Logo */}
      <div className="h-16 flex items-center px-6 border-b border-dark-700">
        <ShieldAlert className="w-8 h-8 text-danger mr-3" />
        <span className="text-xl font-bold text-white tracking-wide">TVD Admin</span>
      </div>

      {/* Navigation */}
      <div className="flex-1 py-6 px-4 space-y-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.name}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center px-4 py-3 rounded-lg transition-colors ${
                  isActive 
                    ? 'bg-primary/10 text-primary font-semibold' 
                    : 'text-slate-400 hover:bg-dark-700 hover:text-white'
                }`
              }
            >
              <Icon className="w-5 h-5 mr-3" />
              {item.name}
            </NavLink>
          );
        })}
      </div>

      {/* Settings (Bottom) */}
      <div className="p-4 border-t border-dark-700">
        <button className="flex items-center px-4 py-2 w-full text-slate-400 hover:text-white transition-colors">
          <Settings className="w-5 h-5 mr-3" />
          System Config
        </button>
      </div>
    </div>
  );
}
