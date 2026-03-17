'use client';
import { Crown, LogOut, User } from 'lucide-react';
import { clearToken } from '../../lib/intake-auth';
import { useRouter } from 'next/navigation';

export default function IntakeNav({ user }: { user?: { name: string; company?: string } | null }) {
  const router = useRouter();
  const handleLogout = () => {
    clearToken();
    router.push('/intake');
  };

  return (
    <nav className="bg-[#1a1a1a] border-b border-[#2a2a2a] sticky top-0 z-50">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 flex items-center justify-between h-14">
        <a href="/intake" className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-[#b8960c] flex items-center justify-center">
            <Crown size={13} className="text-white" />
          </div>
          <div className="flex items-center gap-1.5">
            <span className="font-bold text-[13px] text-white tracking-wide">Empire</span>
            <span className="text-[9px] text-[#888] font-medium tracking-wider uppercase">LuxeForge</span>
          </div>
        </a>
        {user && (
          <div className="flex items-center gap-3">
            <button onClick={() => router.push('/intake/account')}
              className="flex items-center gap-1.5 text-[#999] hover:text-[#b8960c] transition-colors cursor-pointer bg-transparent border-none p-2 min-h-[44px] min-w-[44px]"
              title="My Account">
              <User size={16} />
              <span className="text-sm font-semibold hidden sm:inline">{user.name}</span>
            </button>
            {user.company && <span className="text-xs text-[#555] hidden sm:inline">{user.company}</span>}
            <button onClick={handleLogout} className="text-[#666] hover:text-[#dc2626] transition-colors cursor-pointer bg-transparent border-none p-2 min-h-[44px] min-w-[44px]" title="Sign Out">
              <LogOut size={18} />
            </button>
          </div>
        )}
      </div>
    </nav>
  );
}
