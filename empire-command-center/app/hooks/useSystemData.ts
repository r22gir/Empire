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
      const res = await fetch(API + '/max/services');
      if (res.ok) {
        const svcData = await res.json();
        // Also fetch Telegram bot status and merge into services
        try {
          const tgRes = await fetch(API + '/max/telegram/status');
          if (tgRes.ok) {
            const tg = await tgRes.json();
            svcData.tg = { status: tg.configured ? 'online' : 'offline' };
          }
        } catch { /* silent */ }
        setServices(svcData);
      }
    } catch { /* silent */ }
  }, []);

  const fetchBriefing = useCallback(async () => {
    try {
      const res = await fetch(API + '/max/briefing');
      if (res.ok) {
        const data = await res.json();
        setBriefing(data.briefing || data.content || '');
      }
    } catch { /* silent */ }
  }, []);

  const fetchSystem = useCallback(async () => {
    try {
      const res = await fetch(API + '/max/system');
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
