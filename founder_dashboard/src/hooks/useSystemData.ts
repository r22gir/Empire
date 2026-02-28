'use client';
import { useState, useEffect, useCallback } from 'react';
import {
  Desk, AIModel, UploadedFile, MaxTask, Reminder,
  AINotification, ServiceHealth, SystemStats, BrainStatus, TokenStats,
  AIDeskStatus,
} from '@/lib/types';
import { API_URL } from '@/lib/api';
import { MOCK_DESKS, MOCK_MODELS } from '@/lib/mockData';

async function timedFetch(url: string, ms = 3000, opts?: RequestInit): Promise<Response | null> {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), ms);
  try {
    const r = await fetch(url, { ...opts, signal: ctrl.signal });
    clearTimeout(t);
    return r.ok ? r : null;
  } catch {
    clearTimeout(t);
    return null;
  }
}

export function useSystemData() {
  const [backendOnline,  setBackendOnline]  = useState(false);
  const [desks,          setDesks]          = useState<Desk[]>(MOCK_DESKS);
  const [models,         setModels]         = useState<AIModel[]>(MOCK_MODELS);
  const [selectedModel,  setSelectedModel]  = useState('grok');
  const [stats,          setStats]          = useState({ total_completed: 0, active_tasks: 0, pending_tasks: 0, total_failed: 0 });
  const [files,          setFiles]          = useState<UploadedFile[]>([]);
  const [tasks,          setTasks]          = useState<MaxTask[]>([]);
  const [reminders,      setReminders]      = useState<Reminder[]>([]);
  const [aiNotifications,setAiNotifications]= useState<AINotification[]>([]);
  const [serviceHealth,  setServiceHealth]  = useState<ServiceHealth>({
    backend: false, workroomforge: false, luxeforge: false,
    homepage: false, amp: false, socialforge: false,
  });
  const [systemStats, setSystemStats] = useState<SystemStats | null>(null);
  const [brainStatus, setBrainStatus] = useState<BrainStatus | null>(null);
  const [tokenStats, setTokenStats] = useState<TokenStats | null>(null);
  const [aiDeskStatuses, setAiDeskStatuses] = useState<AIDeskStatus[]>([]);

  /* ── port probe (2 s timeout, any response = alive) ───────── */
  const checkPort = useCallback(async (url: string): Promise<boolean> => {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 2000);
    try {
      await fetch(url, { signal: ctrl.signal });
      clearTimeout(t);
      return true;
    } catch {
      clearTimeout(t);
      return false;
    }
  }, []);

  /* ── service health ────────────────────────────────────────── */
  const checkHealth = useCallback(async () => {
    const base = API_URL.replace('/api/v1', '');
    const [be, wf, lx, hp, amp, sf] = await Promise.all([
      checkPort(base + '/health'),
      checkPort('http://localhost:3001'),
      checkPort('http://localhost:3002'),
      checkPort('http://localhost:8080'),
      checkPort('http://localhost:3003'),
      checkPort('http://localhost:3004'),
    ]);
    setServiceHealth({ backend: be, workroomforge: wf, luxeforge: lx, homepage: hp, amp, socialforge: sf });
    setBackendOnline(be);
  }, [checkPort]);

  /* ── backend data fetchers ─────────────────────────────────── */
  const fetchDesks = useCallback(async () => {
    const r = await timedFetch(API_URL + '/max/desks');
    if (r) { const d = await r.json(); setDesks(d.desks?.length ? d.desks : MOCK_DESKS); }
  }, []);

  const fetchModels = useCallback(async () => {
    const r = await timedFetch(API_URL + '/max/models');
    if (r) { const d = await r.json(); setModels(d.models?.length ? d.models : MOCK_MODELS); }
  }, []);

  const fetchStats = useCallback(async () => {
    const r = await timedFetch(API_URL + '/max/stats');
    if (r) { const d = await r.json(); setStats(d.stats || {}); }
  }, []);

  const fetchFiles = useCallback(async () => {
    const r = await timedFetch(API_URL + '/files/list');
    if (r) { const d = await r.json(); setFiles(d.files || []); }
  }, []);

  const fetchTasks = useCallback(async () => {
    const r = await timedFetch(API_URL + '/max/tasks');
    if (r) { const d = await r.json(); setTasks(d.tasks || []); }
  }, []);

  const fetchNotifications = useCallback(async () => {
    const r = await timedFetch(API_URL + '/notifications?unread_only=false');
    if (r) { const d = await r.json(); setAiNotifications(d.notifications || []); }
  }, []);

  const fetchSystemStats = useCallback(async () => {
    const r = await timedFetch(API_URL + '/system/stats');
    if (r) setSystemStats(await r.json());
  }, []);

  const fetchBrainStatus = useCallback(async () => {
    const r = await timedFetch(API_URL + '/max/brain/status', 5000);
    if (r) setBrainStatus(await r.json());
  }, []);

  const fetchTokenStats = useCallback(async () => {
    const r = await timedFetch(API_URL + '/max/tokens/stats?days=30');
    if (r) setTokenStats(await r.json());
  }, []);

  const fetchAIDeskStatuses = useCallback(async () => {
    const r = await timedFetch(API_URL + '/max/ai-desks/status');
    if (r) { const d = await r.json(); setAiDeskStatuses(d.desks || []); }
  }, []);

  /* ── polling ───────────────────────────────────────────────── */
  useEffect(() => {
    checkHealth();
    const iv = setInterval(checkHealth, 15000);
    return () => clearInterval(iv);
  }, [checkHealth]);

  useEffect(() => {
    if (!backendOnline) return;
    fetchDesks(); fetchModels(); fetchStats(); fetchFiles(); fetchTasks();
    fetchNotifications(); fetchSystemStats(); fetchBrainStatus(); fetchTokenStats();
    fetchAIDeskStatuses();
    const i1 = setInterval(() => { fetchDesks(); fetchStats(); fetchFiles(); fetchTasks(); }, 30000);
    const i2 = setInterval(fetchSystemStats, 15000);
    const i3 = setInterval(fetchNotifications, 10000);
    const i4 = setInterval(() => { fetchBrainStatus(); fetchTokenStats(); fetchAIDeskStatuses(); }, 30000);
    return () => { clearInterval(i1); clearInterval(i2); clearInterval(i3); clearInterval(i4); };
  }, [backendOnline, fetchDesks, fetchModels, fetchStats, fetchFiles, fetchTasks, fetchNotifications, fetchSystemStats, fetchBrainStatus, fetchTokenStats, fetchAIDeskStatuses]);

  /* ── reminders (localStorage) ──────────────────────────────── */
  useEffect(() => {
    try { const s = localStorage.getItem('empire-reminders'); if (s) setReminders(JSON.parse(s)); } catch {}
  }, []);
  useEffect(() => {
    try { localStorage.setItem('empire-reminders', JSON.stringify(reminders)); } catch {}
  }, [reminders]);

  const addReminder = useCallback((text: string, dueDate: string, priority: 'low' | 'medium' | 'high') => {
    setReminders(p => [...p, { id: Date.now().toString(), text, dueDate, priority, completed: false, createdAt: new Date().toISOString() }]);
  }, []);
  const toggleReminder = useCallback((id: string) => setReminders(p => p.map(r => r.id === id ? { ...r, completed: !r.completed } : r)), []);
  const deleteReminder = useCallback((id: string) => setReminders(p => p.filter(r => r.id !== id)), []);

  /* ── task mutations ────────────────────────────────────────── */
  const createTask = useCallback(async (title: string, description: string, desk_id: string, priority: number) => {
    try {
      await fetch(API_URL + '/max/tasks', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, description, desk_id, priority }),
      });
      fetchTasks(); fetchStats();
    } catch {}
  }, [fetchTasks, fetchStats]);

  const completeTask = useCallback(async (id: string) => {
    try { await fetch(API_URL + '/max/tasks/' + id + '/complete', { method: 'POST' }); fetchTasks(); fetchStats(); } catch {}
  }, [fetchTasks, fetchStats]);

  const failTask = useCallback(async (id: string) => {
    try { await fetch(API_URL + '/max/tasks/' + id + '/fail', { method: 'POST' }); fetchTasks(); fetchStats(); } catch {}
  }, [fetchTasks, fetchStats]);

  /* ── notification mutations ────────────────────────────────── */
  const markNotificationRead = useCallback(async (id: string) => {
    try { await fetch(`${API_URL}/notifications/${id}/read`, { method: 'PATCH' }); fetchNotifications(); } catch {}
  }, [fetchNotifications]);

  const dismissNotification = useCallback(async (id: string) => {
    try { await fetch(`${API_URL}/notifications/${id}`, { method: 'DELETE' }); fetchNotifications(); } catch {}
  }, [fetchNotifications]);

  const respondToNotification = useCallback(async (id: string, action: string) => {
    try { await fetch(`${API_URL}/notifications/respond/${id}?action=${encodeURIComponent(action)}`, { method: 'POST' }); fetchNotifications(); } catch {}
  }, [fetchNotifications]);

  return {
    backendOnline,
    desks, models, selectedModel, setSelectedModel,
    stats, files, tasks, reminders, aiNotifications,
    serviceHealth, systemStats, brainStatus, tokenStats, aiDeskStatuses,
    fetchDesks, fetchModels, fetchStats, fetchFiles, fetchTasks, fetchNotifications,
    addReminder, toggleReminder, deleteReminder,
    createTask, completeTask, failTask,
    markNotificationRead, dismissNotification, respondToNotification,
  };
}
