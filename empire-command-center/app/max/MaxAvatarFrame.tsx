'use client';

import { useEffect, useState } from 'react';
import { API } from '../lib/api';

const PLACEHOLDER = "Placeholder. This is TalkingHead's female brunette sample (CC BY-NC 4.0, non-commercial), loaded with body M. Edition GLB files are not installed yet.";

export default function MaxAvatarFrame() {
  const [note, setNote] = useState('Checking avatar…');
  const [minutes, setMinutes] = useState<string>('');

  useEffect(() => {
    let stop = false;
    const onMsg = (event: MessageEvent) => {
      if (event.data?.type !== 'avatar-status') return;
      const renderer = event.data.renderer === 'simli' ? 'Simli face only.' : 'TalkingHead.';
      const reason = event.data.reason || '';
      const flag = event.data.placeholder ? (event.data.placeholderNote || PLACEHOLDER) : '';
      setNote([renderer, reason, flag].filter(Boolean).join(' '));
    };
    window.addEventListener('message', onMsg);

    const load = async () => {
      try {
        const [statusRes, usageRes] = await Promise.all([
          fetch(`${API}/avatar/simli/status?edition=workroom`, { signal: AbortSignal.timeout(4000) }),
          fetch(`${API}/avatar/simli/usage?edition=workroom`, { signal: AbortSignal.timeout(4000) }),
        ]);
        if (stop) return;
        if (statusRes.ok) {
          const status = await statusRes.json();
          const renderer = status.renderer === 'simli' ? 'Simli face only.' : 'TalkingHead.';
          const flag = status.edition_avatar?.placeholder ? status.talkinghead_placeholder?.note : '';
          setNote([renderer, status.reason, flag].filter(Boolean).join(' '));
        } else if (!stop) {
          setNote('Simli status unavailable. TalkingHead is the avatar. ' + PLACEHOLDER);
        }
        if (usageRes.ok) {
          const usage = await usageRes.json();
          setMinutes(usage.simli_enabled
            ? `Simli ${(Number(usage.minutes) || 0).toFixed(2)} min`
            : 'Simli off — TalkingHead');
        }
      } catch {
        if (!stop) setNote('Simli status unavailable. TalkingHead is the avatar. ' + PLACEHOLDER);
      }
    };
    load();
    return () => {
      stop = true;
      window.removeEventListener('message', onMsg);
    };
  }, []);

  return (
    <div style={{ border: '1px solid #d9ded5', borderRadius: 8, background: '#fff', overflow: 'hidden' }}>
      <iframe
        src="/avatar.html?edition=workroom"
        title="MAX avatar"
        style={{ width: '100%', height: 360, border: 0, display: 'block', background: '#111' }}
        allow="autoplay"
      />
      <p style={{ margin: 0, padding: '10px 12px', fontSize: 12, lineHeight: 1.45, color: '#4d564d' }}>
        {minutes ? `${minutes}. ` : ''}{note}
      </p>
    </div>
  );
}
