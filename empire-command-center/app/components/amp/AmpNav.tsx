'use client';
import { Flame, LogOut, User } from 'lucide-react';
import { clearAmpToken } from '../../lib/amp-auth';
import { useRouter } from 'next/navigation';
import { useAssistantName } from '../../lib/assistant';
import { API } from '../../lib/api';

/** Only routes that exist under empire-command-center/app. */
const ORGANIZER = [
  { label: 'Entrevista', href: '/amp/empresas/entrevista' },
  { label: 'Empresas', href: '/amp/empresas' },
  { label: 'Contactos', href: '/amp/empresas' },
  { label: 'Finanzas', href: '/amp/empresas' },
  { label: 'Cursos', href: '/amp/cursos' },
  { label: 'WhatsApp', href: '/amp/whatsapp' },
  { label: 'Chats', href: '/amp/whatsapp/chats' },
  { label: 'Panel', href: '/amp/dashboard' },
] as const;

export default function AmpNav({ user }: { user?: { name: string } | null }) {
  const router = useRouter();
  const assistant = useAssistantName();
  const handleLogout = () => {
    clearAmpToken();
    fetch(`${API}/amp/auth/logout`, { method: 'POST', credentials: 'include' }).catch(() => {});
    router.push('/login');
  };

  return (
    <nav style={{ background: '#2D2A26', borderBottom: '1px solid #3d3a36', position: 'sticky', top: 0, zIndex: 50 }}>
      <div style={{ maxWidth: 640, margin: '0 auto', padding: '0 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 48 }}>
        <a href="/amp" style={{ display: 'flex', alignItems: 'center', gap: 10, textDecoration: 'none' }}>
          <div style={{ width: 28, height: 28, borderRadius: 8, background: '#D4A030', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Flame size={14} color="#fff" />
          </div>
          <span style={{ fontWeight: 700, fontSize: 14, color: '#FFF9F0' }}>{assistant}</span>
          <span style={{ fontSize: 9, color: '#9B9590', fontWeight: 500, letterSpacing: 1 }}>Centro de mando</span>
        </a>
        {user && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#9B9590', fontSize: 11, fontWeight: 600 }}>
              <User size={13} />
              <span>{user.name}</span>
            </span>
            <button onClick={handleLogout} style={{ color: '#666', background: 'none', border: 'none', cursor: 'pointer' }} title="Salir">
              <LogOut size={14} />
            </button>
          </div>
        )}
      </div>
      <div style={{ maxWidth: 640, margin: '0 auto', padding: '0 16px 10px', display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {ORGANIZER.map((item) => (
          <a
            key={`${item.label}-${item.href}`}
            href={item.href}
            style={{ color: '#D4A030', fontSize: 11, fontWeight: 700, textDecoration: 'none', letterSpacing: 0.3 }}
          >
            {item.label}
          </a>
        ))}
      </div>
    </nav>
  );
}
