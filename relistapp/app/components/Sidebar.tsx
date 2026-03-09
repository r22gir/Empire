'use client';

import {
  LayoutDashboard, List, Share2, Globe, DollarSign,
  Clock, BarChart3, Settings, UserCircle, Camera,
} from 'lucide-react';

const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'profile', label: 'Seller Profile', icon: UserCircle },
  { id: 'smartlister', label: 'Smart Lister', icon: Camera },
  { id: 'listings', label: 'Listings', icon: List },
  { id: 'crosspost', label: 'Cross-Post', icon: Share2 },
  { id: 'platforms', label: 'Platforms', icon: Globe },
  { id: 'pricing', label: 'Pricing', icon: DollarSign },
  { id: 'scheduler', label: 'Scheduler', icon: Clock },
  { id: 'analytics', label: 'Analytics', icon: BarChart3 },
  { id: 'settings', label: 'Settings', icon: Settings },
];

interface SidebarProps {
  active: string;
  onNavigate: (section: string) => void;
}

export default function Sidebar({ active, onNavigate }: SidebarProps) {
  return (
    <aside className="w-52 border-r bg-white flex flex-col" style={{ borderColor: 'var(--border)' }}>
      <nav className="flex-1 py-3 px-2">
        <div className="section-label px-3 mb-2">Navigation</div>
        {NAV_ITEMS.map(item => {
          const Icon = item.icon;
          const isActive = active === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-all mb-0.5"
              style={{
                background: isActive ? 'var(--teal-light, #ecfeff)' : 'transparent',
                color: isActive ? '#06b6d4' : 'var(--text-secondary)',
                borderLeft: isActive ? '3px solid #06b6d4' : '3px solid transparent',
              }}
            >
              <Icon size={17} />
              {item.label}
            </button>
          );
        })}
      </nav>

      <div className="p-3 border-t text-xs" style={{ borderColor: 'var(--border)', color: 'var(--muted)' }}>
        <div className="flex items-center gap-2 mb-1">
          <div className="w-2 h-2 rounded-full bg-green-500" />
          Empire Connected
        </div>
        <div>Port 3007</div>
      </div>
    </aside>
  );
}
