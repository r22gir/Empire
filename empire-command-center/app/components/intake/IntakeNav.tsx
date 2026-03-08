'use client';
import { Zap, LogOut } from 'lucide-react';
import { clearToken } from '../../lib/intake-auth';
import { useRouter } from 'next/navigation';

export default function IntakeNav({ user }: { user?: { name: string; company?: string } | null }) {
  const router = useRouter();
  const handleLogout = () => {
    clearToken();
    router.push('/intake');
  };

  return (
    <nav className="bg-white border-b border-[#e5e0d8] sticky top-0 z-50">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 flex items-center justify-between h-14">
        <a href="/intake" className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-[#c9a84c] flex items-center justify-center">
            <Zap size={16} className="text-white" />
          </div>
          <div>
            <span className="font-bold text-[14px] text-[#1a1a1a]">Empire</span>
            <span className="text-[10px] text-[#aaa] ml-1.5">Design Portal</span>
          </div>
        </a>
        {user && (
          <div className="flex items-center gap-3">
            <div className="text-right hidden sm:block">
              <div className="text-xs font-semibold text-[#1a1a1a]">{user.name}</div>
              {user.company && <div className="text-[10px] text-[#aaa]">{user.company}</div>}
            </div>
            <button onClick={handleLogout} className="text-[#aaa] hover:text-[#dc2626] transition-colors" title="Sign Out">
              <LogOut size={16} />
            </button>
          </div>
        )}
      </div>
    </nav>
  );
}
