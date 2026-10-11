'use client';

import { useCallback, useEffect, useState } from 'react';
import { Gauge } from 'lucide-react';
import { useTranslation } from '../../lib/i18n';
import { API } from '../../lib/api';
import { minimaxUsageLabels } from '../../lib/minimaxUsageCopy';

type EditionRow = {
  edition: string;
  label?: string;
  text_share_pct?: number;
  text_cap_pct?: number;
  images_today?: number;
  image_daily_cap?: number;
  tts_today?: number;
  tts_daily_cap?: number;
  video_this_week?: number;
  video_weekly_cap?: number;
};

type Usage = {
  editions?: EditionRow[];
  family_text_share_used_pct?: number;
  family_text_share_pct?: number;
  reserved_share_pct?: number;
  plan?: {
    available?: boolean;
    remaining_pct?: number | null;
    used_pct?: number | null;
    hard_stopped?: boolean;
    message?: string;
  };
  message?: string;
};

type Draft = {
  id: string;
  status: string;
  prompt: string;
  edition: string;
  label_es?: string;
};

const CONFIRM = { 'X-Minimax-Video-Confirm': 'aprobar' };

export default function MinimaxUsageScreen() {
  const { locale } = useTranslation();
  const t = minimaxUsageLabels(locale || 'es');
  const [usage, setUsage] = useState<Usage | null>(null);
  const [denied, setDenied] = useState(false);
  const [queue, setQueue] = useState<Draft[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const res = await fetch(`${API}/minimax-meter/usage`, { credentials: 'include', cache: 'no-store' });
    if (res.status === 403) {
      setDenied(true);
      return;
    }
    if (res.ok) setUsage(await res.json());
    const q = await fetch(`${API}/minimax-meter/video/queue`, { credentials: 'include', cache: 'no-store' });
    if (q.ok) {
      const data = await q.json();
      setQueue(data.items || []);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const act = async (id: string, path: 'approve' | 'reject') => {
    const res = await fetch(`${API}/minimax-meter/video/${id}/${path}`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...CONFIRM },
      body: JSON.stringify({ explicit_yes: false }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      setError(data.detail || `HTTP ${res.status}`);
      return;
    }
    setError(null);
    await load();
  };

  return (
    <div style={{ padding: 24, overflow: 'auto', height: '100%', background: 'var(--chat-bg)' }}>
      <h2 style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 18 }}>
        <Gauge size={18} /> {t.title}
      </h2>
      <p style={{ color: '#5C5650', maxWidth: 720 }}>{t.intro}</p>
      <p style={{ color: '#9a7b2f', fontSize: 13 }}>{t.credits}</p>
      {denied ? <p>{t.denied}</p> : null}
      {usage?.plan?.available ? (
        <p>
          {t.plan}: {usage.plan.used_pct ?? '—'}% used · {usage.plan.remaining_pct ?? '—'}% remaining
          {usage.plan.hard_stopped ? ` · ${usage.plan.message}` : ''}
        </p>
      ) : (
        <p style={{ fontSize: 13, color: '#5C5650' }}>{t.plan}: local meter (remains endpoint not available)</p>
      )}
      <p>
        {t.family}: {usage?.family_text_share_used_pct ?? 0}% / {usage?.family_text_share_pct ?? 20}%
        {' · '}
        {t.reserved}: {usage?.reserved_share_pct ?? 80}%
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 12, marginTop: 16 }}>
        {(usage?.editions || []).map((row) => (
          <section key={row.edition} style={{ border: '1px solid #e5e2dc', borderRadius: 12, padding: 14, background: '#fff' }}>
            <strong>{row.label || row.edition}</strong>
            <div style={{ fontSize: 13, color: '#5C5650', marginTop: 8 }}>
              Text {row.text_share_pct ?? 0}% / {row.text_cap_pct ?? 0}%
              <br />
              {t.images}: {row.images_today ?? 0}/{row.image_daily_cap ?? 5}
              <br />
              {t.voice}: {row.tts_today ?? 0}/{row.tts_daily_cap ?? 20}
              <br />
              {t.video}: {row.video_this_week ?? 0}/{row.video_weekly_cap ?? 1}
            </div>
          </section>
        ))}
      </div>
      <h3 style={{ marginTop: 28 }}>{t.queue}</h3>
      <p style={{ fontSize: 12, color: '#9a7b2f' }}>{t.aiLabel}</p>
      {error ? <p style={{ color: '#9a3412' }}>{error}</p> : null}
      {queue.length === 0 ? <p style={{ fontSize: 13 }}>No drafts.</p> : null}
      {queue.map((item) => (
        <div key={item.id} style={{ border: '1px solid #e5e2dc', borderRadius: 8, padding: 12, marginTop: 8, background: '#fff' }}>
          <div style={{ fontSize: 12, color: '#9a7b2f' }}>{item.edition} · {item.status} · {item.id}</div>
          <div style={{ margin: '6px 0' }}>{item.prompt}</div>
          {item.status === 'draft' ? (
            <div style={{ display: 'flex', gap: 8 }}>
              <button type="button" onClick={() => act(item.id, 'approve')}>{t.approve}</button>
              <button type="button" onClick={() => act(item.id, 'reject')}>{t.reject}</button>
            </div>
          ) : null}
        </div>
      ))}
    </div>
  );
}
