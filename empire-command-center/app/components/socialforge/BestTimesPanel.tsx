'use client';

import { useEffect, useState } from 'react';
import { Clock, Sparkles, BarChart3 } from 'lucide-react';
import { API } from '../../lib/api';

export type BestTimeSlot = {
  weekday: string;
  hour: number;
  label: string;
  score: number;
  source: 'history' | 'default' | string;
  sample_size?: number;
};

export type BestTimesPayload = {
  platform?: string;
  used_defaults?: boolean;
  history_posts?: number;
  suggestions?: BestTimeSlot[];
  note?: string;
};

function nextOccurrence(weekday: string, hour: number): { date: string; time: string } {
  const names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  const target = names.indexOf(weekday);
  const now = new Date();
  const next = new Date(now);
  const delta = (target - now.getDay() + 7) % 7;
  next.setDate(now.getDate() + (delta === 0 && now.getHours() >= hour ? 7 : delta));
  next.setHours(hour, 0, 0, 0);
  const date = `${next.getFullYear()}-${String(next.getMonth() + 1).padStart(2, '0')}-${String(next.getDate()).padStart(2, '0')}`;
  const time = `${String(hour).padStart(2, '0')}:00`;
  return { date, time };
}

export default function BestTimesPanel({
  platform,
  compact = false,
  onPick,
}: {
  platform?: string;
  compact?: boolean;
  onPick?: (date: string, time: string, slot: BestTimeSlot) => void;
}) {
  const [data, setData] = useState<BestTimesPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const qs = platform ? `?platform=${encodeURIComponent(platform)}` : '';
    fetch(`${API}/socialforge/best-times${qs}`)
      .then(r => { if (!r.ok) throw new Error('Could not load best times'); return r.json(); })
      .then(body => {
        if (platform) setData(body);
        else setData(body.all || body);
      })
      .catch(err => setError(err.message));
  }, [platform]);

  const suggestions = data?.suggestions || [];

  return (
    <div className="empire-card" style={{ padding: compact ? 14 : 18 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{
            width: 28, height: 28, borderRadius: 8,
            background: 'linear-gradient(135deg, #ec4899, #a855f7)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Clock size={14} color="#fff" />
          </div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>Best time to post</div>
            <div style={{ fontSize: 10, color: '#999' }}>
              {data?.used_defaults
                ? 'Industry defaults — not enough engagement history yet'
                : 'Ranked from your posted engagement history'}
            </div>
          </div>
        </div>
        {data?.used_defaults
          ? <Sparkles size={14} color="#c9a84c" />
          : <BarChart3 size={14} color="#ec4899" />}
      </div>

      {error && <div style={{ fontSize: 11, color: '#dc2626' }}>{error}</div>}

      <div style={{ display: 'grid', gridTemplateColumns: compact ? '1fr' : 'repeat(3, minmax(0, 1fr))', gap: 8 }}>
        {suggestions.map(slot => (
          <button
            key={`${slot.weekday}-${slot.hour}`}
            onClick={() => {
              const next = nextOccurrence(slot.weekday, slot.hour);
              onPick?.(next.date, next.time, slot);
            }}
            style={{
              textAlign: 'left', padding: '10px 12px', borderRadius: 12,
              border: '1px solid #ece8e0', background: '#fff', cursor: onPick ? 'pointer' : 'default',
            }}
          >
            <div style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>{slot.label}</div>
            <div style={{ fontSize: 10, color: '#888', marginTop: 4 }}>
              {slot.source === 'history' ? `${slot.sample_size || 0} posts` : 'Default window'}
            </div>
          </button>
        ))}
      </div>
      {data?.note && (
        <p style={{ fontSize: 10, color: '#aaa', margin: '10px 0 0' }}>{data.note}</p>
      )}
    </div>
  );
}
