'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { API } from '../../lib/api';
import MoodBoardView from '../../components/luxeforge/MoodBoardView';

export default function SharedMoodBoardPage() {
  const params = useParams<{ token: string }>();
  const [board, setBoard] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!params?.token) return;
    fetch(`${API}/luxeforge/mood-boards/share/${params.token}`)
      .then(r => { if (!r.ok) throw new Error('This mood board is private or the link expired.'); return r.json(); })
      .then(setBoard)
      .catch(err => setError(err.message));
  }, [params?.token]);

  return (
    <div style={{ minHeight: '100vh', background: '#f5f2ed', padding: '28px 20px' }}>
      <div style={{ maxWidth: 1100, margin: '0 auto' }}>
        <div style={{ fontSize: 11, letterSpacing: 0.08, textTransform: 'uppercase', color: '#7c3aed', fontWeight: 700, marginBottom: 8 }}>
          LuxeForge · Read-only mood board
        </div>
        {error && <div style={{ background: '#fff', border: '1px solid #fecaca', color: '#b91c1c', padding: 16, borderRadius: 12 }}>{error}</div>}
        {board && <MoodBoardView readOnly sharedBoard={board} />}
      </div>
    </div>
  );
}
