'use client';

import { useEffect, useMemo, useState } from 'react';
import { CalendarCheck } from 'lucide-react';
import { API } from '../../lib/api';

type OrgTheme = 'a' | 'b' | 'c';

function readTheme(): OrgTheme {
  if (typeof window === 'undefined') return 'a';
  const q = new URLSearchParams(window.location.search).get('orgTheme');
  return q === 'b' || q === 'c' ? q : 'a';
}

export default function OrganizerScreen() {
  const [theme, setTheme] = useState<OrgTheme>(readTheme);
  const [board, setBoard] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const url = new URL(window.location.href);
    if (url.searchParams.get('orgTheme') !== theme) {
      url.searchParams.set('screen', 'calendar');
      url.searchParams.set('orgTheme', theme);
      window.history.replaceState({}, '', `${url.pathname}${url.search}`);
    }
  }, [theme]);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API}/organizer/today`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`${r.status}`))))
      .then((data) => {
        if (!cancelled) setBoard(data);
      })
      .catch((e) => {
        if (!cancelled) setError(e?.message || 'organizer API unavailable');
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const items = useMemo(() => {
    const rows = board?.today || board?.items || board?.overdue || [];
    return Array.isArray(rows) ? rows.slice(0, 12) : [];
  }, [board]);

  return (
    <div className="flex-1 min-h-0 overflow-auto p-6" data-org-theme={theme}>
      <div className="flex items-center justify-between gap-4 mb-5">
        <div>
          <div className="flex items-center gap-2 text-[#b8960c] font-semibold">
            <CalendarCheck size={18} />
            Organizer
          </div>
          <p className="text-sm text-[#666] mt-1">
            Founder task/planner — /api/v1/organizer/* · screen /?screen=calendar
          </p>
        </div>
        <div className="flex gap-1 bg-[#f5f3ef] rounded-lg p-1">
          {(['a', 'b', 'c'] as OrgTheme[]).map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setTheme(t)}
              className="px-3 py-1.5 rounded-md text-xs font-semibold"
              style={{
                background: theme === t ? '#fff' : 'transparent',
                color: theme === t ? '#1a1a1a' : '#888',
                border: theme === t ? '1px solid #e5e2dc' : '1px solid transparent',
              }}
            >
              Theme {t.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <p className="text-sm text-[#888] mb-4">
          Planner API not on this checkout yet ({error}). Route is still /?screen=calendar.
        </p>
      )}

      <div className="grid gap-2">
        {items.length === 0 && !error && (
          <p className="text-sm text-[#888]">No items on the Today board.</p>
        )}
        {items.map((item: any, i: number) => (
          <div key={item.id || i} className="rounded-lg border border-[#ece8df] bg-white px-3 py-2 text-sm">
            {item.title || item.name || item.summary || 'Item'}
          </div>
        ))}
      </div>
    </div>
  );
}
