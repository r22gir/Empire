'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import AmpNav from '../../components/amp/AmpNav';
import { getAmpToken, getAmpMe } from '../../lib/amp-auth';

export default function AmpPerfil() {
  const router = useRouter();
  const [user, setUser] = useState<{ name?: string; email?: string } | null>(null);

  useEffect(() => {
    if (!getAmpToken()) {
      router.push('/amp/login');
      return;
    }
    getAmpMe().then(setUser).catch(() => router.push('/amp/login'));
  }, [router]);

  return (
    <div style={{ minHeight: '100vh', background: '#1c1a17', color: '#FFF9F0' }}>
      <AmpNav user={user?.name ? { name: user.name } : null} />
      <main style={{ maxWidth: 640, margin: '0 auto', padding: 24 }}>
        <h1 style={{ fontSize: 22, margin: '8px 0 16px' }}>Perfil</h1>
        {user ? (
          <div style={{ background: '#2D2A26', borderRadius: 12, padding: 16 }}>
            <div style={{ fontSize: 16, fontWeight: 700 }}>{user.name || 'AMP'}</div>
            {user.email && <div style={{ fontSize: 13, color: '#9B9590', marginTop: 4 }}>{user.email}</div>}
          </div>
        ) : (
          <p style={{ color: '#9B9590' }}>Cargando perfil...</p>
        )}
      </main>
    </div>
  );
}
