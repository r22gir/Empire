'use client';
// Per-user lists for the Max home (research interests, goals, learning, projects),
// stored by the backend in home_center_state (GET/PUT /api/v1/home-center/state).
import { useCallback, useEffect, useState } from 'react';
import { API } from '../../lib/api';

export type HomeKind = 'interests' | 'goals' | 'learning' | 'projects';
export interface HomeItem { id: string; name: string; icon?: string; note?: string; unit?: string; query?: string; due?: string; progress?: number; total?: number; done?: number }
type State = Record<HomeKind, HomeItem[]>;
const EMPTY: State = { interests: [], goals: [], learning: [], projects: [] };

export function newId(): string { return Math.random().toString(36).slice(2, 10) + Date.now().toString(36).slice(-4); }

export function useHomeStore(user: string) {
  const [state, setState] = useState<State>(EMPTY);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    fetch(`${API}/home-center/state?user=${encodeURIComponent(user)}`, { cache: 'no-store' })
      .then(r => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(d => { if (!alive) return; setState({ interests: d.interests || [], goals: d.goals || [], learning: d.learning || [], projects: d.projects || [] }); setReady(true); })
      .catch(e => { if (alive) { setError(`Could not load your lists (${e.message}).`); setReady(true); } });
    return () => { alive = false; };
  }, [user]);
  const save = useCallback(async (kind: HomeKind, items: HomeItem[]) => {
    const prev = state[kind];
    setState(s => ({ ...s, [kind]: items }));
    try {
      const r = await fetch(`${API}/home-center/state/${kind}?user=${encodeURIComponent(user)}`, {
        method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ items }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json();
      setState(s => ({ ...s, [kind]: d.items || items }));
      setError(null);
    } catch (e: any) {
      setState(s => ({ ...s, [kind]: prev }));
      setError(`Not saved (${e.message}). Try again.`);
    }
  }, [state, user]);
  return { state, ready, error, save };
}
