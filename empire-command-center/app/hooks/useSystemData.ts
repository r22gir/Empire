'use client';
import { useState, useEffect, useCallback } from 'react';
import { API } from '../lib/api';
import { Desk } from '../lib/types';

export function useSystemData() {
  const [desks, setDesks] = useState<Desk[]>([]);
  const [services, setServices] = useState<any>(null);
  const [briefing, setBriefing] = useState<string>('');
  const [systemStats, setSystemStats] = useState<any>(null);

  const fetchDesks = useCallback(async () => {
    try {
      const res = await fetch(API + '/max/desks');
      if (res.ok) {
        const data = await res.json();
        setDesks(data.desks || data || []);
      }
    } catch { /* silent */ }
  }, []);

  const fetchServices = useCallback(async () => {
    try {
      // Check real service endpoints in parallel
      const checks = [
        { name: 'backend', url: API + '/system/stats' },
        { name: 'ollama', url: API + '/ollama/models' },
        { name: 'openclaw', url: API + '/openclaw/health' },
      ];
      const results: Record<string, string> = {};
      await Promise.all(checks.map(async (svc) => {
        try {
          const r = await fetch(svc.url, { signal: AbortSignal.timeout(3000) });
          results[svc.name] = r.ok ? 'online' : 'degraded';
        } catch {
          results[svc.name] = 'offline';
        }
      }));
      // Telegram status
      try {
        const tgRes = await fetch(API + '/max/telegram/status', { signal: AbortSignal.timeout(3000) });
        if (tgRes.ok) {
          const tg = await tgRes.json();
          results.tg = tg.configured ? 'online' : 'offline';
        }
      } catch { results.tg = 'offline'; }
      setServices(results);
    } catch { /* silent */ }
  }, []);

  const fetchBriefing = useCallback(async () => {
    try {
      const res = await fetch(API + '/max/ai-desks/briefing');
      if (res.ok) {
        const data = await res.json();
        setBriefing(data.briefing || data.content || '');
      }
    } catch { /* silent */ }
  }, []);

  const fetchSystem = useCallback(async () => {
    try {
      const res = await fetch(API + '/system/stats');
      if (res.ok) setSystemStats(await res.json());
    } catch { /* silent */ }
  }, []);

  useEffect(() => {
    fetchDesks();
    fetchServices();
    fetchBriefing();
    fetchSystem();
    const interval = setInterval(() => { fetchServices(); fetchSystem(); }, 60000);
    return () => clearInterval(interval);
  }, [fetchDesks, fetchServices, fetchBriefing, fetchSystem]);

  return { desks, services, briefing, systemStats, fetchDesks, fetchServices };
}
