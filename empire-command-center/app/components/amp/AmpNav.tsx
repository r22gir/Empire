'use client';
import { Flame, LogOut, User } from 'lucide-react';
import { clearAmpToken } from '../../lib/amp-auth';
import { useRouter } from 'next/navigation';

export default function AmpNav({ user }: { user?: { name: string } | null }) {
  const router = useRouter();
  const handleLogout = () => {
    clearAmpToken();
    router.push('/amp');
  };

  return (
    <nav style={{ background: '#2D2A26', borderBottom: '1px solid #3d3a36', position: 'sticky', top: 0, zIndex: 50 }}>
      <div style={{ maxWidth: 640, margin: '0 auto', padding: '0 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 48 }}>
        <a href="/amp" style={{ display: 'flex', alignItems: 'center', gap: 10, textDecoration: 'none' }}>
          <div style={{ width: 28, height: 28, borderRadius: 8, background: '#D4A030', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Flame size={14} color="#fff" />
          </div>
          <span style={{ fontWeight: 700, fontSize: 14, color: '#FFF9F0', letterSpacing: 2 }}>AMP</span>
          <span style={{ fontSize: 9, color: '#9B9590', fontWeight: 500, letterSpacing: 1 }}>Actitud Mental Positiva</span>
        </a>
        {user && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <button onClick={() => router.push('/amp/perfil')}
              style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#9B9590', background: 'none', border: 'none', cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>
              <User size={13} />
              <span>{user.name}</span>
            </button>
            <button onClick={handleLogout} style={{ color: '#666', background: 'none', border: 'none', cursor: 'pointer' }} title="Salir">
              <LogOut size={14} />
            </button>
          </div>
        )}
      </div>
    </nav>
  );
}
